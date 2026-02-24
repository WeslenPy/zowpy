"""
Update Business Profile IQ - Atualização de perfil business (w:biz).

Equivalente ao UpdateBusinessProfile do go-whatsapp:
- xmlns: w:biz, type: set, to: s.whatsapp.net
- Filho <business_profile v="3" mutation_type="delta"> com um filho <address|description|email|website> com conteúdo infoData.
"""

from typing import Optional

from .iq import IqProtocolEntity
from ...protocol.structs import ProtocolNode
from ...utils.constants import YowConstants


VALID_INFO_TYPES = ("address", "description", "email", "website")


class InvalidBusinessUpdateInfoType(ValueError):
    """info_type deve ser um de: address, description, email, website."""


class UpdateBusinessProfileIqProtocolEntity(IqProtocolEntity):
    """
    IQ para atualizar um campo do perfil business (endereço, descrição, email ou website).

    Estrutura (go-whatsapp):
    <iq xmlns="w:biz" type="set" to="s.whatsapp.net">
      <business_profile v="3" mutation_type="delta">
        <address>infoData</address>   <!-- ou description, email, website -->
      </business_profile>
    </iq>
    """

    def __init__(
        self,
        info_type: str,
        info_data: str,
        iq_id: Optional[str] = None,
    ):
        """
        Args:
            info_type: Um de "address", "description", "email", "website".
            info_data: Conteúdo do campo (texto).
            iq_id: ID do IQ (gerado se None).

        Raises:
            InvalidBusinessUpdateInfoType: Se info_type não for permitido.
        """
        if info_type not in VALID_INFO_TYPES:
            raise InvalidBusinessUpdateInfoType(
                f"info_type deve ser um de: {', '.join(VALID_INFO_TYPES)}; recebido: {info_type!r}"
            )
        super().__init__(
            xmlns="w:biz",
            iq_type="set",
            iq_id=iq_id,
            to=YowConstants.WHATSAPP_SERVER,
        )
        self.info_type = info_type
        self.info_data = info_data

    def to_protocol_node(self) -> ProtocolNode:
        node = super().to_protocol_node()
        business_profile = ProtocolNode(
            tag="business_profile",
            attributes={"v": "3", "mutation_type": "delta"},
            children=[],
        )
        content_node = ProtocolNode(
            tag=self.info_type,
            attributes={},
            children=[],
            data=self.info_data.encode("utf-8"),
        )
        
        business_profile.children.append(content_node)
        node.children.append(business_profile)
        return node
