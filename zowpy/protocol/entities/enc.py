"""
Enc Protocol Entity - Entidade de criptografia <enc>.

Baseado em EncProtocolEntity do zowsuplib.
"""

from typing import Optional
from .base import ProtocolEntity


class EncProtocolEntity(ProtocolEntity):
    """
    Entidade de criptografia <enc>.
    
    Baseado em EncProtocolEntity do zowsuplib.
    """
    
    TYPE_MSG = "msg"
    TYPE_PKMSG = "pkmsg"
    TYPE_SKMSG = "skmsg"
    TYPE_FRSKMSG = "frskmsg"
    TYPE_MSMSG = "msmsg"
    
    def __init__(
        self,
        enc_type: str,
        ciphertext: bytes,
        mediatype: Optional[str] = None,
        jid: Optional[str] = None,
        count: Optional[str] = None
    ):
        """
        Cria entidade de criptografia.
        
        Args:
            enc_type: Tipo de criptografia (msg, pkmsg, skmsg, etc.)
            ciphertext: Dados criptografados (bytes)
            mediatype: Tipo de mídia (text, image, audio, etc.)
            jid: JID do destinatário (opcional, usado para participants)
            count: Contador de retry (opcional)
        """
        attributes = {
            "type": enc_type,
            "v": "2"
        }
        
        if mediatype:
            attributes["mediatype"] = mediatype
        
        if count and count != "0":
            attributes["count"] = count
        
        # Se jid fornecido, envolve em <to> node (para participants)
        if jid:
            enc_node = ProtocolEntity(
                tag="enc",
                attributes=attributes,
                data=ciphertext
            )
            super().__init__(
                tag="to",
                attributes={"jid": jid},
                children=[enc_node]
            )
        else:
            super().__init__(
                tag="enc",
                attributes=attributes,
                data=ciphertext
            )
        
        self.enc_type = enc_type
        self.ciphertext = ciphertext

