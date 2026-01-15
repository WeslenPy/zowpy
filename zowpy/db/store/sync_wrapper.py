"""
Sync Store Wrapper - Wrapper síncrono para stores assíncronos.

Converte chamadas async do store para síncronas para uso com SessionCipher.
"""

import asyncio
from typing import Optional
from loguru import logger

from ...axolotl.state.axolotlstore import AxolotlStore
from ...axolotl.state.sessionrecord import SessionRecord
from ...axolotl.state.prekeyrecord import PreKeyRecord
from ...axolotl.state.signedprekeyrecord import SignedPreKeyRecord
from ...axolotl.identitykey import IdentityKey
from ...axolotl.identitykeypair import IdentityKeyPair
from ...axolotl.groups.state.senderkeyrecord import SenderKeyRecord


class SyncStoreWrapper:
    """
    Wrapper síncrono para AxolotlStore assíncrono.
    
    Converte chamadas async para síncronas usando event loop.
    Usado pelo SessionCipher que espera métodos síncronos.
    """
    
    def __init__(self, async_store: AxolotlStore, loop: Optional[asyncio.AbstractEventLoop] = None):
        """
        Inicializa wrapper.
        
        Args:
            async_store: Store assíncrono a ser envolvido
            loop: Event loop a usar (usa loop atual se None)
        """
        self._async_store = async_store
        self._loop = loop
    
    def _run_async(self, coro):
        """
        Executa corrotina de forma síncrona.
        
        Args:
            coro: Corrotina a executar
        
        Returns:
            Resultado da corrotina
        """
        try:
            # Tenta obter loop atual
            loop = self._loop or asyncio.get_event_loop()
            
            # Se já estamos em um loop, usa run_coroutine_threadsafe
            if loop.is_running():
                # Cria um novo loop em thread separada ou usa executor
                import concurrent.futures
                import threading
                
                # Cria um novo loop em thread separada
                result = None
                exception = None
                
                def run_in_thread():
                    nonlocal result, exception
                    try:
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        result = new_loop.run_until_complete(coro)
                        new_loop.close()
                    except Exception as e:
                        exception = e
                
                thread = threading.Thread(target=run_in_thread)
                thread.start()
                thread.join()
                
                if exception:
                    raise exception
                return result
            else:
                # Loop não está rodando, pode usar run_until_complete
                return loop.run_until_complete(coro)
        except RuntimeError:
            # Não há loop, cria um novo
            return asyncio.run(coro)
    
    # SessionStore methods
    def loadSession(self, recipientId: int, deviceId: int) -> SessionRecord:
        """Carrega sessão de forma síncrona"""
        return self._run_async(self._async_store.sessionStore.loadSession(recipientId, deviceId))
    
    def storeSession(self, recipientId: int, deviceId: int, sessionRecord: SessionRecord) -> None:
        """Armazena sessão de forma síncrona"""
        return self._run_async(self._async_store.sessionStore.storeSession(recipientId, deviceId, sessionRecord))
    
    def containsSession(self, recipientId: int, deviceId: int) -> bool:
        """Verifica se sessão existe de forma síncrona"""
        return self._run_async(self._async_store.sessionStore.containsSession(recipientId, deviceId))
    
    def deleteSession(self, recipientId: int, deviceId: int) -> None:
        """Deleta sessão de forma síncrona"""
        return self._run_async(self._async_store.sessionStore.deleteSession(recipientId, deviceId))
    
    def deleteAllSessions(self, recipientId: int) -> None:
        """Deleta todas as sessões de forma síncrona"""
        return self._run_async(self._async_store.sessionStore.deleteAllSessions(recipientId))
    
    # PreKeyStore methods
    def loadPreKey(self, preKeyId: int) -> Optional[PreKeyRecord]:
        """Carrega prekey de forma síncrona"""
        return self._run_async(self._async_store.preKeyStore.loadPreKey(preKeyId))
    
    def storePreKey(self, preKeyId: int, preKeyRecord: PreKeyRecord) -> None:
        """Armazena prekey de forma síncrona"""
        return self._run_async(self._async_store.preKeyStore.storePreKey(preKeyId, preKeyRecord))
    
    def containsPreKey(self, preKeyId: int) -> bool:
        """Verifica se prekey existe de forma síncrona"""
        return self._run_async(self._async_store.preKeyStore.containsPreKey(preKeyId))
    
    def removePreKey(self, preKeyId: int) -> None:
        """Remove prekey de forma síncrona"""
        return self._run_async(self._async_store.preKeyStore.removePreKey(preKeyId))
    
    # SignedPreKeyStore methods
    def loadSignedPreKey(self, signedPreKeyId: int) -> Optional[SignedPreKeyRecord]:
        """Carrega signed prekey de forma síncrona"""
        return self._run_async(self._async_store.signedPreKeyStore.loadSignedPreKey(signedPreKeyId))
    
    def storeSignedPreKey(self, signedPreKeyId: int, signedPreKeyRecord: SignedPreKeyRecord) -> None:
        """Armazena signed prekey de forma síncrona"""
        return self._run_async(self._async_store.signedPreKeyStore.storeSignedPreKey(signedPreKeyId, signedPreKeyRecord))
    
    def containsSignedPreKey(self, signedPreKeyId: int) -> bool:
        """Verifica se signed prekey existe de forma síncrona"""
        return self._run_async(self._async_store.signedPreKeyStore.containsSignedPreKey(signedPreKeyId))
    
    def removeSignedPreKey(self, signedPreKeyId: int) -> None:
        """Remove signed prekey de forma síncrona"""
        return self._run_async(self._async_store.signedPreKeyStore.removeSignedPreKey(signedPreKeyId))
    
    # IdentityKeyStore methods
    def getIdentityKeyPair(self) -> Optional[IdentityKeyPair]:
        """Obtém identity key pair de forma síncrona"""
        return self._run_async(self._async_store.identityKeyStore.getIdentityKeyPair())
    
    def getLocalRegistrationId(self) -> Optional[int]:
        """Obtém registration ID local de forma síncrona"""
        return self._run_async(self._async_store.identityKeyStore.getLocalRegistrationId())
    
    def saveIdentity(self, recipientId: int, deviceId: int, identityKey: IdentityKey) -> None:
        """Salva identity de forma síncrona"""
        return self._run_async(self._async_store.identityKeyStore.saveIdentity(recipientId, deviceId, identityKey))
    
    def isTrustedIdentity(self, recipientId: int, deviceId: int, identityKey: IdentityKey) -> bool:
        """Verifica se identity é confiável de forma síncrona"""
        return self._run_async(self._async_store.identityKeyStore.isTrustedIdentity(recipientId, deviceId, identityKey))
    
    def getIdentity(self, recipientId: int) -> Optional[IdentityKey]:
        """Obtém identity de forma síncrona"""
        return self._run_async(self._async_store.identityKeyStore.getIdentity(recipientId))
    
    # SenderKeyStore methods (para GroupCipher)
    def loadSenderKey(self, senderKeyName) -> SenderKeyRecord:
        """Carrega sender key de forma síncrona"""
        return self._run_async(self._async_store.senderKeyStore.loadSenderKey(senderKeyName))
    
    def storeSenderKey(self, senderKeyName, senderKeyRecord: SenderKeyRecord) -> None:
        """Armazena sender key de forma síncrona"""
        return self._run_async(self._async_store.senderKeyStore.storeSenderKey(senderKeyName, senderKeyRecord))

