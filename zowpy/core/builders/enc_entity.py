"""
EncEntity Helper - Cria nodes <enc> corretamente.

Baseado em EncProtocolEntity.toProtocolTreeNode() do zowsuplib.
"""

from typing import Optional
from ...protocol.structs import ProtocolNode


class EncEntity:
    """
    Helper para criar nodes <enc> seguindo padrão do zowsuplib.
    
    Baseado em zowsuplib.yowsup.layers.axolotl.protocolentities.enc.EncProtocolEntity
    """
    
    TYPE_MSG = "msg"
    TYPE_PKMSG = "pkmsg"
    TYPE_SKMSG = "skmsg"
    TYPE_FRSKMSG = "frskmsg"
    TYPE_MSMSG = "msmsg"
    
    @staticmethod
    def create_enc_node(
        enc_type: str,
        ciphertext: bytes,
        mediatype: str = "text",
        jid: Optional[str] = None,
        count: Optional[str] = None
    ) -> ProtocolNode:
        """
        Cria node <enc> seguindo padrão do zowsuplib.
        
        Baseado em EncProtocolEntity.toProtocolTreeNode()
        
        Args:
            enc_type: Tipo de criptografia (msg, pkmsg, skmsg, etc.)
            ciphertext: Dados criptografados (bytes)
            mediatype: Tipo de mídia (text, image, audio, etc.)
            jid: JID do destinatário (opcional, usado para participants)
            count: Contador de retry (opcional)
        
        Returns:
            ProtocolNode: Node <enc> ou <to> com <enc> dentro (se jid fornecido)
        """
        # Cria atributos do node <enc>
        attribs = {
            "type": enc_type,
            "v": "2"
        }
        
        # Adiciona mediatype se fornecido
        if mediatype:
            attribs["mediatype"] = mediatype
        
        # Adiciona count se fornecido e não for "0"
        if count and count != "0":
            attribs["count"] = count
        
        # Cria node <enc>
        enc_node = ProtocolNode(
            tag="enc",
            attributes=attribs,
            data=ciphertext
        )
        
        # Se jid fornecido, envolve em <to> node (para participants)
        # Baseado em EncProtocolEntity.toProtocolTreeNode() linha 48
        if jid:
            return ProtocolNode(
                tag="to",
                attributes={"jid": jid},
                children=[enc_node]
            )
        
        return enc_node



