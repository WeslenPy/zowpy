"""
Consonance Structs - Portado para zowpy.

Porta KeyPair, PublicKey e PrivateKey do consonance.
"""

from dissononce.dh.x25519.x25519 import X25519DH
from dissononce.dh.x25519.keypair import KeyPair as X25519KeyPair


class PublicKey:
    """Chave pública X25519."""

    def __init__(self, data: bytes):
        """
        :param data: Dados da chave pública (32 bytes)
        :type data: bytes
        """
        self._data = data

    @property
    def data(self) -> bytes:
        return self._data

    def __eq__(self, other: object) -> bool:
        return isinstance(other, PublicKey) and self.data == other.data

    def __hash__(self) -> int:
        return hash(self.data)


class PrivateKey:
    """Chave privada X25519."""

    def __init__(self, data: bytes):
        """
        :param data: Dados da chave privada (32 bytes)
        :type data: bytes
        """
        self._data = data

    @property
    def data(self) -> bytes:
        return self._data

    def __eq__(self, other: object) -> bool:
        return isinstance(other, PrivateKey) and self.data == other.data

    def __hash__(self) -> int:
        return hash(self.data)


class KeyPair:
    """Par de chaves X25519 (pública e privada)."""

    def __init__(self, public: PublicKey, private: PrivateKey):
        """
        :param public: Chave pública
        :param private: Chave privada
        """
        self._public = public
        self._private = private

    @property
    def public(self) -> PublicKey:
        return self._public

    @property
    def private(self) -> PrivateKey:
        return self._private

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, KeyPair)
            and other.public == self.public
            and other.private == self.private
        )

    @classmethod
    def generate(cls) -> "KeyPair":
        """
        Gera um novo par de chaves.

        :return: Novo KeyPair
        :rtype: KeyPair
        """
        keypair = X25519DH().generate_keypair()
        return KeyPair(
            PublicKey(keypair.public.data),
            PrivateKey(keypair.private.data),
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "KeyPair":
        """
        Cria KeyPair a partir de bytes.

        :param data: Dados do keypair (64 bytes: 32 privada + 32 pública)
        :type data: bytes
        :return: KeyPair
        :rtype: KeyPair
        """
        keypair = X25519KeyPair.from_bytes(data)
        return KeyPair(
            PublicKey(keypair.public.data),
            PrivateKey(keypair.private.data),
        )
    
    def serialize(self) -> bytes:
        """
        Serializa KeyPair para bytes.
        
        Formato: 64 bytes (32 privada + 32 pública)
        
        :return: Bytes serializados
        :rtype: bytes
        """
        return self.private.data + self.public.data

