"""
Media Cipher - Criptografia de mídia usando AES-CBC.

Baseado em MediaCipher do zowsuplib.
"""

import hmac
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from loguru import logger

from ...axolotl.kdf.hkdfv3 import HKDFv3
from ...axolotl.util.byteutil import ByteUtil


class MediaCipher:
    """
    Criptografa e descriptografa mídia usando AES-CBC.
    
    Baseado em MediaCipher do zowsuplib:
    - Usa HKDFv3 para derivar IV, key e MAC key
    - Criptografia AES-CBC com PKCS7 padding
    - HMAC-SHA256 para autenticação (10 bytes)
    """
    
    INFO_IMAGE = b"WhatsApp Image Keys"
    INFO_AUDIO = b"WhatsApp Audio Keys"
    INFO_VIDEO = b"WhatsApp Video Keys"
    INFO_DOCUMENT = b"WhatsApp Document Keys"
    INFO_HISTORY_SYNC = b"WhatsApp History Keys"
    INFO_APP_STATE = b"WhatsApp App State Keys"
    INFO_STICKER = b"WhatsApp Sticker Pack Keys"
    
    def __init__(self):
        """Inicializa MediaCipher."""
        self._hkdf = HKDFv3()
    
    def encrypt_image(self, plaintext: bytes, ref_key: bytes) -> bytes:
        """Criptografa imagem."""
        return self.encrypt(plaintext, ref_key, self.INFO_IMAGE)
    
    def encrypt_audio(self, plaintext: bytes, ref_key: bytes) -> bytes:
        """Criptografa áudio."""
        return self.encrypt(plaintext, ref_key, self.INFO_AUDIO)
    
    def encrypt_video(self, plaintext: bytes, ref_key: bytes) -> bytes:
        """Criptografa vídeo."""
        return self.encrypt(plaintext, ref_key, self.INFO_VIDEO)
    
    def encrypt_document(self, plaintext: bytes, ref_key: bytes) -> bytes:
        """Criptografa documento."""
        return self.encrypt(plaintext, ref_key, self.INFO_DOCUMENT)
    
    def encrypt_history_sync(self, plaintext: bytes, ref_key: bytes) -> bytes:
        """Criptografa history sync."""
        return self.encrypt(plaintext, ref_key, self.INFO_HISTORY_SYNC)
    
    def encrypt_app_state(self, plaintext: bytes, ref_key: bytes) -> bytes:
        """Criptografa app state."""
        return self.encrypt(plaintext, ref_key, self.INFO_APP_STATE)
    
    def encrypt_sticker(self, plaintext: bytes, ref_key: bytes) -> bytes:
        """Criptografa sticker."""
        return self.encrypt(plaintext, ref_key, self.INFO_STICKER)
    
    def decrypt_image(self, ciphertext: bytes, ref_key: bytes) -> bytes:
        """Descriptografa imagem."""
        return self.decrypt(ciphertext, ref_key, self.INFO_IMAGE)
    
    def decrypt_audio(self, ciphertext: bytes, ref_key: bytes) -> bytes:
        """Descriptografa áudio."""
        return self.decrypt(ciphertext, ref_key, self.INFO_AUDIO)
    
    def decrypt_video(self, ciphertext: bytes, ref_key: bytes) -> bytes:
        """Descriptografa vídeo."""
        return self.decrypt(ciphertext, ref_key, self.INFO_VIDEO)
    
    def decrypt_document(self, ciphertext: bytes, ref_key: bytes) -> bytes:
        """Descriptografa documento."""
        return self.decrypt(ciphertext, ref_key, self.INFO_DOCUMENT)
    
    def decrypt_history_sync(self, ciphertext: bytes, ref_key: bytes) -> bytes:
        """Descriptografa history sync."""
        return self.decrypt(ciphertext, ref_key, self.INFO_HISTORY_SYNC)
    
    def decrypt_app_state(self, ciphertext: bytes, ref_key: bytes) -> bytes:
        """Descriptografa app state."""
        return self.decrypt(ciphertext, ref_key, self.INFO_APP_STATE)
    
    def decrypt_sticker(self, ciphertext: bytes, ref_key: bytes) -> bytes:
        """Descriptografa sticker."""
        return self.decrypt(ciphertext, ref_key, self.INFO_STICKER)
    
    def encrypt(self, plaintext: bytes, ref_key: bytes, media_info: bytes) -> bytes:
        """
        Criptografa mídia usando AES-CBC.
        
        Baseado em MediaCipher.encrypt() do zowsuplib:
        1. Deriva secrets usando HKDFv3 (112 bytes)
        2. Extrai IV (16 bytes), key (32 bytes) e MAC key (32 bytes)
        3. Criptografa com AES-CBC + PKCS7 padding
        4. Calcula HMAC-SHA256 (10 bytes) e anexa
        
        Args:
            plaintext: Dados originais a criptografar
            ref_key: Chave de referência (media_key)
            media_info: Info string específica do tipo de mídia
            
        Returns:
            bytes: Dados criptografados + MAC (10 bytes)
        """
        # Deriva secrets usando HKDFv3 (112 bytes)
        derived = self._hkdf.deriveSecrets(ref_key, media_info, 112)
        
        # Divide: IV (16), key (32), MAC key (32 bytes a partir do byte 48)
        parts = ByteUtil.split(derived, 16, 32)
        iv = parts[0]
        key = parts[1]
        mac_key = derived[48:80]
        
        # Criptografa com AES-CBC
        cipher_encryptor = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend()
        ).encryptor()
        
        # Adiciona padding PKCS7 se necessário
        if len(plaintext) % 16 != 0:
            padder = padding.PKCS7(128).padder()
            padded_plaintext = padder.update(plaintext) + padder.finalize()
        else:
            padded_plaintext = plaintext
        
        # Criptografa
        ciphertext = cipher_encryptor.update(padded_plaintext) + cipher_encryptor.finalize()
        
        # Calcula HMAC-SHA256 (apenas 10 bytes)
        mac = hmac.new(mac_key, digestmod=hashlib.sha256)
        mac.update(iv)
        mac.update(ciphertext)
        
        # Retorna ciphertext + MAC (10 bytes)
        return ciphertext + mac.digest()[:10]
    
    def decrypt(self, ciphertext: bytes, ref_key: bytes, media_info: bytes) -> bytes:
        """
        Descriptografa mídia usando AES-CBC.
        
        Baseado em MediaCipher.decrypt() do zowsuplib:
        1. Verifica MAC (últimos 10 bytes)
        2. Deriva secrets usando HKDFv3
        3. Descriptografa com AES-CBC
        4. Remove PKCS7 padding
        
        Args:
            ciphertext: Dados criptografados + MAC (10 bytes)
            ref_key: Chave de referência (media_key)
            media_info: Info string específica do tipo de mídia
            
        Returns:
            bytes: Dados descriptografados
            
        Raises:
            ValueError: Se MAC inválido
        """
        # Deriva secrets usando HKDFv3 (112 bytes)
        derived = self._hkdf.deriveSecrets(ref_key, media_info, 112)
        
        # Divide: IV (16), key (32), MAC key (32 bytes a partir do byte 48)
        parts = ByteUtil.split(derived, 16, 32)
        iv = parts[0]
        key = parts[1]
        mac_key = derived[48:80]
        
        # Separa ciphertext e MAC (últimos 10 bytes)
        media_ciphertext = ciphertext[:-10]
        mac_value = ciphertext[-10:]
        
        # Verifica MAC
        mac = hmac.new(mac_key, digestmod=hashlib.sha256)
        mac.update(iv)
        mac.update(media_ciphertext)
        
        if mac_value != mac.digest()[:10]:
            raise ValueError("Invalid MAC")
        
        # Descriptografa com AES-CBC
        cipher_decryptor = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend()
        ).decryptor()
        
        decrypted = cipher_decryptor.update(media_ciphertext) + cipher_decryptor.finalize()
        
        # Remove PKCS7 padding
        unpadder = padding.PKCS7(128).unpadder()
        return unpadder.update(decrypted) + unpadder.finalize()

