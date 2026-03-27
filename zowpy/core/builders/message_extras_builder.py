"""
Constrói e adiciona elementos extras ao node de mensagem (device-identity, reporting, tctoken).

Ordem whatsmeow: participants → device-identity; em seguida reporting e tctoken quando existirem.
"""

import base64
import os
import secrets
from typing import Optional

from zowpy.utils.tools import WATools
from ...protocol.structs import ProtocolNode

import secrets

def generate_hex_token(prefix_hex: str = "040123", total_bytes: int = 11) -> bytes:
    """
    Gera um token hexadecimal aleatório com prefixo fixo (040123)
    e tamanho total definido em bytes.
    """
    prefix_bytes = len(prefix_hex) // 2
    if prefix_bytes >= total_bytes:
        raise ValueError("O prefixo é maior ou igual ao tamanho total do token")

    remaining_bytes = total_bytes - prefix_bytes

    # return bytes.fromhex("0401235016c0aff54fd55c")

    return bytes.fromhex(prefix_hex + secrets.token_hex(remaining_bytes))

def add_message_extras(
    message_node: ProtocolNode,
    message_secret:bytes,
    proto_bytes:bytes,
    sender_jid:str,
    category: Optional[str],
    tctoken: Optional[bytes] = None,
    device_identity_b64: Optional[str] = None,
) -> None:
    """
    Adiciona device-identity, reporting e tctoken ao message_node (in-place).
    Ordem: device-identity primeiro (logo após participants), depois reporting, tctoken.

    Args:
        message_node: Node da mensagem (será modificado)
        category: Atributo "category"; se != "peer", adiciona reporting
        tctoken: Token para trusted contacts (opcional)
        device_identity_b64: device_identity em base64 (opcional)
    """
    from loguru import logger

    extras_to_append = []

    if device_identity_b64:
        try:
            did_data = base64.b64decode(device_identity_b64)
            device_identity = ProtocolNode(
                tag="device-identity",
                attributes={},
                data=did_data
            )
            extras_to_append.append(device_identity)
        except Exception as e:
            from loguru import logger
            logger.warning(f"Erro ao adicionar device-identity: {e}")

    remote_jid = message_node.get_attribute("to")
    message_id = message_node.get_attribute("id")

    logger.debug(f"Adicionando reporting ao message_node: {message_node}")

    reporting_token = WATools.get_message_reporting_token(proto_bytes, message_secret, sender_jid, remote_jid, message_id)
    logger.debug(f"Reporting token: {reporting_token}")

    if category != "peer":
        reporting = ProtocolNode(
            tag="reporting",
            attributes={},
            children=[]
        )
        reporting_token = ProtocolNode(
            tag="reporting_token",
            attributes={"v": "2"},
            data=reporting_token
        )

        reporting_tag = ProtocolNode(
            tag="reporting_tag",
            attributes={},
            data=os.urandom(20)
        )
        # reporting.children.append(reporting_tag)
        reporting.children.append(reporting_token)
        extras_to_append.append(reporting)


    # tctoken = tctoken if tctoken else generate_hex_token()

    if tctoken:
        tctoken_node = ProtocolNode(
            tag="tctoken",
            attributes={},
            data=tctoken
        )
        extras_to_append.append(tctoken_node)

    for node in extras_to_append:
        message_node.children.append(node)
