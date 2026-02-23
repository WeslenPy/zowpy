"""
Testes usando o node de mensagem recebida (ex.: LID, pkmsg, reporting).

Estrutura do node (exemplo real):
  <message from="4347077386271:0@lid" type="text" id="..." notify="Weslen"
           sender_pn="5511930023692@s.whatsapp.net" t="1771818539">
    <reporting>...</reporting>
    <enc v="2" type="pkmsg">0x33...</enc>
  </message>
"""

import pytest
from unittest.mock import MagicMock

from zowpy.protocol.structs import ProtocolNode
from zowpy.core.encryption.receiver import EncryptionReceiver


# Dados do enc (hex do node anexado, sem 0x e sem quebras)
ENC_PKMSG_HEX = (
    "3308900612210585c51cbd11f52d9395651983c20e3e3f88b21f5b66eb0e670af57f8b6d0"
    "80f541a2105ceae2bd635b7d77e9f46150e685769d3c664fd49c74173fb9fa1e00f5d391"
    "65a2262330a2105668f0d2c421268cbac994277e50c91b2bab071d9085744657ad35251"
    "abf46259100018002230b0ff625deee3a512724fa6a1df5c157b3d89f814f0e682a588c"
    "1cc956d58b0b5a370fe7cc415ef47306fc831ca8f739f84a5299b0cc9956328db9c81c7"
    "0430fc04"
)


def build_message_node_from_fixture():
    """Constrói o ProtocolNode equivalente ao node anexado (message com reporting + enc pkmsg)."""
    enc_data = bytes.fromhex(ENC_PKMSG_HEX)
    reporting_tag_hex = "01102a1b4cb13a444acc112c1fa2272b8d973d85"
    reporting_token_hex = "de8a9cd2b9169e26599b49a56172e687"

    reporting_tag_node = ProtocolNode(
        tag="reporting_tag",
        attributes={},
        children=[],
        data=bytes.fromhex(reporting_tag_hex),
    )
    reporting_token_node = ProtocolNode(
        tag="reporting_token",
        attributes={"v": "2"},
        children=[],
        data=bytes.fromhex(reporting_token_hex),
    )
    reporting_node = ProtocolNode(
        tag="reporting",
        attributes={},
        children=[reporting_tag_node, reporting_token_node],
    )

    enc_node = ProtocolNode(
        tag="enc",
        attributes={"v": "2", "type": "pkmsg"},
        children=[],
        data=enc_data,
    )

    message_node = ProtocolNode(
        tag="message",
        attributes={
            "from": "4347077386271:0@lid",
            "type": "text",
            "id": "ACB5C7306828FC035B16CCCA3BBA43B7",
            "notify": "Weslen",
            "sender_pn": "5511930023692@s.whatsapp.net",
            "t": "1771818539",
        },
        children=[reporting_node, enc_node],
    )
    return message_node


class TestMessageNodePkmsgStructure:
    """Valida estrutura e seleção de enc no node de mensagem recebida (pkmsg)."""

    def test_message_has_expected_attributes(self):
        """Node message tem from, type, id, notify, sender_pn, t."""
        node = build_message_node_from_fixture()
        assert node.tag == "message"
        assert node.get_attribute("from") == "4347077386271:0@lid"
        assert node.get_attribute("type") == "text"
        assert node.get_attribute("id") == "ACB5C7306828FC035B16CCCA3BBA43B7"
        assert node.get_attribute("notify") == "Weslen"
        assert node.get_attribute("sender_pn") == "5511930023692@s.whatsapp.net"
        assert node.get_attribute("t") == "1771818539"

    def test_message_has_reporting_and_enc_children(self):
        """Node message tem filhos <reporting> e <enc>."""
        node = build_message_node_from_fixture()
        tags = [c.tag for c in node.children]
        assert "reporting" in tags
        assert "enc" in tags

    def test_enc_is_pkmsg_v2_with_data(self):
        """O único <enc> tem type=pkmsg, v=2 e data (bytes)."""
        node = build_message_node_from_fixture()
        enc = node.get_child("enc")
        assert enc is not None
        assert enc.get_attribute("type") == "pkmsg"
        assert enc.get_attribute("v") == "2"
        assert enc.data is not None
        assert len(enc.data) == len(bytes.fromhex(ENC_PKMSG_HEX))

    def test_get_all_children_enc_returns_one(self):
        """get_all_children('enc') retorna exatamente um enc."""
        node = build_message_node_from_fixture()
        enc_list = node.get_all_children("enc")
        assert len(enc_list) == 1
        assert enc_list[0].get_attribute("type") == "pkmsg"


class TestEncryptionReceiverSelectEncPkmsg:
    """Valida _select_enc_node com o node de mensagem pkmsg (1:1, sem participant)."""

    @pytest.fixture
    def receiver(self):
        """Receiver com manager mock; só usamos _select_enc_node (não chama decrypt)."""
        return EncryptionReceiver(manager=MagicMock())

    def test_select_enc_node_returns_pkmsg_for_this_node(self, receiver):
        """_select_enc_node escolhe o enc pkmsg para este node (1:1)."""
        node = build_message_node_from_fixture()
        selection = receiver._select_enc_node(node)
        assert selection is not None
        enc_type, enc_version, enc_data, mediatype = selection
        assert enc_type == "pkmsg"
        assert enc_version == "2"
        assert enc_data == bytes.fromhex(ENC_PKMSG_HEX)
        # mediatype pode ser None se o enc não tiver atributo mediatype
        assert mediatype is None or isinstance(mediatype, str)

    def test_select_enc_node_no_participant_so_1v1(self):
        """Node não tem participant, então é 1:1; ordem de busca é PKMSG depois MSG."""
        node = build_message_node_from_fixture()
        assert node.get_attribute("participant") is None
        receiver = EncryptionReceiver(manager=MagicMock())
        selection = receiver._select_enc_node(node)
        assert selection is not None
        assert selection[0] == "pkmsg"
