# -*- coding: utf-8 -*-
import asyncio
from ..protocol.senderkeydistributionmessage import SenderKeyDistributionMessage
from ..invalidkeyidexception import InvalidKeyIdException
from ..invalidkeyexception import InvalidKeyException
from ..util.keyhelper import KeyHelper

def _run_async(coro):
    """Helper para executar corrotina em contexto síncrono"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Se já há um loop rodando, cria um novo
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        # Não há loop, cria um novo
        return asyncio.run(coro)

class GroupSessionBuilder:
    def __init__(self, senderKeyStore):
        self.senderKeyStore = senderKeyStore

    def process(self, senderKeyName, senderKeyDistributionMessage):
        """
        :type senderKeyName: SenderKeyName
        :type senderKeyDistributionMessage: SenderKeyDistributionMessage
        """
        senderKeyRecord = self.senderKeyStore.loadSenderKey(senderKeyName)
        senderKeyRecord.addSenderKeyState(senderKeyDistributionMessage.getId(),
                                          senderKeyDistributionMessage.getIteration(),
                                          senderKeyDistributionMessage.getChainKey(),
                                          senderKeyDistributionMessage.getSignatureKey())
        self.senderKeyStore.storeSenderKey(senderKeyName, senderKeyRecord)


    def create(self, senderKeyName):
        """
        :type senderKeyName: SenderKeyName
        """
        try:
            senderKeyRecord = self.senderKeyStore.loadSenderKey(senderKeyName);

            if senderKeyRecord.isEmpty() :
                senderKeyRecord.setSenderKeyState(_run_async(KeyHelper.generateSenderKeyId()),
                                                0,
                                                _run_async(KeyHelper.generateSenderKey()),
                                                _run_async(KeyHelper.generateSenderSigningKey()));
                self.senderKeyStore.storeSenderKey(senderKeyName, senderKeyRecord);

            state = senderKeyRecord.getSenderKeyState();

            return SenderKeyDistributionMessage(state.getKeyId(),
                                                state.getSenderChainKey().getIteration(),
                                                state.getSenderChainKey().getSeed(),
                                                state.getSigningKeyPublic());
        except (InvalidKeyException, InvalidKeyIdException) as e:
            raise AssertionError(e)


