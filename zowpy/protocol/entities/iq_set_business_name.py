"""
Set Business Name IQ - Nome verificado de negócio (w:biz).

Baseado em SetBusinessNameIqProtocolEntity do zowsuplib.
"""

import random
from typing import Optional

from .iq import IqProtocolEntity
from ...protocol.structs import ProtocolNode
from ...utils.constants import YowConstants


class SetBusinessNameIqProtocolEntity(IqProtocolEntity):
    """
    IQ para definir nome de negócio verificado (xmlns w:biz).
    Requer assinatura com a identidade (chave privada) do axolotl.
    """

    def __init__(
        self,
        name: str,
        private_signing_key,
        iq_id: Optional[str] = None,
    ):
        """
        Args:
            name: Nome do negócio (verified name).
            private_signing_key: Chave privada da identidade (identity.getPrivateKey()) para assinar o certificado.
            iq_id: ID do IQ (gerado se None).
        """
        super().__init__(
            xmlns="w:biz",
            iq_type="set",
            iq_id=iq_id,
            to=YowConstants.WHATSAPP_SERVER,
        )
        self.name = name
        self._private_signing_key = private_signing_key

    def to_protocol_node(self) -> ProtocolNode:
        from ...proto import e2e_pb2
        from ...axolotl.ecc.curve import Curve

        node = super().to_protocol_node()
        payload = e2e_pb2.VerifiedNameCertificate()
        details = e2e_pb2.VerifiedNameCertificate.Details()
        details.serial = random.randint(1, 1000000000000000)
        details.issuer = "smb:wa"
        details.verifiedName = self.name
        payload.details.MergeFrom(details)
        details_bytes = payload.details.SerializeToString()
        payload.signature = Curve.calculateSignature(
            self._private_signing_key,
            details_bytes,
        )
        cert_node = ProtocolNode(
            tag="verified_name",
            attributes={"v": "2"},
            children=[],
            data=payload.SerializeToString(),
        )
        node.children.append(cert_node)
        return node
