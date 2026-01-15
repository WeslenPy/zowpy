from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncContextManager, AsyncGenerator, List, Optional
import threading

from sqlalchemy.orm import Session
from sqlalchemy import func, text
from sqlalchemy.exc import PendingRollbackError, InvalidRequestError
import asyncio


from ...axolotl.identitykey import IdentityKey
from ...axolotl.identitykeypair import IdentityKeyPair
from ...axolotl.ecc.djbec import DjbECPublicKey, DjbECPrivateKey
from ...axolotl.util.keyhelper import KeyHelper
from ...axolotl.state.axolotlstore import AxolotlStore
from ...axolotl.state.prekeyrecord import PreKeyRecord
from ...axolotl.state.sessionrecord import SessionRecord
from ...axolotl.state.signedprekeyrecord import SignedPreKeyRecord
from ...axolotl.invalidkeyidexception import InvalidKeyIdException

from ...db.models import Account
from ...db import models
from ...db.pool import AsyncDatabasePool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, exists
from ...utils.tools import WATools

from zowpy.protocol.historysync.attributes import (
                AppStateSyncKeyAttribute,
                AppStateSyncKeyIdAttribute,
                AppStateSyncKeyDataAttribute,
            )
from loguru import logger


async def _get_or_create_account(db: AsyncSession, phone: str) -> models.Account:
    """
    Ensures there is an Account row for the given phone.
    ✅ OTIMIZAÇÃO: Usa cache para reduzir queries.
    """
    logger.debug(f"_get_or_create_account: checking for account with phone {phone}")
    # Busca ou cria Account
    result = await db.execute(select(models.Account).filter_by(phone=phone))
    account = result.scalar_one_or_none()
    if account is None:
        logger.debug(f"_get_or_create_account: account not found, creating new account for phone {phone}")
        account = models.Account(phone=phone)
        db.add(account)
        await db.flush()
        await db.refresh(account)
        logger.info(f"_get_or_create_account: created new Account row for phone={phone} (id={account.id})")
    else:
        logger.debug(f"_get_or_create_account: found existing account id {account.id} for phone {phone}")

    return account


class SqlIdentityKeyStore:
    """
    Identity store backed by SQLAlchemy / MySQL.
    Mirrors the behaviour of LiteIdentityKeyStore but bound to an Account.
    """

    def __init__(self, db: AsyncSession, account: models.Account):
        self.db = db
        self.account = account

        # Lazily ensure local identity exists - will be done async

    async def initialize(self):
        if await self.getLocalRegistrationId() is None or await self.getIdentityKeyPair() is None:
            identity = await KeyHelper.generateIdentityKeyPair()
            registration_id = await KeyHelper.generateRegistrationId(True)
            await self._storeLocalData(registration_id, identity)

    async def _query_local_row(self) -> Optional[models.Identity]:


        logger.debug(f"_query_local_row(account_id={self.account})")
        result = await self.db.execute(
            select(models.Identity).filter(
                models.Identity.account_id == self.account.id,
                models.Identity.recipient_id == -1,
            )
        )
        return result.scalar_one_or_none()

    async def getIdentityKeyPair(self) -> Optional[IdentityKeyPair]:
        logger.debug("getIdentityKeyPair: querying local identity row")
        row = await self._query_local_row()
        if not row or not row.public_key or not row.private_key:
            logger.debug("getIdentityKeyPair: no valid identity key pair found")
            return None

        public_key_bytes = row.public_key
        private_key_bytes = row.private_key
        logger.debug(f"getIdentityKeyPair: loaded identity key pair, public_key_len={len(public_key_bytes)}, private_key_len={len(private_key_bytes)}")
        # Original LiteIdentityKeyStore strips first byte (0x05) for public key
        return IdentityKeyPair(
            IdentityKey(DjbECPublicKey(public_key_bytes[1:])),
            DjbECPrivateKey(private_key_bytes),
        )

    async def getLocalRegistrationId(self) -> Optional[int]:
        logger.debug("getLocalRegistrationId: querying local identity row")
        row = await self._query_local_row()
        reg_id = row.registration_id if row else None
        logger.debug(f"getLocalRegistrationId: registration_id={reg_id}")
        return reg_id

    async def _storeLocalData(self, registrationId, identityKeyPair, deviceid: int = 0) -> None:
        try:
            row = await self._query_local_row()
            if row is None:
                row = models.Identity(
                    account_id=self.account.id,
                    recipient_id=-1,
                    recipient_type=0,
                    device_id=deviceid,
                )
                self.db.add(row)

            row.registration_id = registrationId
            pub_key = identityKeyPair.getPublicKey().getPublicKey().serialize()
            priv_key = identityKeyPair.getPrivateKey().serialize()
            row.public_key = pub_key
            row.private_key = priv_key
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Erro ao armazenar dados locais de identidade: {e}", exc_info=True)
            raise

    async def saveIdentity(self, recipientId, deviceId, identityKey) -> None:
        logger.debug(f"saveIdentity: recipientId={recipientId}, deviceId={deviceId}")
        try:
            # Delete existing
            logger.debug(f"saveIdentity: deleting existing identity for recipientId={recipientId}, deviceId={deviceId}")
            await self.db.execute(
                delete(models.Identity).filter(
                    models.Identity.account_id == self.account.id,
                    models.Identity.recipient_id == recipientId,
                    models.Identity.device_id == deviceId,
                )
            )
            pub_key = identityKey.getPublicKey().serialize()
            logger.debug(f"saveIdentity: inserting new identity, public_key_len={len(pub_key)}")
            row = models.Identity(
                account_id=self.account.id,
                recipient_id=recipientId,
                recipient_type=0,
                device_id=deviceId,
                public_key=pub_key,
            )
            self.db.add(row)
            await self.db.commit()
            logger.debug(f"saveIdentity: successfully saved identity for recipientId={recipientId}, deviceId={deviceId}")
        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"saveIdentity: error saving identity for recipientId={recipientId}, deviceId={deviceId}: {e}",
                exc_info=True
            )
            raise

    async def isTrustedIdentity(self, recipient, deviceid, identityKey) -> bool:
        result = await self.db.execute(
            select(models.Identity.public_key).filter(
                models.Identity.account_id == self.account.id,
                models.Identity.recipient_id == recipient,
                models.Identity.device_id == deviceid,
            )
        )
        public_key = result.scalar()
        if not public_key:
            return True

        pub_key = identityKey.getPublicKey().serialize()
        return public_key == pub_key


class SqlPreKeyStore:
    """
    PreKey store backed by SQLAlchemy.
    """

    def __init__(self, db: AsyncSession, account: models.Account):
        self.db = db
        self.account = account

    async def loadPreKey(self, preKeyId: int) -> PreKeyRecord:
        logger.debug(f"loadPreKey: preKeyId={preKeyId}")
        result = await self.db.execute(
            select(models.PreKey.record)
            .filter(
                models.PreKey.account_id == self.account.id,
                models.PreKey.prekey_id == preKeyId,
            )
        )
        record = result.scalar()
        if not record:
            logger.warning(f"loadPreKey: no prekey found for preKeyId={preKeyId}")
            raise InvalidKeyIdException("No such prekeyrecord!")
        logger.debug(f"loadPreKey: loaded prekey record, size={len(record)} bytes")
        return PreKeyRecord(serialized=record)

    async def loadUnsentPendingPreKeys(self) -> List[PreKeyRecord]:
        logger.debug("loadUnsentPendingPreKeys: querying unsent prekeys")
        result = await self.db.execute(
            select(models.PreKey.record)
            .filter(
                models.PreKey.account_id == self.account.id,
                (models.PreKey.sent_to_server.is_(None))
                | (models.PreKey.sent_to_server.is_(False)),
            )
        )
        rows = result.all()
        prekeys = [PreKeyRecord(serialized=r[0]) for r in rows]
        logger.debug(f"loadUnsentPendingPreKeys: found {len(prekeys)} unsent prekeys")
        return prekeys

    async def setAsSent(self, prekeyIds: List[int]) -> None:
        if not prekeyIds:
            return
        try:
            await self.db.execute(
                update(models.PreKey)
                .filter(
                    models.PreKey.account_id == self.account.id,
                    models.PreKey.prekey_id.in_(prekeyIds),
                )
                .values(sent_to_server=True)
            )
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Erro ao marcar PreKeys como enviados: {e}", exc_info=True)
            raise

    async def loadPendingPreKeys(self) -> List[PreKeyRecord]:
        try:
            result = await self.db.execute(
                select(models.PreKey.record).filter(models.PreKey.account_id == self.account.id)
            )
            rows = result.all()
            return [PreKeyRecord(serialized=r[0]) for r in rows]
        except Exception as e:
            logger.error(f"Erro em loadPendingPreKeys: {e}")
            return []

    async def storePreKey(self, preKeyId: int, preKeyRecord: PreKeyRecord) -> None:
        logger.debug(f"storePreKey: preKeyId={preKeyId}")
        try:
            record_data = preKeyRecord.serialize()
            logger.debug(f"storePreKey: storing prekey, record_size={len(record_data)} bytes")
            row = models.PreKey(
                account_id=self.account.id,
                prekey_id=preKeyId,
                record=record_data,
            )
            self.db.add(row)
            await self.db.commit()
            logger.debug(f"storePreKey: successfully stored prekey {preKeyId}")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"storePreKey: error storing prekey {preKeyId}: {e}", exc_info=True)
            raise

    async def containsPreKey(self, preKeyId: int) -> bool:
        result = await self.db.execute(
            select(
                exists(
                    select(models.PreKey.id)
                    .filter(
                        models.PreKey.account_id == self.account.id,
                        models.PreKey.prekey_id == preKeyId,
                    )
                )
            )
        )
        return result.scalar() or False

    async def removePreKey(self, preKeyId: int) -> None:
        try:
            await self.db.execute(
                delete(models.PreKey)
                .filter(
                    models.PreKey.account_id == self.account.id,
                    models.PreKey.prekey_id == preKeyId,
                )
            )
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Erro ao remover PreKey {preKeyId}: {e}", exc_info=True)
            raise

    async def loadMaxPreKeyId(self) -> int:
        result = await self.db.execute(
            select(func.max(models.PreKey.prekey_id))
            .filter(models.PreKey.account_id == self.account.id)
        )
        max_id = result.scalar()
        return int(max_id or 0)

    async def clear(self) -> None:
        await self.db.execute(
            delete(models.PreKey)
            .filter(models.PreKey.account_id == self.account.id)
        )
        await self.db.commit()


class SqlSignedPreKeyStore:
    """
    Signed prekey store backed by SQLAlchemy.
    """

    def __init__(self, db: AsyncSession, account: models.Account):
        self.db = db
        self.account = account

    async def loadSignedPreKey(self, signedPreKeyId: int) -> SignedPreKeyRecord:
        logger.debug(f"loadSignedPreKey: signedPreKeyId={signedPreKeyId}")
        result = await self.db.execute(
            select(models.SignedPreKey.record)
            .filter(
                models.SignedPreKey.account_id == self.account.id,
                models.SignedPreKey.prekey_id == signedPreKeyId,
            )
        )
        record = result.scalar()
        if not record:
            logger.warning(f"loadSignedPreKey: no signed prekey found for signedPreKeyId={signedPreKeyId}")
            raise InvalidKeyIdException("No such signedprekeyrecord! %s " % signedPreKeyId)
        logger.debug(f"loadSignedPreKey: loaded signed prekey record, size={len(record)} bytes")
        return SignedPreKeyRecord(serialized=record)

    async def loadSignedPreKeys(self) -> List[SignedPreKeyRecord]:
        result = await self.db.execute(
            select(models.SignedPreKey.record)
            .filter(models.SignedPreKey.account_id == self.account.id)
            .order_by(models.SignedPreKey.prekey_id.asc())
        )
        rows = result.all()
        return [SignedPreKeyRecord(serialized=r[0]) for r in rows]

    async def storeSignedPreKey(self, signedPreKeyId: int, signedPreKeyRecord: SignedPreKeyRecord) -> None:
        logger.debug(f"storeSignedPreKey: signedPreKeyId={signedPreKeyId}")
        try:
            # Delete existing
            logger.debug(f"storeSignedPreKey: deleting existing signed prekey for signedPreKeyId={signedPreKeyId}")
            await self.db.execute(
                delete(models.SignedPreKey)
                .filter(
                    models.SignedPreKey.account_id == self.account.id,
                    models.SignedPreKey.prekey_id == signedPreKeyId,
                )
            )
            record_data = signedPreKeyRecord.serialize()
            timestamp = signedPreKeyRecord.getTimestamp()
            logger.debug(f"storeSignedPreKey: storing signed prekey, record_size={len(record_data)} bytes, timestamp={timestamp}")
            row = models.SignedPreKey(
                account_id=self.account.id,
                prekey_id=signedPreKeyId,
                timestamp=timestamp,
                record=record_data,
            )
            self.db.add(row)
            await self.db.commit()
            logger.debug(f"storeSignedPreKey: successfully stored signed prekey {signedPreKeyId}")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"storeSignedPreKey: error storing signed prekey {signedPreKeyId}: {e}", exc_info=True)
            raise

    async def containsSignedPreKey(self, signedPreKeyId: int) -> bool:
        result = await self.db.execute(
            select(
                exists(
                    select(models.SignedPreKey.id)
                    .filter(
                        models.SignedPreKey.account_id == self.account.id,
                        models.SignedPreKey.prekey_id == signedPreKeyId,
                    )
                )
            )
        )
        return result.scalar() or False

    async def removeSignedPreKey(self, signedPreKeyId: int) -> None:
        try:
            await self.db.execute(
                delete(models.SignedPreKey)
                .filter(
                    models.SignedPreKey.account_id == self.account.id,
                    models.SignedPreKey.prekey_id == signedPreKeyId,
                )
            )
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Erro ao remover SignedPreKey {signedPreKeyId}: {e}", exc_info=True)
            raise


class SqlSessionStore:
    """
    Session store backed by SQLAlchemy.
    """

    def __init__(self, db: AsyncSession, account: models.Account):
        self.db = db
        self.account = account

    async def loadSession(self, account: int, deviceId: int) -> SessionRecord:
        logger.debug(f"loadSession: account={account}, deviceId={deviceId}")
        result = await self.db.execute(
            select(models.Session.record)
            .filter(
                models.Session.account_id == self.account.id,
                models.Session.recipient_id == account,
                models.Session.device_id == deviceId,
            )
        )
        record = result.scalar()
        if record:
            logger.debug(f"loadSession: found existing session, record_size={len(record)} bytes")
            return SessionRecord(serialized=record)
        logger.debug("loadSession: no existing session found, returning empty session")
        return SessionRecord()

    async def getSubDeviceSessions(self, recipient: int) -> List[int]:
        result = await self.db.execute(
            select(models.Session.device_id)
            .filter(
                models.Session.account_id == self.account.id,
                models.Session.recipient_id == recipient,
            )
        )
        rows = result.all()
        return [r[0] for r in rows]

    async def storeSession(self, recipient: int, deviceId: int, sessionRecord: SessionRecord) -> None:
        logger.debug(f"storeSession: recipient={recipient}, deviceId={deviceId}")
        try:
            # Delete existing first
            logger.debug(f"storeSession: deleting existing session for recipient={recipient}, deviceId={deviceId}")
            await self.db.execute(
                delete(models.Session)
                .filter(
                    models.Session.account_id == self.account.id,
                    models.Session.recipient_id == recipient,
                    models.Session.device_id == deviceId,
                )
            )

            record_data = sessionRecord.serialize()
            logger.debug(f"storeSession: storing session, record_size={len(record_data)} bytes")
            row = models.Session(
                account_id=self.account.id,
                recipient_id=recipient,
                device_id=deviceId,
                record=record_data,
            )
            self.db.add(row)
            await self.db.commit()
            logger.debug(f"storeSession: successfully stored session for recipient={recipient}, deviceId={deviceId}")
        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"storeSession: error storing session for recipient={recipient}, deviceId={deviceId}: {e}",
                exc_info=True
            )
            raise

    async def containsSession(self, recipient: int, deviceId: int) -> bool:
        logger.debug(f"containsSession: checking session for recipient={recipient}, deviceId={deviceId}")
        result = await self.db.execute(
            select(
                exists(
                    select(models.Session.id)
                    .filter(
                        models.Session.account_id == self.account.id,
                        models.Session.recipient_id == recipient,
                        models.Session.device_id == deviceId,
                    )
                )
            )
        )
        session_exists = result.scalar() or False
        logger.debug(f"containsSession: session exists={session_exists}")
        return session_exists

    async def deleteSession(self, recipient: int, deviceId: int) -> None:
        await self.db.execute(
            delete(models.Session)
            .filter(
                models.Session.account_id == self.account.id,
                models.Session.recipient_id == recipient,
                models.Session.device_id == deviceId,
            )
        )
        await self.db.commit()

    async def deleteAllSessions(self, recipient: int) -> None:
        await self.db.execute(
            delete(models.Session)
            .filter(
                models.Session.account_id == self.account.id,
                models.Session.recipient_id == recipient,
            )
        )
        await self.db.commit()

    async def getAllAccounts(self, recipient: int) -> List[str]:
        result = await self.db.execute(
            select(
                models.Session.recipient_id,
                models.Session.recipient_type,
                models.Session.device_id,
            ).filter(
                models.Session.account_id == self.account.id,
                models.Session.recipient_id == recipient,
            )
        )
        rows = result.all()
        return ["%d.%d:%d" % (r[0], r[1], r[2]) for r in rows]
    
    async def get_all_session_usernames(self, recipient: int) -> List[str]:
        """
        Obtém todos os usernames de sessão relacionados a um recipient.
        Similar ao getAllAccounts mas retorna lista de JIDs completos.

        :param recipient: ID do recipient
        :return: Lista de JIDs de sessão
        """
        result = await self.db.execute(
            select(
                models.Session.recipient_id,
                models.Session.recipient_type,
                models.Session.device_id,
            )
            .filter(
                models.Session.account_id == self.account.id,
                models.Session.recipient_id == recipient,
            )
        )
        rows = result.all()
        return ["%d.%d:%d" % (r[0], r[1], r[2]) for r in rows]


class SqlSenderKeyStore:
    """
    SenderKey store backed by SQLAlchemy.
    """

    def __init__(self, db: AsyncSession, account: models.Account):
        self.db = db
        self.account = account

    async def storeSenderKey(self, senderKeyName, senderKeyRecord) -> None:
        # senderKeyName.getGroupId(), senderKeyName.getSender().getName()
        group_id = senderKeyName.getGroupId()
        sender_id = senderKeyName.getSender().getName()
        serialized = senderKeyRecord.serialize()

        logger.debug(f"storeSenderKey: group_id={group_id}, sender_id={sender_id}, record_size={len(serialized)} bytes")

        result = await self.db.execute(
            select(models.SenderKey)
            .filter(
                models.SenderKey.account_id == self.account.id,
                models.SenderKey.group_id == group_id,
                models.SenderKey.sender_id == sender_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            logger.debug("storeSenderKey: creating new sender key record")
            row = models.SenderKey(
                account_id=self.account.id,
                group_id=group_id,
                sender_id=sender_id,
                record=serialized,
            )
            self.db.add(row)
        else:
            logger.debug("storeSenderKey: updating existing sender key record")
            row.record = serialized
        await self.db.commit()
        logger.debug(f"storeSenderKey: successfully stored sender key for group_id={group_id}, sender_id={sender_id}")

    async def loadSenderKey(self, senderKeyName):
        from ...axolotl.groups.state.senderkeyrecord import SenderKeyRecord

        group_id = senderKeyName.getGroupId()
        sender_id = senderKeyName.getSender().getName()
        result = await self.db.execute(
            select(models.SenderKey.record)
            .filter(
                models.SenderKey.account_id == self.account.id,
                models.SenderKey.group_id == group_id,
                models.SenderKey.sender_id == sender_id,
            )
        )
        record = result.scalar()
        if not record:
            return SenderKeyRecord()
        return SenderKeyRecord(serialized=record)


class SqlPollStore:
    """
    Poll store backed by SQLAlchemy.
    Exposed via SqlAxolotlStore.pollStore for compatibility with existing code.
    """

    def __init__(self, db: AsyncSession, account: models.Account):
        self.db = db
        self.account = account

    async def deletePoll(self, poll_msg_id: int) -> None:
        result = await self.db.execute(
            select(models.Poll)
            .filter(
                models.Poll.account_id == self.account.id,
                models.Poll.poll_msg_id == poll_msg_id,
            )
        )
        poll = result.scalar_one_or_none()
        if poll:
            await self.db.delete(poll)
            await self.db.commit()

    async def storePoll(self, poll_msg_id: int, name: str, enc_key: bytes, options: List[str]) -> None:
        poll = models.Poll(
            account_id=self.account.id,
            poll_msg_id=poll_msg_id,
            enc_key=enc_key,
            name=name,
        )
        self.db.add(poll)
        await self.db.flush()  # so poll.id is available

        import hashlib

        for item in options:
            opt_hash = hashlib.sha256(item.encode()).digest()
            opt = models.PollOption(
                poll_id=poll.id,
                option_name=item,
                option_sha256=opt_hash,
            )
            self.db.add(opt)

        await self.db.commit()

    async def decryptOptions(self, poll_msg_id: int, option_sha256_list: List[bytes]) -> List[str]:
        options: List[str] = []
        result = await self.db.execute(
            select(models.Poll)
            .filter(
                models.Poll.account_id == self.account.id,
                models.Poll.poll_msg_id == poll_msg_id,
            )
        )
        poll = result.scalar_one_or_none()
        if not poll:
            return ["ITEM ERROR"] * len(option_sha256_list)

        for sha256_item in option_sha256_list:
            opt_result = await self.db.execute(
                select(models.PollOption)
                .filter(
                    models.PollOption.poll_id == poll.id,
                    models.PollOption.option_sha256 == sha256_item,
                )
            )
            opt = opt_result.scalar_one_or_none()
            if opt:
                options.append(opt.option_name)
            else:
                options.append("ITEM ERROR")
        return options

    async def getPollEncKey(self, poll_msg_id: int) -> Optional[bytes]:
        result = await self.db.execute(
            select(models.Poll)
            .filter(
                models.Poll.account_id == self.account.id,
                models.Poll.poll_msg_id == poll_msg_id,
            )
        )
        poll = result.scalar_one_or_none()
        return poll.enc_key if poll else None


class SqlTaskMsgStore:
    """
    TaskMsg store backed by SQLAlchemy.
    Port of LiteTaskMsgStore.
    """

    def __init__(self, db: AsyncSession, account: models.Account):
        self.db = db
        self.account = account

    async def setTaskMsg(self, msg_id: str, task_id: str, src: str, dst: str) -> None:
        """
        Armazena uma mensagem de tarefa.
        """
        # Remove existente se houver (upsert)
        result = await self.db.execute(
            select(models.TaskMsg)
            .filter(
                models.TaskMsg.account_id == self.account.id,
                models.TaskMsg.msg_id == msg_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.task_id = task_id
            existing.src = src
            existing.dst = dst
        else:
            row = models.TaskMsg(
                account_id=self.account.id,
                msg_id=msg_id,
                task_id=task_id,
                src=src,
                dst=dst,
            )
            self.db.add(row)
        await self.db.commit()

    async def getTaskMsg(self, msg_id: str) -> Optional[dict]:
        """
        Retorna informações da mensagem de tarefa.
        """
        result = await self.db.execute(
            select(models.TaskMsg)
            .filter(
                models.TaskMsg.account_id == self.account.id,
                models.TaskMsg.msg_id == msg_id,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        return {
            "msg_id": row.msg_id,
            "task_id": row.task_id,
            "src": row.src,
            "dst": row.dst,
        }

    async def getMsgTaskByResponseMsg(self, sender: str, receive: str) -> Optional[str]:
        """
        Busca task_id baseado em mensagem de resposta (sender/receive).
        """
        result = await self.db.execute(
            select(models.TaskMsg.task_id)
            .filter(
                models.TaskMsg.account_id == self.account.id,
                models.TaskMsg.src == sender,
                models.TaskMsg.dst == receive,
            )
            .order_by(models.TaskMsg.created_at.desc())
        )
        row = result.first()
        return row[0] if row else None

    async def delExpiredTaskMsg(self) -> int:
        """
        Remove mensagens de tarefa expiradas.
        Retorna número de registros removidos.
        """
        from datetime import datetime
        now = datetime.utcnow()
        result = await self.db.execute(
            delete(models.TaskMsg)
            .filter(
                models.TaskMsg.account_id == self.account.id,
                models.TaskMsg.expires_at < now,
            )
        )
        await self.db.commit()
        return result.rowcount


class SqlAppStateStore:
    """
    AppState key store backed by SQLAlchemy.
    """

    def __init__(self, db: AsyncSession, account: models.Account):
        self.db = db
        self.account = account

    async def addAppStateKeys(self, keys) -> None:
        import time

        now = int(time.time())
        for key in keys:
            row = models.AppStateKey(
                account_id=self.account.id,
                key_id=key.key_id.key_id,
                key_data=key.key_data.key_data,
                fingerprint=None,
                timestamp=now,
            )
            self.db.add(row)
        await self.db.commit()

    async def getOneAppStateKey(self):

        result = await self.db.execute(
            select(models.AppStateKey)
            .filter(models.AppStateKey.account_id == self.account.id)
            .order_by(models.AppStateKey.timestamp.desc())
        )
        row = result.first()
        if not row:
            return None
        return AppStateSyncKeyAttribute(
            key_id=AppStateSyncKeyIdAttribute(key_id=row.key_id),
            key_data=AppStateSyncKeyDataAttribute(
                key_data=row.key_data,
                fingerprint=row.fingerprint,
                timestamp=row.timestamp,
            ),
        )

    async def getAppStateKey(self, key_id: bytes):

        result = await self.db.execute(
            select(models.AppStateKey)
            .filter(
                models.AppStateKey.account_id == self.account.id,
                models.AppStateKey.key_id == key_id,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        return AppStateSyncKeyAttribute(
            key_id=AppStateSyncKeyIdAttribute(key_id=row.key_id),
            key_data=AppStateSyncKeyDataAttribute(
                key_data=row.key_data,
                fingerprint=row.fingerprint,
                timestamp=row.timestamp,
            ),
        )

    async def deleteAppStateKey(self, key_id: bytes) -> None:
        await self.db.execute(
            delete(models.AppStateKey)
            .filter(
                models.AppStateKey.account_id == self.account.id,
                models.AppStateKey.key_id == key_id,
            )
        )
        await self.db.commit()


class SqlContactStore:
    """
    Contact store backed by SQLAlchemy.
    """

    def __init__(self, db: AsyncSession, account: models.Account):
        self.db = db
        self.account = account

    async def addContact(self, jid: str, name: Optional[str] = None):
        if not (jid.endswith("s.whatsapp.net") or jid.endswith("lid")):
            return None
        if name is None:
            name = ""
        if not await self.findContact(jid):
            import time

            row = models.Contact(
                account_id=self.account.id,
                jid=jid,
                name=name,
                timestamp=int(time.time()),
            )
            self.db.add(row)
            await self.db.commit()
            return jid
        return None

    async def findContact(self, jid: str):
        if not (jid.endswith("s.whatsapp.net") or jid.endswith("lid")):
            return None
        result = await self.db.execute(
            select(models.Contact)
            .filter(
                models.Contact.account_id == self.account.id,
                models.Contact.jid == jid,
            )
        )
        row = result.scalar_one_or_none()
        return bool(row)

    async def isNewContact(self, jid: str) -> bool:
        if jid.endswith("@s.whatsapp.net") or jid.endswith("@c.us"):
            return not await self.findContact(jid)
        return False

    async def removeContact(self, jid: str) -> bool:
        await self.db.execute(
            delete(models.Contact)
            .filter(
                models.Contact.account_id == self.account.id,
                models.Contact.jid == jid,
            )
        )
        await self.db.commit()
        return True

    async def getAllContact(self):
        result = await self.db.execute(
            select(models.Contact.jid)
            .filter(models.Contact.account_id == self.account.id)
        )
        rows = result.all()
        return [r[0] for r in rows]


class SqlBroadcastStore:
    """
    Broadcast store backed by SQLAlchemy.
    """

    def __init__(self, db: AsyncSession, account: models.Account):
        self.db = db
        self.account = account

    def phash(self, jids):
        import hashlib
        import base64

        jids = sorted(jids)
        h = hashlib.sha256()
        for jid in jids:
            h.update(jid.encode())
        return "2:" + base64.b64encode(h.digest()[:6]).decode()

    async def addBroadcast(self, jids, senderJid, name=None):
        # WATools já importado no topo do arquivo

        if isinstance(jids, str):
            jids = jids.split(",")

        newJid = [WATools.fullJid(j) for j in jids]
        newJid.append(WATools.fullJid(senderJid))

        phash = self.phash(newJid)
        if name is None:
            name = ""

        # Try to reuse existing broadcast by phash
        result = await self.db.execute(
            select(models.Broadcast)
            .filter(
                models.Broadcast.account_id == self.account.id,
                models.Broadcast.phash == phash,
            )
        )
        bcast = result.scalar_one_or_none()
        if bcast:
            return bcast.bcid, bcast.phash

        import time

        bcid = "%d@broadcast" % time.time()
        bcast = models.Broadcast(
            account_id=self.account.id,
            sender=WATools.fullJid(senderJid),
            name=name,
            jids=",".join(newJid),
            phash=phash,
            bcid=bcid,
        )
        self.db.add(bcast)
        await self.db.commit()
        return bcid, phash

    async def findParticipantsByBcid(self, bcid: str):
        result = await self.db.execute(
            select(models.Broadcast)
            .filter(
                models.Broadcast.account_id == self.account.id,
                models.Broadcast.bcid == bcid,
            )
        )
        bcast = result.scalar_one_or_none()
        if not bcast:
            return None
        # Return list of jids excluding sender
        jids = [item for item in bcast.jids.split(",") if item != bcast.sender]
        return jids


class SqlTrustedContactStore:
    """
    Trusted contact store backed by SQLAlchemy.
    """

    def __init__(self, db: AsyncSession, account: models.Account):
        self.db = db
        self.account = account

    async def updateTrustedContact(self, jid: str, tctoken: Optional[bytes] = None) -> bool:
        import time

        if not (jid.endswith("s.whatsapp.net") or jid.endswith("lid")):
            return False
        if tctoken is None:
            return False

        await self.db.execute(
            delete(models.TrustedContact)
            .filter(
                models.TrustedContact.account_id == self.account.id,
                models.TrustedContact.jid == jid,
            )
        )
        row = models.TrustedContact(
            account_id=self.account.id,
            jid=jid,
            incoming_tc_token=tctoken,
            timestamp=int(time.time()),
        )
        self.db.add(row)
        await self.db.commit()
        return True

    async def getTcToken(self, jid: str) -> Optional[bytes]:
        result = await self.db.execute(
            select(models.TrustedContact)
            .filter(
                models.TrustedContact.account_id == self.account.id,
                models.TrustedContact.jid == jid,
            )
        )
        row = result.scalar_one_or_none()
        return row.incoming_tc_token if row else None

    async def removeTrustedContact(self, jid: str) -> bool:
        await self.db.execute(
            delete(models.TrustedContact)
            .filter(
                models.TrustedContact.account_id == self.account.id,
                models.TrustedContact.jid == jid,
            )
        )
        await self.db.commit()
        return True


class SqlAxolotlStore(AxolotlStore):
    """
    Axolotl store implementation backed by MySQL/SQLAlchemy.

    It wraps the per‑table stores above and exposes the same public surface
    as LiteAxolotlStore so that AxolotlManager and the rest of the stack
    can work unchanged.
    
    IMPORTANT: This store uses thread-local sessions for thread-safe isolation.
    Each thread gets its own session, preventing concurrent operation errors.
    The session is automatically managed via thread-local storage.
    
    The store creates a synchronous engine from the async engine of db_pool,
    allowing the synchronous Axolotl core to work with the async database pool.
    """

    def __init__(self, username: str, db_pool: Optional[AsyncDatabasePool] = None):
        """
        :param username: phone / account identifier (same as AxolotlManager.username)
        :param db_pool: AsyncDatabasePool instance (required)
        """
        if db_pool is None:
            raise ValueError("db_pool é obrigatório para SqlAxolotlStore")
        
        self._username = username
        self._db_pool = db_pool
        self._account_id: Optional[int] = None
        self._closed = False
        # Sub-stores serão criados quando necessário
        self._sub_stores_initialized = False
        # Lock para proteger inicialização de sub-stores (evita race conditions)
        import threading
        self._init_lock = threading.RLock()

    
    @asynccontextmanager
    async def _get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Obtém sessão assíncrona.
        Usa o db_pool para obter uma sessão async.

        Returns:
            AsyncSession: Sessão assíncrona
        """
        if self._closed:
            raise RuntimeError("SqlAxolotlStore foi fechado. Não é possível reutilizar.")

        async with self._db_pool.get_session() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            else:
                await session.commit()


    async def _get_account(self, db: AsyncSession) -> models.Account:
        """
        Obtém ou cria account para a sessão atual.
        Usa cache para evitar queries repetidas.
        
        Valida que o account corresponde ao username correto para garantir isolamento.
        
        Args:
            db: Sessão do banco de dados
            
        Returns:
            models.Account: Account associado ao username
            
        Raises:
            RuntimeError: Se não for possível obter ou criar o account
        """
        if self._account_id is None:
            logger.debug(f"_get_account: creating/getting account for username {self._username}")
            account = await _get_or_create_account(db, self._username)
            self._account_id = account.id
            # Validação de isolamento: garante que o account corresponde ao username
            if account.phone != self._username:
                logger.error(
                    f"[ISOLATION] Account ID {account.id} não corresponde ao username {self._username} | "
                    f"account.phone={account.phone}"
                )
                raise RuntimeError(f"Account mismatch: expected {self._username}, got {account.phone}")
            logger.debug(f"_get_account: using account id {account.id} for username {self._username}")
            return account

        # Busca account pelo ID (mais eficiente que buscar por phone)
        # Usa one_or_none para tratar caso o account tenha sido deletado
        result = await db.execute(select(models.Account).filter_by(id=self._account_id))
        account = result.scalar_one_or_none()

        # Se não encontrou, limpa cache e recria
        if account is None:
            logger.warning(
                f"Account {self._account_id} não encontrado para username={self._username}, "
                f"limpando cache e recriando..."
            )
            self._account_id = None
            account = await _get_or_create_account(db, self._username)
            self._account_id = account.id

        # Validação de isolamento: garante que o account corresponde ao username
        if account.phone != self._username:
            logger.error(
                f"[ISOLATION] Account ID {account.id} não corresponde ao username {self._username} | "
                f"account.phone={account.phone}"
            )
            # Limpa cache e recria para corrigir
            self._account_id = None
            account = await _get_or_create_account(db, self._username)
            self._account_id = account.id

        logger.debug(f"get_account(username={self._username}, account_id={account.id})")
        return account
    
    async def _ensure_sub_stores(self, db: AsyncSession, account: models.Account):
        """
        Cria sub-stores se ainda não foram inicializados.
        Cada sub-store recebe a sessão thread-local atual.
        Thread-safe: usa lock para evitar race conditions.
        
        Args:
            db: Sessão thread-local atual
            account: Account associado
        """
        with self._init_lock:
            if self._sub_stores_initialized:
                # Atualiza referências de db e account nos sub-stores existentes
                # Isso é necessário porque o account pode estar detached da sessão anterior
                await self._update_sub_stores_db_and_account(db, account)
                return
            
            # Cria sub-stores pela primeira vez
            self.identityKeyStore = SqlIdentityKeyStore(db, account)
            self.preKeyStore = SqlPreKeyStore(db, account)
            self.signedPreKeyStore = SqlSignedPreKeyStore(db, account)
            self.sessionStore = SqlSessionStore(db, account)
            self.senderKeyStore = SqlSenderKeyStore(db, account)
            self.pollStore = SqlPollStore(db, account)
            self.appStateStore = SqlAppStateStore(db, account)
            self.contactStore = SqlContactStore(db, account)
            self.broadcastStore = SqlBroadcastStore(db, account)
            self.trustedContactStore = SqlTrustedContactStore(db, account)
            self.taskMsgStore = SqlTaskMsgStore(db, account)

            await self.identityKeyStore.initialize()
            
            self._sub_stores_initialized = True
    
    async def _update_sub_stores_db_and_account(self, db: AsyncSession, account: models.Account):
        """
        Atualiza referências de db e account nos sub-stores.
        Isso é necessário para evitar DetachedInstanceError quando a sessão muda.
        Garante que o account está vinculado à sessão atual usando merge.
        
        Args:
            db: Nova sessão thread-local
            account: Account vinculado à nova sessão
        """
        # Garante que o account está vinculado à sessão atual
        # Isso evita DetachedInstanceError quando o account veio de outra sessão
        try:
            # Tenta fazer merge do account na sessão atual
            # Se o account já estiver na sessão, merge retorna o mesmo objeto
            await db.merge(account)
            logger.debug(f"_update_sub_stores_db_and_account(db={db}, account={account})")
        except Exception as e:
            # Se merge falhar, tenta recarregar o account da sessão atual
            logger.warning(f"Erro ao fazer merge do account na sessão: {e}, tentando recarregar...")
            query = select(models.Account).filter_by(id=account.id)
            result = await db.execute(query)
            account = result.scalar_one_or_none()
            if account is None:
                account = await _get_or_create_account(db, self._username)
                self._account_id = account.id
    
        stores = [
            self.identityKeyStore,
            self.preKeyStore,
            self.signedPreKeyStore,
            self.sessionStore,
            self.senderKeyStore,
            self.pollStore,
            self.appStateStore,
            self.contactStore,
            self.broadcastStore,
            self.trustedContactStore,
            self.taskMsgStore,
        ]
        
        for store in stores:
            if store is not None:
                if hasattr(store, 'db'):
                    store.db = db
                if hasattr(store, 'account'):
                    store.account = account
    
    def _update_sub_stores_db(self, db: AsyncSession):
        """
        Atualiza apenas a referência de db nos sub-stores (account não mudou).
        DEPRECATED: Use _update_sub_stores_db_and_account em vez disso.
        
        Args:
            db: Nova sessão thread-local
        """
        stores = [
            self.identityKeyStore,
            self.preKeyStore,
            self.signedPreKeyStore,
            self.sessionStore,
            self.senderKeyStore,
            self.pollStore,
            self.appStateStore,
            self.contactStore,
            self.broadcastStore,
            self.trustedContactStore,
        ]
        
        for store in stores:
            if store is not None and hasattr(store, 'db'):
                store.db = db
    
    def close(self):
        """
        Fecha store e limpa recursos.
        """
        self._closed = True
        self._account_id = None
        self._sub_stores_initialized = False
    
    def __del__(self):
        """
        Cleanup automático quando o objeto é destruído.
        Não precisa fechar sessões thread-local aqui.
        """
        self._closed = True

    def __str__(self):
        return "mysql:account=%s" % self._username

    # Identity store facade
    async def getIdentityKeyPair(self):
        logger.debug("SqlAxolotlStore.getIdentityKeyPair: starting")
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            result = await self.identityKeyStore.getIdentityKeyPair()
            logger.debug(f"SqlAxolotlStore.getIdentityKeyPair: result={'found' if result else 'not found'}")
            return result

    async def getLocalRegistrationId(self):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            return await self.identityKeyStore.getLocalRegistrationId()

    async def saveIdentity(self, recipientId, deviceId, identityKey):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            await self.identityKeyStore.saveIdentity(recipientId, deviceId, identityKey)

    async def isTrustedIdentity(self, recipientId, deviceId, identityKey):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            return await self.identityKeyStore.isTrustedIdentity(recipientId, deviceId, identityKey)

    # Helper for migration/import flows: update local identity row
    async def updateLocalIdentityKeys(self, registration_id, public_key, private_key, deviceid: int = 0) -> None:
        """
        Updates the local identity row (recipient_id = -1) with the provided
        registration_id, public_key and private_key.

        This is used by legacy import/export flows that previously updated
        the SQLite 'identities' table directly.
        """
        logger.debug(f"SqlAxolotlStore.updateLocalIdentityKeys: registration_id={registration_id}, deviceid={deviceid}")
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)

            try:
                logger.debug("SqlAxolotlStore.updateLocalIdentityKeys: querying existing identity row")
                result = await db.execute(
                    select(models.Identity).filter(
                        models.Identity.account_id == account.id,
                        models.Identity.recipient_id == -1,
                    )
                )
                row = result.scalar_one_or_none()
                if row is None:
                    logger.debug("SqlAxolotlStore.updateLocalIdentityKeys: creating new identity row")
                    row = models.Identity(
                        account_id=account.id,
                        recipient_id=-1,
                        recipient_type=0,
                        device_id=deviceid,
                    )
                    db.add(row)
                else:
                    logger.debug("SqlAxolotlStore.updateLocalIdentityKeys: updating existing identity row")

                row.registration_id = registration_id
                row.public_key = public_key
                row.private_key = private_key
                row.device_id = deviceid
                await db.commit()
                logger.debug(f"SqlAxolotlStore.updateLocalIdentityKeys: successfully updated local identity keys for account {account.id}")
            except Exception as e:
                await db.rollback()
                logger.error(f"SqlAxolotlStore.updateLocalIdentityKeys: error updating local identity keys: {e}", exc_info=True)
                raise

    # PreKey store facade
    async def loadPreKey(self, preKeyId):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            return self.preKeyStore.loadPreKey(preKeyId)

    async def loadPreKeys(self):
        logger.debug("SqlAxolotlStore.loadPreKeys: starting")
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            result = await self.preKeyStore.loadPendingPreKeys()
            logger.debug(f"SqlAxolotlStore.loadPreKeys: loaded {len(result)} unsent prekeys")
            return result

    async def storePreKey(self, preKeyId, preKeyRecord):
        logger.debug(f"SqlAxolotlStore.storePreKey: preKeyId={preKeyId}")
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            await self.preKeyStore.storePreKey(preKeyId, preKeyRecord)
            logger.debug(f"SqlAxolotlStore.storePreKey: successfully stored preKeyId={preKeyId}")

    async def containsPreKey(self, preKeyId):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            return self.preKeyStore.containsPreKey(preKeyId)

    async def removePreKey(self, preKeyId):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            self.preKeyStore.removePreKey(preKeyId)

    async def removeAllPreKeys(self):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            self.preKeyStore.clear()

    # Session store facade
    async def loadSession(self, account, deviceId):
        logger.debug(f"SqlAxolotlStore.loadSession: account={account}, deviceId={deviceId}")
        async with self._get_session() as db:
            account_obj = await self._get_account(db)
            await self._ensure_sub_stores(db, account_obj)
            result = await self.sessionStore.loadSession(account, deviceId)
            logger.debug(f"SqlAxolotlStore.loadSession: loaded session, has_data={len(result.serialize()) > 0}")
            return result

    async def getSubDeviceSessions(self, account):
        async with self._get_session() as db:
            account_obj = await self._get_account(db)
            await self._ensure_sub_stores(db, account_obj)
            return self.sessionStore.getSubDeviceSessions(account)

    async def storeSession(self, account, deviceId, sessionRecord):
        logger.debug(f"SqlAxolotlStore.storeSession: account={account}, deviceId={deviceId}")
        async with self._get_session() as db:
            account_obj = await self._get_account(db)
            await self._ensure_sub_stores(db, account_obj)
            await self.sessionStore.storeSession(account, deviceId, sessionRecord)
            logger.debug(f"SqlAxolotlStore.storeSession: successfully stored session for account={account}, deviceId={deviceId}")

    async def containsSession(self, account, deviceId):
        async with self._get_session() as db:
            account_obj = await self._get_account(db)
            await self._ensure_sub_stores(db, account_obj)
            return await self.sessionStore.containsSession(account, deviceId)

    async def deleteSession(self, account, deviceId):
        async with self._get_session() as db:
            account_obj = await self._get_account(db)
            await self._ensure_sub_stores(db, account_obj)
            self.sessionStore.deleteSession(account, deviceId)

    async def deleteAllSessions(self, account):
        async with self._get_session() as db:
            account_obj = await self._get_account(db)
            await self._ensure_sub_stores(db, account_obj)
            self.sessionStore.deleteAllSessions(account)

    async def getAllAccounts(self, account):
        async with self._get_session() as db:
            account_obj = await self._get_account(db)
            await self._ensure_sub_stores(db, account_obj)
            return await self.sessionStore.getAllAccounts(account)
    
    async def get_all_session_usernames(self, account):
        """
        Obtém todos os usernames de sessão relacionados.

        :param account: ID do recipient
        :return: Lista de JIDs de sessão
        """
        async with self._get_session() as db:
            account_obj = await self._get_account(db)
            await self._ensure_sub_stores(db, account_obj)
            return await self.sessionStore.get_all_session_usernames(account)

    # Signed prekey facade
    async def loadSignedPreKey(self, signedPreKeyId):
        logger.debug(f"SqlAxolotlStore.loadSignedPreKey: signedPreKeyId={signedPreKeyId}")
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            result = await self.signedPreKeyStore.loadSignedPreKey(signedPreKeyId)
            logger.debug(f"SqlAxolotlStore.loadSignedPreKey: loaded signed prekey {signedPreKeyId}")
            return result

    async def loadSignedPreKeys(self):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            return await self.signedPreKeyStore.loadSignedPreKeys()

    async def storeSignedPreKey(self, signedPreKeyId, signedPreKeyRecord):
        logger.debug(f"SqlAxolotlStore.storeSignedPreKey: signedPreKeyId={signedPreKeyId}")
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            await self.signedPreKeyStore.storeSignedPreKey(signedPreKeyId, signedPreKeyRecord)
            logger.debug(f"SqlAxolotlStore.storeSignedPreKey: successfully stored signed prekey {signedPreKeyId}")

    async def containsSignedPreKey(self, signedPreKeyId):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            return self.signedPreKeyStore.containsSignedPreKey(signedPreKeyId)

    async def removeSignedPreKey(self, signedPreKeyId):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            self.signedPreKeyStore.removeSignedPreKey(signedPreKeyId)

    # Sender key facade
    async def loadSenderKey(self, senderKeyName):
        group_id = senderKeyName.getGroupId()
        sender_id = senderKeyName.getSender().getName()
        logger.debug(f"SqlAxolotlStore.loadSenderKey: group_id={group_id}, sender_id={sender_id}")
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            result = await self.senderKeyStore.loadSenderKey(senderKeyName)
            logger.debug(f"SqlAxolotlStore.loadSenderKey: loaded sender key, has_data={len(result.serialize()) > 0}")
            return result

    async def storeSenderKey(self, senderKeyName, senderKeyRecord):
        group_id = senderKeyName.getGroupId()
        sender_id = senderKeyName.getSender().getName()
        logger.debug(f"SqlAxolotlStore.storeSenderKey: group_id={group_id}, sender_id={sender_id}")
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            await self.senderKeyStore.storeSenderKey(senderKeyName, senderKeyRecord)
            logger.debug(f"SqlAxolotlStore.storeSenderKey: successfully stored sender key for group_id={group_id}, sender_id={sender_id}")

    # App state keys
    async def addAppStateKeys(self, keys):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            return self.appStateStore.addAppStateKeys(keys)

    async def getOneAppStateKey(self):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            return self.appStateStore.getOneAppStateKey()

    async def getAppStateKey(self, key_id):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            return self.appStateStore.getAppStateKey(key_id)

    async def removeAppStateKey(self, key_id):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            return self.appStateStore.deleteAppStateKey(key_id)

    # Contacts
    async def addContact(self, jid):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            return self.contactStore.addContact(jid, "")

    async def removeContact(self, jid):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            return self.contactStore.removeContact(jid)

    async def getAllContact(self):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            return self.contactStore.getAllContact()

    async def findContact(self, jid):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            return self.contactStore.findContact(jid)

    async def isNewContact(self, jid):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            return self.contactStore.isNewContact(jid)

    # Broadcasts
    async def addBroadcast(self, jids, senderJid, name=None):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            return self.broadcastStore.addBroadcast(jids, senderJid, name)

    async def findParticipantsByBcid(self, bcid):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            return self.broadcastStore.findParticipantsByBcid(bcid)

    # Trusted contacts
    async def updateTrustedContact(self, jid, tctoken):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            return self.trustedContactStore.updateTrustedContact(jid, tctoken)

    async def getTcToken(self, jid):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            return self.trustedContactStore.getTcToken(jid)

    # Poll store facade
    async def deletePoll(self, poll_msg_id):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            return self.pollStore.deletePoll(poll_msg_id)

    async def storePoll(self, poll_msg_id, name, enc_key, options):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            return self.pollStore.storePoll(poll_msg_id, name, enc_key, options)

    async def decryptOptions(self, poll_msg_id, option_sha256_list):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            return self.pollStore.decryptOptions(poll_msg_id, option_sha256_list)

    async def getPollEncKey(self, poll_msg_id):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            return self.pollStore.getPollEncKey(poll_msg_id)

    # TaskMsg store facade
    async def setTaskMsg(self, msg_id, task_id, src, dst):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            return self.taskMsgStore.setTaskMsg(msg_id, task_id, src, dst)

    async def getTaskMsg(self, msg_id):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            return self.taskMsgStore.getTaskMsg(msg_id)

    async def getMsgTaskByResponseMsg(self, sender, receive):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            return self.taskMsgStore.getMsgTaskByResponseMsg(sender, receive)

    async def delExpiredTaskMsg(self):
        async with self._get_session() as db:
            account = await self._get_account(db)
            await self._ensure_sub_stores(db, account)
            return self.taskMsgStore.delExpiredTaskMsg()




