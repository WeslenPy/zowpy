# -*- coding: utf-8 -*-

from ..invalidkeyidexception import InvalidKeyIdException
from ..invalidkeyexception import InvalidKeyException
from ..invalidmessageexception import InvalidMessageException
from ..duplicatemessagexception import DuplicateMessageException
from ..nosessionexception import NoSessionException
from ..protocol.senderkeymessage import SenderKeyMessage
from ..sessioncipher import AESCipher
from ..groups.state.senderkeystore import SenderKeyStore
class GroupCipher:
    def __init__(self, senderKeyStore, senderKeyName):
        """
        :type senderKeyStore: SenderKeyStore
        :type senderKeyName: SenderKeyName
        """
        self.senderKeyStore = senderKeyStore
        self.senderKeyName = senderKeyName

    async def encrypt(self, paddedPlaintext):
        """
        :type paddedPlaintext: bytes
        """
        try:
            record = await self.senderKeyStore.loadSenderKey(self.senderKeyName)
            senderKeyState = record.getSenderKeyState()
            senderKey = senderKeyState.getSenderChainKey().getSenderMessageKey()
            ciphertext = self.getCipherText(senderKey.getIv(), senderKey.getCipherKey(), paddedPlaintext)

            senderKeyMessage = SenderKeyMessage(senderKeyState.getKeyId(),
                                                senderKey.getIteration(),
                                                ciphertext,
                                                senderKeyState.getSigningKeyPrivate())

            senderKeyState.setSenderChainKey(senderKeyState.getSenderChainKey().getNext())
            await self.senderKeyStore.storeSenderKey(self.senderKeyName, record)

            return senderKeyMessage.serialize()
        except InvalidKeyIdException as e:
            raise NoSessionException(str(e) if str(e) else "No session")

    async def decrypt(self, senderKeyMessageBytes):
        """
        :type senderKeyMessageBytes: bytearray
        """
        try:
            record = await self.senderKeyStore.loadSenderKey(self.senderKeyName)
            if record.isEmpty():
                raise NoSessionException("No sender key for: %s" % self.senderKeyName)
            senderKeyMessage = SenderKeyMessage(serialized = bytes(senderKeyMessageBytes))
            senderKeyState = record.getSenderKeyState(senderKeyMessage.getKeyId())

            senderKeyMessage.verifySignature(senderKeyState.getSigningKeyPublic())

            senderKey = self.getSenderKey(senderKeyState, senderKeyMessage.getIteration())

            plaintext = self.getPlainText(senderKey.getIv(), senderKey.getCipherKey(), senderKeyMessage.getCipherText())

            await self.senderKeyStore.storeSenderKey(self.senderKeyName, record)

            return plaintext
        except (InvalidKeyException, InvalidKeyIdException) as e:
            raise InvalidMessageException(str(e) if str(e) else "Invalid key")

        except ValueError as e:
            raise InvalidMessageException(str(e) if str(e) else "Invalid value")

        except Exception as e:
            raise InvalidMessageException(str(e) if str(e) else "Invalid message")

    def getSenderKey(self, senderKeyState, iteration):
        senderChainKey = senderKeyState.getSenderChainKey()

        if senderChainKey.getIteration() > iteration:
            if senderKeyState.hasSenderMessageKey(iteration):
                return senderKeyState.removeSenderMessageKey(iteration)
            else:
                raise DuplicateMessageException("Received message with old counter: %s, %s" %
                                                (senderChainKey.getIteration(), iteration))

        if senderChainKey.getIteration() - iteration > 2000:
            raise InvalidMessageException("Over 2000 messages into the future!")

        while senderChainKey.getIteration() < iteration:
            senderKeyState.addSenderMessageKey(senderChainKey.getSenderMessageKey())
            senderChainKey = senderChainKey.getNext()

        senderKeyState.setSenderChainKey(senderChainKey.getNext())
        return senderChainKey.getSenderMessageKey()

    def getPlainText(self, iv, key, ciphertext):
        """
        :type iv: bytearray
        :type key: bytearray
        :type ciphertext: bytearray
        """
        try:
            cipher = AESCipher(key, iv)
            plaintext = cipher.decrypt(ciphertext)
            return plaintext
        except Exception as e:
            raise InvalidMessageException(str(e) if str(e) else "Decryption failed")

    def getCipherText(self, iv, key, plaintext):
        """
        :type iv: bytearray
        :type key: bytearray
        :type plaintext: bytearray
        """
        cipher = AESCipher(key, iv)
        return cipher.encrypt(plaintext)


