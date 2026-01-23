from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncContextManager, AsyncGenerator, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func, text
from sqlalchemy.exc import PendingRollbackError, InvalidRequestError


from ..axolotl.identitykey import IdentityKey
from ..axolotl.identitykeypair import IdentityKeyPair
from ..axolotl.ecc.djbec import DjbECPublicKey, DjbECPrivateKey
from ..axolotl.util.keyhelper import KeyHelper
from ..axolotl.state.axolotlstore import AxolotlStore
from ..axolotl.state.prekeyrecord import PreKeyRecord
from ..axolotl.state.sessionrecord import SessionRecord
from ..axolotl.state.signedprekeyrecord import SignedPreKeyRecord
from ..axolotl.invalidkeyidexception import InvalidKeyIdException

from ..db.models import (Account, Identity, 
                        PreKey, SignedPreKey, 
                        SessionKey, SenderKey, Poll, 
                        AppStateKey, Contact, Broadcast, 
                        TrustedContact, TaskMsg)



from ..db import models
from ..db.config.engine import AsyncSessionMaker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, exists, insert
from ..utils.tools import WATools

from zowpy.protocol.historysync.attributes import (
                AppStateSyncKeyAttribute,
                AppStateSyncKeyIdAttribute,
                AppStateSyncKeyDataAttribute,
            )
from loguru import logger


class BaseStore:
    pass

class SqlIdentityKeyStore(BaseStore):
    """
    Identity store backed by SQLAlchemy / MySQL.
    Mirrors the behaviour of LiteIdentityKeyStore but bound to an Account.
    """

    async def initialize(self, session: AsyncSession, account_id: int):
        if await self.getLocalRegistrationId(account_id, session) is None or await self.getIdentityKeyPair(account_id, session) is None:
            identity = KeyHelper.generateIdentityKeyPair()
            registration_id = KeyHelper.generateRegistrationId(True)
            await self._storeLocalData(session, account_id, registration_id, identity)

    async def getIdentityKeyPair(self,account_id: int, session: AsyncSession) -> Optional[IdentityKeyPair]:
        return await Identity.get_identity_key_pair(session, account_id)

    async def getLocalRegistrationId(self,account_id: int, session: AsyncSession) -> Optional[int]:
        logger.debug("getLocalRegistrationId: querying local identity row")
        return await Identity.get_local_registration_id(session, account_id)

    async def _storeLocalData(self,session: AsyncSession, account_id: int, registrationId, identityKeyPair, deviceid: int = 0) -> None:
        return await Identity.store_local_data(session, account_id, registrationId, identityKeyPair, deviceid)


    async def saveIdentity(self,session: AsyncSession, account_id: int, recipientId, deviceId, identityKey) -> None:
        return await Identity.save_identity(session, account_id, recipientId, deviceId, identityKey)

    async def isTrustedIdentity(self,session: AsyncSession, account_id: int, recipient, deviceid, identityKey) -> bool:
        return await Identity.is_trusted_identity(session, account_id, recipient, deviceid, identityKey)
        

class SqlPreKeyStore(BaseStore):
    """
    PreKey store backed by SQLAlchemy.
    """

    async def loadPreKey(self,session: AsyncSession, account_id: int, preKeyId: int) -> PreKeyRecord:
        return await PreKey.load_prekey(session, account_id, preKeyId)

    async def loadUnsentPendingPreKeys(self,session: AsyncSession, account_id: int) -> List[PreKeyRecord]:
        return await PreKey.load_unsent_pending_prekeys(session, account_id)

    async def setAsSent(self,session: AsyncSession, account_id: int, prekeyIds: List[int]) -> None:
        return await PreKey.set_as_sent(session, account_id, prekeyIds)

    async def loadPendingPreKeys(self,session: AsyncSession, account_id: int) -> List[PreKeyRecord]:
        return await PreKey.load_pending_prekeys(session, account_id)

    async def storePreKey(self, session: AsyncSession, account_id: int, preKeyId: int, preKeyRecord: PreKeyRecord) -> None:
        record_data = preKeyRecord.serialize()
        return await PreKey.store_prekey(session, account_id, preKeyId, record_data)

    async def storePreKeys(self, session: AsyncSession, account_id: int, prekeys: List[Tuple[int, PreKeyRecord]]) -> None:
       return await PreKey.store_prekeys_bulk(session, account_id, prekeys)

    async def containsPreKey(self, session: AsyncSession, account_id: int, preKeyId: int) -> bool:
        return await PreKey.contains_prekey(session, account_id, preKeyId)

    async def removePreKey(self, session: AsyncSession, account_id: int, preKeyId: int) -> None:
        return await PreKey.remove_prekey(session, account_id, preKeyId)

    async def loadMaxPreKeyId(self, session: AsyncSession, account_id: int) -> int:
        return await PreKey.load_max_prekey_id(session, account_id)

    async def clear(self, session: AsyncSession, account_id: int) -> None:
        return await PreKey.clear_prekeys(session, account_id)


class SqlSignedPreKeyStore(BaseStore):
    """
    Signed prekey store backed by SQLAlchemy.
    """

    async def loadSignedPreKey(self, session: AsyncSession, account_id: int, signedPreKeyId: int) -> SignedPreKeyRecord:
        return await SignedPreKey.load_signed_prekey(session, account_id, signedPreKeyId)

    async def loadSignedPreKeys(self, session: AsyncSession, account_id: int) -> List[SignedPreKeyRecord]:
        return await SignedPreKey.load_signed_prekeys(session, account_id)

    async def storeSignedPreKey(self, session: AsyncSession, account_id: int, signedPreKeyId: int, signedPreKeyRecord: SignedPreKeyRecord) -> None:
        record_data = signedPreKeyRecord.serialize()
        timestamp = signedPreKeyRecord.getTimestamp()
        return await SignedPreKey.store_signed_prekey(session, account_id, signedPreKeyId, timestamp, record_data)

    async def containsSignedPreKey(self, session: AsyncSession, account_id: int, signedPreKeyId: int) -> bool:
        return await SignedPreKey.contains_signed_prekey(session, account_id, signedPreKeyId)

    async def removeSignedPreKey(self, session: AsyncSession, account_id: int, signedPreKeyId: int) -> None:
        return await SignedPreKey.remove_signed_prekey(session, account_id, signedPreKeyId)


class SqlSessionStore(BaseStore):
    """
    Session store backed by SQLAlchemy.
    """

    async def loadSession(self, session: AsyncSession, account_id: int, account: int, deviceId: int) -> SessionRecord:
        return await SessionKey.load_session(session, account_id, account, deviceId)

    async def getSubDeviceSessions(self, session: AsyncSession, account_id: int, recipient: int) -> List[int]:
        return await SessionKey.get_sub_device_sessions(session, account_id, recipient)

    async def storeSession(self, session: AsyncSession, account_id: int, recipient: int, deviceId: int, sessionRecord: SessionRecord) -> None:
        record_data = sessionRecord.serialize()
        return await SessionKey.store_session(session, account_id, recipient, deviceId, record_data)

    async def containsSession(self, session: AsyncSession, account_id: int, recipient: int, deviceId: int) -> bool:
        return await SessionKey.contains_session(session, account_id, recipient, deviceId)

    async def containsSessionBulk(self, session: AsyncSession, account_id: int, usernames: list[tuple[int,int]]) -> List[bool]:
        return await SessionKey.contains_session_bulk(session, account_id, usernames)

    async def deleteSession(self, session: AsyncSession, account_id: int, recipient: int, deviceId: int) -> None:
        return await SessionKey.delete_session(session, account_id, recipient, deviceId)

    async def deleteAllSessions(self, session: AsyncSession, account_id: int, recipient: int) -> None:
        return await SessionKey.delete_all_sessions(session, account_id, recipient)

    async def getAllAccounts(self, session: AsyncSession, account_id: int, recipient: int) -> List[str]:
        return await SessionKey.get_all_accounts(session, account_id, recipient)
    
    async def get_all_session_usernames(self, session: AsyncSession, account_id: int, recipient: int) -> List[str]:
        """
        Obtém todos os usernames de sessão relacionados a um recipient.
        Similar ao getAllAccounts mas retorna lista de JIDs completos.

        :param recipient: ID do recipient
        :return: Lista de JIDs de sessão
        """
        return await SessionKey.get_all_accounts(session, account_id, recipient)


class SqlSenderKeyStore(BaseStore):
    """
    SenderKey store backed by SQLAlchemy.
    """

    async def storeSenderKey(self, session: AsyncSession, account_id: int, senderKeyName, senderKeyRecord) -> None:
        group_id = senderKeyName.getGroupId()
        sender_id = senderKeyName.getSender().getName()
        serialized = senderKeyRecord.serialize()
        return await SenderKey.store_sender_key(session, account_id, group_id, sender_id, serialized)

    async def loadSenderKey(self, session: AsyncSession, account_id: int, senderKeyName):
        group_id = senderKeyName.getGroupId()
        sender_id = senderKeyName.getSender().getName()
        return await SenderKey.load_sender_key(session, account_id, group_id, sender_id)


class SqlPollStore(BaseStore):
    """
    Poll store backed by SQLAlchemy.
    Exposed via SqlAxolotlStore.pollStore for compatibility with existing code.
    """

    async def deletePoll(self, session: AsyncSession, account_id: int, poll_msg_id: int) -> None:
        return await Poll.delete_poll(session, account_id, poll_msg_id)

    async def storePoll(self, session: AsyncSession, account_id: int, poll_msg_id: int, name: str, enc_key: bytes, options: List[str]) -> None:
        return await Poll.store_poll(session, account_id, poll_msg_id, name, enc_key, options)

    async def decryptOptions(self, session: AsyncSession, account_id: int, poll_msg_id: int, option_sha256_list: List[bytes]) -> List[str]:
        return await Poll.decrypt_options(session, account_id, poll_msg_id, option_sha256_list)

    async def getPollEncKey(self, session: AsyncSession, account_id: int, poll_msg_id: int) -> Optional[bytes]:
        return await Poll.get_poll_enc_key(session, account_id, poll_msg_id)


class SqlTaskMsgStore(BaseStore):
    """
    TaskMsg store backed by SQLAlchemy.
    Port of LiteTaskMsgStore.
    """

    async def setTaskMsg(self, session: AsyncSession, account_id: int, msg_id: str, task_id: str, src: str, dst: str) -> None:

        return await TaskMsg.store_task_msg(session, account_id, msg_id, task_id, src, dst)
       

    async def getTaskMsg(self, session: AsyncSession, account_id: int, msg_id: str) -> Optional[dict]:
        """
        Retorna informações da mensagem de tarefa.
        """

        return await TaskMsg.get_task_msg(session, account_id, msg_id)

    async def getMsgTaskByResponseMsg(self, session: AsyncSession, account_id: int, sender: str, receive: str) -> Optional[str]:
        """
        Busca task_id baseado em mensagem de resposta (sender/receive).
        """

        return await TaskMsg.get_msg_task_by_response_msg(session, account_id, sender, receive)

    async def delExpiredTaskMsg(self, session: AsyncSession, account_id: int) -> int:
        """
        Remove mensagens de tarefa expiradas.
        Retorna número de registros removidos.
        """
        return await TaskMsg.del_expired_task_msg(session, account_id)


class SqlAppStateStore(BaseStore):
    """
    AppState key store backed by SQLAlchemy.
    """

    async def addAppStateKeys(self, session: AsyncSession, account_id: int, keys) -> None:
        return await AppStateKey.add_app_state_keys(session, account_id, keys)

    async def getOneAppStateKey(self, session: AsyncSession, account_id: int):
        return await AppStateKey.get_one_app_state_key(session, account_id)

    async def getAppStateKey(self, session: AsyncSession, account_id: int, key_id: bytes):
        return await AppStateKey.get_app_state_key(session, account_id, key_id)

    async def deleteAppStateKey(self, session: AsyncSession, account_id: int, key_id: bytes) -> None:
        return await AppStateKey.delete_app_state_key(session, account_id, key_id)


class SqlContactStore(BaseStore):
    """
    Contact store backed by SQLAlchemy.
    """

    async def addContact(self, session: AsyncSession, account_id: int, jid: str, name: Optional[str] = None):
        return await Contact.add_contact(session, account_id, jid, name)

    async def findContact(self, session: AsyncSession, account_id: int, jid: str):
        return await Contact.find_contact(session, account_id, jid)

    async def isNewContact(self, session: AsyncSession, account_id: int, jid: str) -> bool:
        return await Contact.is_new_contact(session, account_id, jid)

    async def removeContact(self, session: AsyncSession, account_id: int, jid: str) -> bool:
        return await Contact.remove_contact(session, account_id, jid)

    async def getAllContact(self, session: AsyncSession, account_id: int):
        return await Contact.get_all_contacts(session, account_id)


class SqlBroadcastStore(BaseStore):
    """
    Broadcast store backed by SQLAlchemy.
    """

    async def addBroadcast(self, session: AsyncSession, account_id: int, jids, senderJid, name=None):
        return await Broadcast.add_broadcast(session, account_id, jids, senderJid, name)

    async def findParticipantsByBcid(self, session: AsyncSession, account_id: int, bcid: str):
        return await Broadcast.find_participants_by_bcid(session, account_id, bcid)


class SqlTrustedContactStore(BaseStore):
    """
    Trusted contact store backed by SQLAlchemy.
    """

    async def updateTrustedContact(self, session: AsyncSession, account_id: int, jid: str, tctoken: Optional[bytes] = None) -> bool:
        return await TrustedContact.update_trusted_contact(session, account_id, jid, tctoken)

    async def getTcToken(self, session: AsyncSession, account_id: int, jid: str) -> Optional[bytes]:
        return await TrustedContact.get_tc_token(session, account_id, jid)

    async def removeTrustedContact(self, session: AsyncSession, account_id: int, jid: str) -> bool:
        return await TrustedContact.remove_trusted_contact(session, account_id, jid)


class SqlAxolotlStore(AxolotlStore):
    """
    Axolotl store implementation backed by MySQL/SQLAlchemy.

    It wraps the per‑table stores above and exposes the same public surface
    as LiteAxolotlStore so that AxolotlManager and the rest of the stack
    can work unchanged.
    
    IMPORTANT: This store uses thread-local sessions for thread-safe isolation.
    Each thread gets its own session, preventing concurrent operation errors.
    The session is automatically managed via thread-local storage.
    
    The store uses AsyncSessionMaker to create sessions on demand.
    """

    def __init__(self, username: str, account_id: int, session_maker: Optional[AsyncSessionMaker] = None):
        """
        :param username: phone / account identifier (same as AxolotlManager.username)
        :param account_id: Account ID (required)
        :param session_maker: AsyncSessionMaker instance (optional, will use default if None)
        """
        if session_maker is None:
            from ..db.config.engine import AsyncSessionMaker
            session_maker = AsyncSessionMaker
        
        self._username = username
        self._session_maker = session_maker
        self._account_id: Optional[int] = account_id
        self._closed = False
        # Sub-stores serão criados quando necessário
        self._sub_stores_initialized = False
        # Lock para proteger inicialização de sub-stores (evita race conditions)
        import threading
        self._init_lock = threading.RLock()

    @asynccontextmanager
    async def _get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Obtém uma nova sessão assíncrona usando o AsyncSessionMaker.
        
        Returns:
            AsyncSession: Sessão assíncrona
        """
        if self._closed:
            raise RuntimeError("SqlAxolotlStore foi fechado. Não é possível reutilizar.")
        
        async with self._session_maker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            else:
                await session.commit()

    async def _get_account(self, session: AsyncSession) -> models.Account:
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
            account = await Account.get_or_create_account(session, self._username)
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
        result = await session.execute(select(models.Account).filter_by(id=self._account_id))
        account = result.scalar_one_or_none()

        # Se não encontrou, limpa cache e recria
        if account is None:
            logger.warning(
                f"Account {self._account_id} não encontrado para username={self._username}, "
                f"limpando cache e recriando..."
            )
            self._account_id = None
            account = await Account.get_or_create_account(session, self._username)
            self._account_id = account.id

        # Validação de isolamento: garante que o account corresponde ao username
        if account.phone != self._username:
            logger.error(
                f"[ISOLATION] Account ID {account.id} não corresponde ao username {self._username} | "
                f"account.phone={account.phone}"
            )
            # Limpa cache e recria para corrigir
            self._account_id = None
            account = await Account.get_or_create_account(session, self._username)
            self._account_id = account.id

        logger.debug(f"get_account(username={self._username}, account_id={account.id})")
        return account
    
    async def setup(self):
        """
        Cria sub-stores se ainda não foram inicializados.
        Cada sub-store recebe a sessão thread-local atual.
        Thread-safe: usa lock para evitar race conditions.
        
        Args:
            db: Sessão thread-local atual
            account: Account associado
        """
        async with self._get_session() as session:
            account = await self._get_account(session)
            self._account_id = account.id

            # Cria sub-stores pela primeira vez
            self.identityKeyStore = SqlIdentityKeyStore()
            await self.identityKeyStore.initialize(session, self._account_id)

            self.preKeyStore = SqlPreKeyStore()
            self.signedPreKeyStore = SqlSignedPreKeyStore()
            self.sessionStore = SqlSessionStore()
            self.senderKeyStore = SqlSenderKeyStore()
            self.pollStore = SqlPollStore()
            self.appStateStore = SqlAppStateStore()
            self.contactStore = SqlContactStore()
            self.broadcastStore = SqlBroadcastStore()
            self.trustedContactStore = SqlTrustedContactStore()
            self.taskMsgStore = SqlTaskMsgStore()


            self._sub_stores_initialized = True

        
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


    async def setPreKeysAsSent(self, prekeyIds: List[int]):
        logger.debug("SqlAxolotlStore.setPreKeysAsSent: starting")
        async with self._get_session() as db:
            return await self.preKeyStore.setAsSent(db, self._account_id, prekeyIds)

    async def loadUnsentPendingPreKeys(self):
        logger.debug("SqlAxolotlStore.loadUnsentPendingPreKeys: starting")
        async with self._get_session() as db:
            return await self.preKeyStore.loadUnsentPendingPreKeys(db, self._account_id)

    # Identity store facade
    async def getIdentityKeyPair(self):
        logger.debug("SqlAxolotlStore.getIdentityKeyPair: starting")
        async with self._get_session() as db:
            result = await self.identityKeyStore.getIdentityKeyPair(self._account_id, db)
            logger.debug(f"SqlAxolotlStore.getIdentityKeyPair: result={'found' if result else 'not found'}")
            return result

    async def getLocalRegistrationId(self):
        async with self._get_session() as db:
            return await self.identityKeyStore.getLocalRegistrationId(self._account_id, db)

    async def saveIdentity(self, recipientId, deviceId, identityKey):
        async with self._get_session() as db:
            await self.identityKeyStore.saveIdentity(db, self._account_id, recipientId, deviceId, identityKey)

    async def isTrustedIdentity(self, recipientId, deviceId, identityKey):
        async with self._get_session() as db:
            return await self.identityKeyStore.isTrustedIdentity(db, self._account_id, recipientId, deviceId, identityKey)

    # Helper for migration/import flows: update local identity row
    async def updateLocalIdentityKeys(self, registration_id, public_key, private_key, deviceid: int = 0) -> None:
        """
        Updates the local identity row (recipient_id = -1) with the provided
        registration_id, public_key and private_key.

        This is used by legacy import/export flows that previously updated
        the SQLite 'identities' table directly.
        """
        logger.debug(f"SqlAxolotlStore.: registration_id={registration_id}, deviceid={deviceid}")
        async with self._get_session() as db:
            try:
                logger.debug("SqlAxolotlStore.: querying existing identity row")
                result = await db.execute(
                    select(Identity).filter(
                        models.Identity.account_id == self._account_id,
                        models.Identity.recipient_id == -1,
                    )
                )
                row = result.scalar_one_or_none()
                if row is None:
                    logger.debug("SqlAxolotlStore.: creating new identity row")
                    row = Identity(
                        account_id=self._account_id,
                        recipient_id=-1,
                        recipient_type=0,
                        device_id=deviceid,
                    )
                    db.add(row)
                else:
                    logger.debug("SqlAxolotlStore.: updating existing identity row")

                row.registration_id = registration_id
                row.public_key = public_key
                row.private_key = private_key
                row.device_id = deviceid
                await db.commit()
                logger.debug(f"SqlAxolotlStore.: successfully updated local identity keys for account {self._account_id}")
            except Exception as e:
                await db.rollback()
                logger.error(f"SqlAxolotlStore.: error updating local identity keys: {e}", exc_info=True)
                raise

    # PreKey store facade
    async def loadPreKey(self, preKeyId):
        async with self._get_session() as db:

            return await self.preKeyStore.loadPreKey(db, self._account_id, preKeyId)

    async def loadPreKeys(self):
        logger.debug("SqlAxolotlStore.loadPreKeys: starting")
        async with self._get_session() as db:

            result = await self.preKeyStore.loadPendingPreKeys(db, self._account_id)
            logger.debug(f"SqlAxolotlStore.loadPreKeys: loaded {len(result)} unsent prekeys")
            return result

    async def storePreKey(self, preKeyId, preKeyRecord):
        logger.debug(f"SqlAxolotlStore.storePreKey: preKeyId={preKeyId}")
        async with self._get_session() as db:

            await self.preKeyStore.storePreKey(db, self._account_id, preKeyId, preKeyRecord)
            logger.debug(f"SqlAxolotlStore.storePreKey: successfully stored preKeyId={preKeyId}")

    async def storePreKeys(self, prekeys: List[Tuple[int, PreKeyRecord]]) -> None:
        """
        Armazena múltiplos prekeys em uma única transação (bulk insert).
        
        Args:
            prekeys: Lista de tuplas (preKeyId, preKeyRecord)
        """
        logger.debug(f"SqlAxolotlStore.storePreKeys: storing {len(prekeys)} prekeys in bulk")
        async with self._get_session() as db:

            await self.preKeyStore.storePreKeys(db, self._account_id, prekeys)
            logger.debug(f"SqlAxolotlStore.storePreKeys: successfully stored {len(prekeys)} prekeys")

    async def containsPreKey(self, preKeyId):
        async with self._get_session() as db:

            return await self.preKeyStore.containsPreKey(db, self._account_id, preKeyId)

    async def removePreKey(self, preKeyId):
        async with self._get_session() as db:

            await self.preKeyStore.removePreKey(db, self._account_id, preKeyId)

    async def removeAllPreKeys(self):
        async with self._get_session() as db:

            await self.preKeyStore.clear(db, self._account_id)

    # Session store facade
    async def loadSession(self, account, deviceId):
        logger.debug(f"SqlAxolotlStore.loadSession: account={account}, deviceId={deviceId}")
        async with self._get_session() as db:

            result = await self.sessionStore.loadSession(db, self._account_id, account, deviceId)
            logger.debug(f"SqlAxolotlStore.loadSession: loaded session, has_data={len(result.serialize()) > 0}")
            return result

    async def getSubDeviceSessions(self, account):
        async with self._get_session() as db:

            return await self.sessionStore.getSubDeviceSessions(db, self._account_id, account)

    async def storeSession(self, account, deviceId, sessionRecord):
        logger.debug(f"SqlAxolotlStore.storeSession: account={account}, deviceId={deviceId}")
        async with self._get_session() as db:

            await self.sessionStore.storeSession(db, self._account_id, account, deviceId, sessionRecord)
            logger.debug(f"SqlAxolotlStore.storeSession: successfully stored session for account={account}, deviceId={deviceId}")

    async def containsSession(self, account, deviceId):
        logger.debug(f"SqlAxolotlStore.containsSession: account={account}, deviceId={deviceId}")
        async with self._get_session() as db:
            return await self.sessionStore.containsSession(db, self._account_id, account, deviceId)


    async def containsSessionBulk(self, usernames):
        async with self._get_session() as db:
            return await self.sessionStore.containsSessionBulk(db, self._account_id, usernames)

    async def deleteSession(self, account, deviceId):
        async with self._get_session() as db:

            await self.sessionStore.deleteSession(db, self._account_id, account, deviceId)

    async def deleteAllSessions(self, account):
        async with self._get_session() as db:

            await self.sessionStore.deleteAllSessions(db, self._account_id, account)

    async def getAllAccounts(self, account):
        async with self._get_session() as db:

            return await self.sessionStore.getAllAccounts(db, self._account_id, account)
    
    async def get_all_session_usernames(self, account):
        """
        Obtém todos os usernames de sessão relacionados.

        :param account: ID do recipient
        :return: Lista de JIDs de sessão
        """
        async with self._get_session() as db:

            return await self.sessionStore.get_all_session_usernames(db, self._account_id, account)

    # Signed prekey facade

    async def loadMaxPreKeyId(self):
        async with self._get_session() as db:
            return await self.preKeyStore.loadMaxPreKeyId(db, self._account_id)

    async def loadSignedPreKey(self, signedPreKeyId):
        logger.debug(f"SqlAxolotlStore.loadSignedPreKey: signedPreKeyId={signedPreKeyId}")
        async with self._get_session() as db:

            result = await self.signedPreKeyStore.loadSignedPreKey(db, self._account_id, signedPreKeyId)
            logger.debug(f"SqlAxolotlStore.loadSignedPreKey: loaded signed prekey {signedPreKeyId}")
            return result

    async def loadSignedPreKeys(self):
        async with self._get_session() as db:

            return await self.signedPreKeyStore.loadSignedPreKeys(db, self._account_id)

    async def storeSignedPreKey(self, signedPreKeyId, signedPreKeyRecord):
        logger.debug(f"SqlAxolotlStore.storeSignedPreKey: signedPreKeyId={signedPreKeyId}")
        async with self._get_session() as db:

            await self.signedPreKeyStore.storeSignedPreKey(db, self._account_id, signedPreKeyId, signedPreKeyRecord)
            logger.debug(f"SqlAxolotlStore.storeSignedPreKey: successfully stored signed prekey {signedPreKeyId}")

    async def containsSignedPreKey(self, signedPreKeyId):
        async with self._get_session() as db:

            return await self.signedPreKeyStore.containsSignedPreKey(db, self._account_id, signedPreKeyId)

    async def removeSignedPreKey(self, signedPreKeyId):
        async with self._get_session() as db:

            await self.signedPreKeyStore.removeSignedPreKey(db, self._account_id, signedPreKeyId)

    # Sender key facade
    async def loadSenderKey(self, senderKeyName):
        group_id = senderKeyName.getGroupId()
        sender_id = senderKeyName.getSender().getName()
        logger.debug(f"SqlAxolotlStore.loadSenderKey: group_id={group_id}, sender_id={sender_id}")
        async with self._get_session() as db:

            result = await self.senderKeyStore.loadSenderKey(db, self._account_id, senderKeyName)
            logger.debug(f"SqlAxolotlStore.loadSenderKey: loaded sender key, has_data={len(result.serialize()) > 0}")
            return result

    async def storeSenderKey(self, senderKeyName, senderKeyRecord):
        group_id = senderKeyName.getGroupId()
        sender_id = senderKeyName.getSender().getName()
        logger.debug(f"SqlAxolotlStore.storeSenderKey: group_id={group_id}, sender_id={sender_id}")
        async with self._get_session() as db:

            await self.senderKeyStore.storeSenderKey(db, self._account_id, senderKeyName, senderKeyRecord)
            logger.debug(f"SqlAxolotlStore.storeSenderKey: successfully stored sender key for group_id={group_id}, sender_id={sender_id}")

    # App state keys
    async def addAppStateKeys(self, keys):
        async with self._get_session() as db:

            return await self.appStateStore.addAppStateKeys(db, self._account_id, keys)

    async def getOneAppStateKey(self):
        async with self._get_session() as db:

            return await self.appStateStore.getOneAppStateKey(db, self._account_id)

    async def getAppStateKey(self, key_id):
        async with self._get_session() as db:

            return await self.appStateStore.getAppStateKey(db, self._account_id, key_id)

    async def removeAppStateKey(self, key_id):
        async with self._get_session() as db:

            return await self.appStateStore.deleteAppStateKey(db, self._account_id, key_id)

    # Contacts
    async def addContact(self, jid):
        async with self._get_session() as db:

            return await self.contactStore.addContact(db, self._account_id, jid, "")

    async def removeContact(self, jid):
        async with self._get_session() as db:

            return await self.contactStore.removeContact(db, self._account_id, jid)

    async def getAllContact(self):
        async with self._get_session() as db:

            return await self.contactStore.getAllContact(db, self._account_id)

    async def findContact(self, jid):
        async with self._get_session() as db:

            return await self.contactStore.findContact(db, self._account_id, jid)

    async def isNewContact(self, jid):
        async with self._get_session() as db:

            return await self.contactStore.isNewContact(db, self._account_id, jid)

    # Broadcasts
    async def addBroadcast(self, jids, senderJid, name=None):
        async with self._get_session() as db:

            return await self.broadcastStore.addBroadcast(db, self._account_id, jids, senderJid, name)

    async def findParticipantsByBcid(self, bcid):
        async with self._get_session() as db:

            return await self.broadcastStore.findParticipantsByBcid(db, self._account_id, bcid)

    # Trusted contacts
    async def updateTrustedContact(self, jid, tctoken):
        async with self._get_session() as db:

            return await self.trustedContactStore.updateTrustedContact(db, self._account_id, jid, tctoken)

    async def getTcToken(self, jid):
        async with self._get_session() as db:

            return await self.trustedContactStore.getTcToken(db, self._account_id, jid)

    # Poll store facade
    async def deletePoll(self, poll_msg_id):
        async with self._get_session() as db:

            return await self.pollStore.deletePoll(db, self._account_id, poll_msg_id)

    async def storePoll(self, poll_msg_id, name, enc_key, options):
        async with self._get_session() as db:

            return await self.pollStore.storePoll(db, self._account_id, poll_msg_id, name, enc_key, options)

    async def decryptOptions(self, poll_msg_id, option_sha256_list):
        async with self._get_session() as db:

            return await self.pollStore.decryptOptions(db, self._account_id, poll_msg_id, option_sha256_list)

    async def getPollEncKey(self, poll_msg_id):
        async with self._get_session() as db:

            return await self.pollStore.getPollEncKey(db, self._account_id, poll_msg_id)

    # TaskMsg store facade
    async def setTaskMsg(self, msg_id, task_id, src, dst):
        async with self._get_session() as db:

            return await self.taskMsgStore.setTaskMsg(db, self._account_id, msg_id, task_id, src, dst)

    async def getTaskMsg(self, msg_id):
        async with self._get_session() as db:

            return await self.taskMsgStore.getTaskMsg(db, self._account_id, msg_id)

    async def getMsgTaskByResponseMsg(self, sender, receive):
        async with self._get_session() as db:

            return await self.taskMsgStore.getMsgTaskByResponseMsg(db, self._account_id, sender, receive)

    async def delExpiredTaskMsg(self):
        async with self._get_session() as db:

            return await self.taskMsgStore.delExpiredTaskMsg(db, self._account_id)



