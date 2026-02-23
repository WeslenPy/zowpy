import asyncio
from ..axolotl.util.keyhelper import KeyHelper
from ..axolotl.identitykeypair import IdentityKeyPair
from ..axolotl.groups.senderkeyname import SenderKeyName
from ..axolotl.axolotladdress import AxolotlAddress
from ..axolotl.sessioncipher import SessionCipher
from ..axolotl.groups.groupcipher import GroupCipher
from ..axolotl.groups.groupsessionbuilder import GroupSessionBuilder
from ..axolotl.sessionbuilder import SessionBuilder
from ..axolotl.protocol.prekeywhispermessage import PreKeyWhisperMessage
from ..axolotl.protocol.whispermessage import WhisperMessage
from ..axolotl.state.prekeybundle import PreKeyBundle
from ..axolotl.exceptions import (
    UntrustedIdentityException,
    InvalidMessageException,
    DuplicateMessageException,
    InvalidKeyIdException,
    NoSessionException,
)
from ..axolotl.protocol.senderkeydistributionmessage import SenderKeyDistributionMessage
from ..axolotl.state.axolotlstore import AxolotlStore
from ..db.store import SqlAxolotlStore
from ..axolotl import exceptions
import random
import sys
import base64
from ..utils.tools import WATools

from loguru import logger


class AxolotlManager(object):

    COUNT_GEN_PREKEYS = 812
    THRESHOLD_REGEN = 10
    MAX_SIGNED_PREKEY_ID = 16777215

    def __init__(self, store, username):
        """
        :param store:
        :type store: AxolotlStore
        :param username:
        :type username: str
        """
        self._username = username # type: str
        self._store:SqlAxolotlStore = store # type: LiteAxolotlStore
        # Initialize identity and registration_id asynchronously later
        self._identity = None  # type: IdentityKeyPair
        self._registration_id = None  # type: int | None

        self._group_session_builder = None  # type: GroupSessionBuilder

    async def initialize(self):
        """Initialize async components"""
        self._identity = await self._store.getIdentityKeyPair()
        self._registration_id = await self._store.getLocalRegistrationId()


        logger.debug(f"Initialized AxolotlManager [username={self._username}, registration_id={self._registration_id}, identity={self._identity}]")
        logger.debug(f"Identity key pair: {type(self._identity)}")
        logger.debug(f"Registration ID: {type(self._registration_id)}")

        assert self._registration_id is not None
        assert self._identity is not None

        # GroupSessionBuilder precisa de senderKeyStore síncrono
        self._group_session_builder = GroupSessionBuilder(self._store)
        self._session_ciphers = {} # type: dict[str, SessionCipher]
        self._group_ciphers = {} # type: dict[str, GroupCipher]
        # logger.debug(f"Initialized AxolotlManager [username={self._username}, db={store}]")


    @property
    def registration_id(self):
        return self._registration_id

    @property
    def identity(self):
        return self._identity
    
    async def get_all_accounts(self,username):
        ret = await self._store.getAllAccounts(username)
        return ret

    async def level_prekeys(self, force=False):
        logger.debug(f"level_prekeys(force={force})")
        # Run potentially blocking operations in thread pool
        len_pending_prekeys = len(await self._store.loadPreKeys())
        logger.debug(f"len(pending_prekeys) = {len_pending_prekeys}")

        if force or len_pending_prekeys < self.THRESHOLD_REGEN:
            count_gen = self.COUNT_GEN_PREKEYS
            max_prekey_id = await self._store.loadMaxPreKeyId()
            logger.info(f"Generating {count_gen} prekeys, current max_prekey_id={max_prekey_id}")
            prekeys = KeyHelper.generatePreKeys(max_prekey_id + 1, count_gen)
            logger.info(f"Storing {len(prekeys)} prekeys using bulk insert")
            
            # Bulk insert: prepara lista de tuplas (preKeyId, preKeyRecord)
            prekey_tuples = [(key.getId(), key) for key in prekeys]
            
            # Armazena todos os prekeys em uma única transação
            await self._store.storePreKeys(prekey_tuples)
            logger.info(f"Successfully stored {len(prekeys)} prekeys in bulk")
            return prekeys

        return []


    async def load_unsent_prekeys(self):
        logger.debug("load_unsent_prekeys")
        # Usa o método do store que já gerencia a sessão de banco
        unsent = await self._store.loadUnsentPendingPreKeys()
        if unsent and len(unsent) > 0:
            logger.info(f"Loaded {len(unsent)} unsent prekeys")
        return unsent if unsent else []

    async def set_prekeys_as_sent(self, prekeyIds):
        """
        :param prekeyIds:
        :type prekeyIds: list
        :return:
        :rtype:
        """
        logger.debug(f"set_prekeys_as_sent(prekeyIds=[{len(prekeyIds)} prekeyIds])")
        await self._store.setPreKeysAsSent([prekey.getId() for prekey in prekeyIds])

    async def generate_signed_prekey(self):
        logger.debug("generate_signed_prekey")
        if self._identity is None:
            await self.initialize()
        latest_signed_prekey = await self.load_latest_signed_prekey(generate=False)
        if latest_signed_prekey is not None:
            if latest_signed_prekey.getId() == self.MAX_SIGNED_PREKEY_ID:
                new_signed_prekey_id = (self.MAX_SIGNED_PREKEY_ID / 2) + 1
            else:
                new_signed_prekey_id = latest_signed_prekey.getId() + 1
        else:
            new_signed_prekey_id = random.randint(0,800)
        signed_prekey = KeyHelper.generateSignedPreKey(self._identity, new_signed_prekey_id)
        await self._store.storeSignedPreKey(signed_prekey.getId(), signed_prekey)
        return signed_prekey

    async def load_latest_signed_prekey(self, generate=False):
        logger.debug("load_latest_signed_prekey")
        signed_prekeys = await self._store.loadSignedPreKeys()
        if len(signed_prekeys):
            return signed_prekeys[-1]

        return await self.generate_signed_prekey() if generate else None
    
    def _get_session_cipher(self, username,deviceid=0):
        logger.debug(f"get_session_cipher(username={username})")
        key = "%s-%d" % (username,deviceid)        
        if key in self._session_ciphers:
            session_cipher = self._session_ciphers[key]
        else:
            # Cria wrapper síncrono do store para uso com SessionCipher
            session_cipher= SessionCipher(self._store,self._store,self._store,self._store, username, deviceid)
            self._session_ciphers[key] = session_cipher
        return session_cipher

    def _get_group_cipher(self, groupid, username):
        logger.debug(f"get_group_cipher(groupid={groupid}, username={username})")
        senderkeyname = SenderKeyName(groupid, AxolotlAddress(username, 0))
        if senderkeyname in self._group_ciphers:
            group_cipher = self._group_ciphers[senderkeyname]
        else:
            # GroupCipher precisa de um senderKeyStore síncrono
            # Cria wrapper síncrono que também funciona como SenderKeyStore
            group_cipher = GroupCipher(self._store, senderkeyname)
            self._group_ciphers[senderkeyname] = group_cipher
        return group_cipher

    def _generate_random_padding(self):
        logger.debug("generate_random_padding")
        num = random.randint(1,255)
        return bytes(bytearray([num] * num))

    def _unpad(self, data):
        padding_byte = data[-1] if type(data[-1]) is int else ord(data[-1]) # bec inconsistent API?
        padding = padding_byte & 0xFF
        return data[:-padding]

    async def encrypt(self, username, message):
        # to avoid the hassle of encoding issues and associated unnecessary crashes,
        # don't log the message content.
        # see https://github.com/tgalal/yowsup/issues/2732
        logger.debug(f"encrypt(username={username}, message=[omitted])")
        """
        :param username:
        :type username: str
        :param data:
        :type data: bytes
        :return:
        :rtype:
        """
        recipientId,a,deviceid = WATools.jidDecode(username)

        cipher = self._get_session_cipher(recipientId,deviceid)
        return await cipher.encrypt(message + self._generate_random_padding())
    
    async def decrypt_pkmsg(self, senderid, data, unpad):
        logger.debug(f"decrypt_pkmsg(senderid={senderid}, data=(omitted), unpad={unpad})")
        pkmsg = PreKeyWhisperMessage(serialized=data)

        recipientId,a,deviceid = WATools.jidDecode(senderid)
        try:
            cipher = self._get_session_cipher(recipientId,deviceid)
            plaintext = await cipher.decryptPkmsg(pkmsg)
            return self._unpad(plaintext) if unpad else plaintext
        except NoSessionException as e:
            raise exceptions.NoSessionException(str(e) if str(e) else "No session")
        except InvalidKeyIdException as e:
            raise exceptions.InvalidKeyIdException(str(e) if str(e) else "Invalid key ID")
        except InvalidMessageException as e:
            # Preserva a mensagem original da exceção (pode conter "Bad Mac!" ou outras informações)
            raise exceptions.InvalidMessageException(str(e) if str(e) else "Invalid message")
        except DuplicateMessageException as e:
            raise exceptions.DuplicateMessageException(str(e) if str(e) else "Duplicate message")


    async def decrypt_msg(self, senderid, data, unpad):
        logger.debug(f"decrypt_msg(senderid={senderid}, data=[omitted], unpad={unpad})")
        msg = WhisperMessage(serialized=data)
        recipientId,a,deviceid = WATools.jidDecode(senderid)

        try:
            cipher = self._get_session_cipher(recipientId,deviceid)
            plaintext = await cipher.decryptMsg(msg)

            return self._unpad(plaintext) if unpad else plaintext
        except NoSessionException as e:
            raise exceptions.NoSessionException(str(e) if str(e) else "No session")
        except InvalidKeyIdException as e:
            raise exceptions.InvalidKeyIdException(str(e) if str(e) else "Invalid key ID")
        except InvalidMessageException as e:
            # Preserva a mensagem original da exceção (pode conter "Bad Mac!" ou outras informações)
            # Isso ajuda no diagnóstico quando a exceção é tratada em camadas superiores
            raise exceptions.InvalidMessageException(str(e) if str(e) else "Invalid message")
        except DuplicateMessageException as e:
            raise exceptions.DuplicateMessageException(str(e) if str(e) else "Duplicate message")

    async def group_encrypt(self, groupid, message):
        """
        :param groupid:
        :type groupid: str
        :param message:
        :type message: bytes
        :return:
        :rtype:
        """
        # to avoid the hassle of encoding issues and associated unnecessary crashes,
        # don't log the message content.
        # see https://github.com/tgalal/yowsup/issues/2732
        logger.debug(f"group_encrypt(groupid={groupid}, message=[omitted])")
        group_cipher = self._get_group_cipher(groupid, self._username)
        try:
            return await group_cipher.encrypt(message + self._generate_random_padding())
        except NoSessionException as e:
            raise exceptions.NoSessionException(str(e) if str(e) else "No sender key for group")

    async def group_decrypt(self, groupid, participantid, data):
        logger.debug(f"group_decrypt(groupid={groupid}, participantid={participantid}, data=[omitted])")
        group_cipher = self._get_group_cipher(groupid, participantid)
        try:
            plaintext = await group_cipher.decrypt(data)
            plaintext = self._unpad(plaintext)
            return plaintext
        except NoSessionException as e:
            raise exceptions.NoSessionException(str(e) if str(e) else "No session")
        except DuplicateMessageException as e:
            raise exceptions.DuplicateMessageException(str(e) if str(e) else "Duplicate message")
        except InvalidMessageException as e:
            raise exceptions.InvalidMessageException(str(e) if str(e) else "Invalid message")

    async def group_create_skmsg(self, groupid):
        logger.debug(f"group_create_skmsg(groupid={groupid})")
        senderKeyName = SenderKeyName(groupid, AxolotlAddress(self._username, 0))
        return await self._group_session_builder.create(senderKeyName)

    async def group_create_session(self, groupid, participantid, skmsgdata):
        """
        :param groupid:
        :type groupid: str
        :param participantid:
        :type participantid: str
        :param skmsgdata:
        :type skmsgdata: bytearray
        :return:
        :rtype:
        """
        logger.debug(f"group_create_session(groupid={groupid}, participantid={participantid}, skmsgdata=[omitted])")
        senderKeyName = SenderKeyName(groupid, AxolotlAddress(participantid, 0))
        senderkeydistributionmessage = SenderKeyDistributionMessage(serialized=skmsgdata)
        await self._group_session_builder.process(senderKeyName, senderkeydistributionmessage)

    async def create_session(self, username, prekeybundle, autotrust=False):
        """
        :param username:
        :type username: str
        :param prekeybundle:
        :type prekeybundle: PreKeyBundle
        :return:
        :rtype:
        """
        logger.debug(f"create_session(username={username}, prekeybundle=[omitted], autotrust={autotrust})")

        recipient,a,deviceid = WATools.jidDecode(username)

        # SessionBuilder agora é async
        session_builder = SessionBuilder(self._store, self._store, 
                                            self._store, self._store, 
                                            recipient, deviceid)
        try:
            await session_builder.processPreKeyBundle(prekeybundle)
        except UntrustedIdentityException as ex:
            if autotrust:
                await self.trust_identity(ex.getName(), ex.getIdentityKey())
            else:
                raise exceptions.UntrustedIdentityException(ex.getName(), ex.getIdentityKey())


    async def session_exists_bulk(self, usernames):
        """
        :param usernames:
        :type usernames: list
        :return:
        :rtype:
        """
        logger.debug(f"session_exists_bulk(usernames={usernames})")


        usernames_maps = []
        for username in usernames:
            jid = str(username).split('@')[0]
            recipient, a, deviceid = WATools.jidDecode(str(jid))
            # Normaliza recipient para int para consistência com recipient_id (BigInteger) no store
            try:
                recipient_id = int(recipient)
            except (ValueError, TypeError):
                recipient_id = recipient
            usernames_maps.append((recipient_id, deviceid))

        return await self._store.containsSessionBulk(usernames_maps)

    async def session_exists(self, username):
        """
        :param username:
        :type username: str
        :return:
        :rtype:
        """
        logger.debug(f"session_exists({username})?")
        recipient,a,deviceid = WATools.jidDecode(username)

        logger.debug(f"session_exists(recipient={recipient}, deviceid={deviceid})")
        return await self._store.containsSession(recipient, deviceid)
    
    async def get_all_session_usernames(self,username):
        #获取一个用户名的所有关联终端的session，主要用来用来发消息
        logger.debug("get_all_session_usernames")
        return await self._store.get_all_session_usernames(username)

    async def load_senderkey(self, groupid):
        logger.debug(f"load_senderkey(groupid={groupid})")
        senderkeyname = SenderKeyName(groupid, AxolotlAddress(self._username, 0))
        return await self._store.loadSenderKey(senderkeyname)

    async def trust_identity(self, account ,identitykey):
        logger.debug(f"trust_identity(account={account}, identitykey=[omitted])")

        recipient,a,deviceid = WATools.jidDecode(account)
        await self._store.saveIdentity(recipient,deviceid,identitykey)



    async def get_all_contacts(self):
        return await self._store.getAllContact()

