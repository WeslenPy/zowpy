"""
Constrói e adiciona elementos extras ao node de mensagem (device-identity, reporting, tctoken).

Ordem whatsmeow: participants → device-identity; em seguida reporting e tctoken quando existirem.
"""

import base64
import os
from typing import Optional

from ...protocol.structs import ProtocolNode


def add_message_extras(
    message_node: ProtocolNode,
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

    if category != "peer":
        reporting = ProtocolNode(
            tag="reporting",
            attributes={},
            children=[]
        )
        reporting_token = ProtocolNode(
            tag="reporting_token",
            attributes={"v": "2"},
            data=os.urandom(16)
        )
        reporting_tag = ProtocolNode(
            tag="reporting_tag",
            attributes={},
            data=os.urandom(20)
        )
        # reporting.children.append(reporting_tag)
        reporting.children.append(reporting_token)
        extras_to_append.append(reporting)

    if tctoken:
        tctoken_node = ProtocolNode(
            tag="tctoken",
            attributes={},
            data=tctoken
        )
        extras_to_append.append(tctoken_node)

    for node in extras_to_append:
        message_node.children.append(node)
