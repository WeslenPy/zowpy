"""
Prekey Builder - Constrói IQs para operações de prekeys.

Baseado nos protocol entities do zowsuplib, mas totalmente assíncrono e moderno.
"""

import struct
import binascii
from typing import Dict, Tuple, List, Optional
from loguru import logger

from ...protocol.structs import ProtocolNode
from .iq_builder import IQBuilder
from ...utils.constants import YowConstants

class PrekeyBuilder:
    """
    Constrói IQs para operações de prekeys.
    
    Baseado nos protocol entities do zowsuplib:
    - SetKeysIqProtocolEntity
    - GetKeysIqProtocolEntity
    """
    
    XMLNS_ENCRYPT = "encrypt"
    
    @staticmethod
    def _adjust_id(_id: int, byte_count: int = 3) -> bytes:
        """
        Ajusta ID para formato de bytes.
        
        Baseado em AxolotlControlLayer.adjustId()
        
        Args:
            _id: ID numérico
            byte_count: Número de bytes desejado
        
        Returns:
            bytes: ID ajustado
        """
        _id_hex = format(_id, 'x')
        zfiller = len(_id_hex) if len(_id_hex) % 2 == 0 else len(_id_hex) + 1
        _id_hex = _id_hex.zfill(zfiller if zfiller > byte_count * 2 else byte_count * 2)
        return binascii.unhexlify(_id_hex)
    
    @staticmethod
    def _adjust_array(arr: bytes) -> bytes:
        """
        Ajusta array para formato hexadecimal.
        
        Baseado em AxolotlControlLayer.adjustArray()
        
        Args:
            arr: Array de bytes
        
        Returns:
            bytes: Array ajustado
        """
        from ...axolotl.util.hexutil import HexUtil
        return HexUtil.decodeHex(binascii.hexlify(arr))
    
    @staticmethod
    def build_set_keys_iq(
        identity_key: bytes,
        signed_prekey: Tuple[int, bytes, bytes],  # (id, public_key, signature)
        prekeys: Dict[int, bytes],  # id -> public_key
        registration_id: int,
        djb_type: int = 5,
        iq_id: Optional[str] = None
    ) -> ProtocolNode:
        """
        Constrói IQ para enviar prekeys ao servidor (upload).
        
        Baseado em SetKeysIqProtocolEntity.toProtocolTreeNode()
        
        Args:
            identity_key: Chave de identidade pública (sem primeiro byte)
            signed_prekey: Tupla (id, public_key, signature)
            prekeys: Dicionário de prekeys {id: public_key}
            registration_id: ID de registro
            djb_type: Tipo DJB (padrão 5)
            iq_id: ID do IQ (gerado se None)
        
        Returns:
            ProtocolNode: Node IQ para enviar prekeys
        """
        if not iq_id:
            iq_id = IQBuilder.generate_iq_id()
        
        # Cria node base IQ
        node = IQBuilder.build_base_iq(
            xmlns=PrekeyBuilder.XMLNS_ENCRYPT,
            iq_type="set",
            iq_id=iq_id,
            to=YowConstants.WHATSAPP_SERVER
        )
        
        # Ajusta identity key
        adjusted_identity = PrekeyBuilder._adjust_array(identity_key)
        identity_node = ProtocolNode(
            tag="identity",
            attributes={},
            data=adjusted_identity
        )
        
        # Cria lista de prekeys
        list_node = ProtocolNode(
            tag="list",
            attributes={},
            children=[]
        )
        
        for key_id, public_key in prekeys.items():
            # Ajusta ID e public key
            adjusted_id = PrekeyBuilder._adjust_id(key_id)
            adjusted_key = PrekeyBuilder._adjust_array(public_key)
            
            key_node = ProtocolNode(
                tag="key",
                attributes={},
                children=[
                    ProtocolNode(
                        tag="id",
                        attributes={},
                        data=adjusted_id
                    ),
                    ProtocolNode(
                        tag="value",
                        attributes={},
                        data=adjusted_key
                    )
                ]
            )
            list_node.children.append(key_node)
        
        # Cria signed prekey node
        signed_id, signed_value, signed_signature = signed_prekey
        adjusted_signed_id = PrekeyBuilder._adjust_id(signed_id)
        adjusted_signed_value = PrekeyBuilder._adjust_array(signed_value)
        adjusted_signed_signature = PrekeyBuilder._adjust_array(signed_signature)
        
        skey_node = ProtocolNode(
            tag="skey",
            attributes={},
            children=[
                ProtocolNode(
                    tag="id",
                    attributes={},
                    data=adjusted_signed_id
                ),
                ProtocolNode(
                    tag="value",
                    attributes={},
                    data=adjusted_signed_value
                ),
                ProtocolNode(
                    tag="signature",
                    attributes={},
                    data=adjusted_signed_signature
                )
            ]
        )
        
        # Cria registration node
        adjusted_reg_id = PrekeyBuilder._adjust_id(registration_id, byte_count=4)
        reg_node = ProtocolNode(
            tag="registration",
            attributes={},
            data=adjusted_reg_id
        )
        
        # Cria type node
        type_node = ProtocolNode(
            tag="type",
            attributes={},
            data=struct.pack('<B', djb_type)
        )
        
        # Adiciona todos os children ao node IQ
        node.children = [
            list_node,
            identity_node,
            reg_node,
            type_node,
            skey_node
        ]
        
        logger.debug(f"Set keys IQ construído: prekeys={len(prekeys)}, registration_id={registration_id}")
        return node
    
    @staticmethod
    def build_get_keys_iq(
        jids: List[str],
        reason: Optional[str] = None,
        iq_id: Optional[str] = None
    ) -> ProtocolNode:
        """
        Constrói IQ para obter prekeys do servidor (download).
        
        Baseado em GetKeysIqProtocolEntity.toProtocolTreeNode()
        
        Args:
            jids: Lista de JIDs para obter chaves
            reason: Razão para obter chaves (opcional)
            iq_id: ID do IQ (gerado se None)
        
        Returns:
            ProtocolNode: Node IQ para obter prekeys
        """
        if not iq_id:
            iq_id = IQBuilder.generate_iq_id()
        
        # Cria node base IQ
        node = IQBuilder.build_base_iq(
            xmlns=PrekeyBuilder.XMLNS_ENCRYPT,
            iq_type="get",
            iq_id=iq_id,
            to=YowConstants.WHATSAPP_SERVER
        )
        
        # Cria key node com users
        key_node = ProtocolNode(
            tag="key",
            attributes={},
            children=[]
        )
        
        for jid in jids:
            user_attrs = {"jid": jid}
            if reason:
                user_attrs["reason"] = reason
            
            user_node = ProtocolNode(
                tag="user",
                attributes=user_attrs,
                children=[]
            )
            key_node.children.append(user_node)
        
        node.children.append(key_node)
        
        logger.debug(f"Get keys IQ construído: jids={len(jids)}, reason={reason}")
        return node

