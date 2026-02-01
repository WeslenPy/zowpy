"""
Prekey Builder - Constrói IQs para operações de prekeys.

Baseado nos protocol entities do zowsuplib, mas totalmente assíncrono e moderno.
"""

import struct
import binascii
from typing import Dict, Tuple, List, Optional
from loguru import logger

from zowpy.utils.tools import Jid

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
        _id_orig = _id
        _id_hex = format(_id, 'x')
        logger.debug(f"[ZOWPY] adjustId: input_id={_id_orig} (tipo={type(_id_orig)}), hex_original={_id_hex}, byte_count={byte_count}")
        
        zfiller = len(_id_hex) if len(_id_hex) % 2 == 0 else len(_id_hex) + 1
        logger.debug(f"[ZOWPY] adjustId: zfiller={zfiller}, target_bytes={byte_count*2}")
        
        _id_hex_padded = _id_hex.zfill(zfiller if zfiller > byte_count * 2 else byte_count * 2)
        logger.debug(f"[ZOWPY] adjustId: hex_padded={_id_hex_padded}, len={len(_id_hex_padded)}")
        
        result = binascii.unhexlify(_id_hex_padded)
        logger.debug(f"[ZOWPY] adjustId: output_len={len(result)}, output_hex={binascii.hexlify(result).decode()}")
        return result
    
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
        arr_hex = binascii.hexlify(arr).decode()
        result = HexUtil.decodeHex(arr_hex)
        logger.debug(f"[ZOWPY] adjustArray: input_len={len(arr)}, input_hex_first_40={arr_hex[:40]}..., output_len={len(result)}, output_hex_first_40={binascii.hexlify(result[:40]).decode() if len(result) >= 40 else binascii.hexlify(result).decode()}...")
        return result
    
    @staticmethod
    def build_set_keys_iq(
        identity_key: bytes,
        signed_prekey: Tuple[bytes, bytes, bytes],  # (id ajustado, public_key, signature)
        prekeys: Dict[bytes, bytes],  # id ajustado -> public_key ajustado
        registration_id: bytes,  # ID ajustado
        djb_type: int = 5,
        iq_id: Optional[str] = None
    ) -> ProtocolNode:
        """
        Constrói IQ para enviar prekeys ao servidor (upload).
        
        Baseado em SetKeysIqProtocolEntity.toProtocolTreeNode()
        
        CORREÇÃO: Agora recebe IDs já ajustados (bytes) como no zowsuplib.
        
        Args:
            identity_key: Chave de identidade pública ajustada (já processada por _adjust_array)
            signed_prekey: Tupla (id ajustado: bytes, public_key ajustado: bytes, signature ajustado: bytes)
            prekeys: Dicionário {id ajustado: bytes -> public_key ajustado: bytes}
            registration_id: ID de registro ajustado (bytes, já processado por _adjust_id com byte_count=4)
            djb_type: Tipo DJB (padrão 5)
            iq_id: ID do IQ (gerado se None)
        
        Returns:
            ProtocolNode: Node IQ para enviar prekeys
        """
        logger.info("=" * 80)
        logger.info("[ZOWPY] PrekeyBuilder.build_set_keys_iq() INICIADO")
        
        if not iq_id:
            iq_id = IQBuilder.generate_iq_id()
        
        # Cria node base IQ
        node = IQBuilder.build_base_iq(
            xmlns=PrekeyBuilder.XMLNS_ENCRYPT,
            iq_type="set",
            iq_id=iq_id,
            to=YowConstants.WHATSAPP_SERVER
        )
        logger.debug(f"[ZOWPY] IQ base node criado: xmlns=encrypt, type=set, id={iq_id}")
        
        # Identity key já vem ajustado de _flush_prekeys()
        identity_node = ProtocolNode(
            tag="identity",
            attributes={},
            data=identity_key  # Usa diretamente, sem ajuste
        )
        logger.debug(f"[ZOWPY] Identity node criado: data_len={len(identity_key)}, first_40_hex={binascii.hexlify(identity_key[:40]).decode() if len(identity_key) >= 40 else binascii.hexlify(identity_key).decode()}...")
        
        # Cria lista de prekeys
        list_node = ProtocolNode(
            tag="list",
            attributes={},
            children=[]
        )
        keyNodes = []
        
        logger.info(f"[ZOWPY] Criando lista de {len(prekeys)} prekeys...")
        for i, (key_id, public_key) in enumerate(prekeys.items()):
            # CORREÇÃO: ID já vem ajustado (bytes), não precisa ajustar novamente
            key_node = ProtocolNode(
                tag="key",
                attributes={},
                children=[
                    ProtocolNode(
                        tag="id",
                        attributes={},
                        data=key_id  # ID já ajustado (bytes)
                    ),
                    ProtocolNode(
                        tag="value",
                        attributes={},
                        data=public_key  # Usa diretamente, sem ajuste
                    )
                ]
            )
            keyNodes.append(key_node)
            
            # Log detalhado para os primeiros 3 prekeys
            if i < 3:
                logger.debug(f"[ZOWPY] Prekey[{i}] no IQ: id_len={len(key_id)}, id_hex={binascii.hexlify(key_id).decode()}, value_len={len(public_key)}, value_first_40_hex={binascii.hexlify(public_key[:40]).decode() if len(public_key) >= 40 else binascii.hexlify(public_key).decode()}...")

        list_node.add_children(keyNodes)
        logger.info(f"[ZOWPY] Lista de prekeys criada com {len(keyNodes)} keys")
        
        # Cria signed prekey node
        # CORREÇÃO: signed_id já vem ajustado (bytes), não precisa ajustar novamente
        signed_id, signed_value, signed_signature = signed_prekey
        
        logger.debug(f"[ZOWPY] Signed prekey detalhes: id_len={len(signed_id)}, key_len={len(signed_value)}, sig_len={len(signed_signature)}")
        logger.debug(f"[ZOWPY] Signed prekey ID hex: {binascii.hexlify(signed_id).decode()}")
        logger.debug(f"[ZOWPY] Signed prekey key first_40_hex: {binascii.hexlify(signed_value[:40]).decode() if len(signed_value) >= 40 else binascii.hexlify(signed_value).decode()}...")
        logger.debug(f"[ZOWPY] Signed prekey sig first_40_hex: {binascii.hexlify(signed_signature[:40]).decode() if len(signed_signature) >= 40 else binascii.hexlify(signed_signature).decode()}...")
        
        skey_node = ProtocolNode(
            tag="skey",
            attributes={},
            children=[
                ProtocolNode(
                    tag="id",
                    attributes={},
                    data=signed_id  # ID já ajustado (bytes)
                ),
                ProtocolNode(
                    tag="value",
                    attributes={},
                    data=signed_value  # Usa diretamente, sem ajuste
                ),
                ProtocolNode(
                    tag="signature",
                    attributes={},
                    data=signed_signature  # Usa diretamente, sem ajuste
                )
            ]
        )
        logger.debug(f"[ZOWPY] Signed prekey node criado")
        
        # Cria registration node
        # CORREÇÃO: registration_id já vem ajustado (bytes), não precisa ajustar novamente
        reg_node = ProtocolNode(
            tag="registration",
            attributes={},
            data=registration_id  # ID já ajustado (bytes)
        )
        logger.debug(f"[ZOWPY] Registration node criado: data_len={len(registration_id)}, hex={binascii.hexlify(registration_id).decode()}")
        
        # Cria type node
        type_node = ProtocolNode(
            tag="type",
            attributes={},
            data=struct.pack('<B', djb_type)
        )
        logger.debug(f"[ZOWPY] Type node criado: djbType={djb_type}, data={binascii.hexlify(struct.pack('<B', djb_type)).decode()}")
        
        # Adiciona todos os children ao node IQ
        node.add_children([
            list_node,
            identity_node,
            reg_node,
            type_node,
            skey_node
        ])
        
        logger.info(f"[ZOWPY] IQ node finalizado: {len(node.children)} children adicionados")
        logger.info("[ZOWPY] PrekeyBuilder.build_set_keys_iq() CONCLUÍDO")
        logger.info("=" * 80)
        
        logger.debug(f"Set keys IQ construído: prekeys={len(prekeys)}, registration_id_len={len(registration_id)}")
        ldata = list(node) if type(node) is bytearray else node
        logger.debug(f"tx:\n{ldata}")

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
            normalized_jid = jid.split("@")[0].split(":")[0]
            user_attrs = {"jid": f"{normalized_jid}@s.whatsapp.net"}
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

