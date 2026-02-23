"""
Testes que validam a estrutura do node de mensagem criptografada no formato whatsmeow.

Estrutura esperada (1:1):
  <message>
    <participants>
      <to jid="own_jid"><enc type="msg" v="2">...</enc></to>
      <to jid="recipient_jid"><enc type="pkmsg" v="2">...</enc></to>
    </participants>
    <device-identity>...</device-identity>
    ...
  </message>
"""

import base64
import unittest

try:
    from zowpy.protocol.structs import ProtocolNode
    from zowpy.core.builders.enc_entity import EncEntity
    from zowpy.core.builders.encrypted_message_builder import EncryptedMessageBuilder
    from zowpy.core.builders.message_extras_builder import add_message_extras
except ImportError as e:
    ProtocolNode = EncEntity = EncryptedMessageBuilder = add_message_extras = None
    _import_error = e
else:
    _import_error = None


def _make_message_node(to_jid: str, message_type: str = "text"):
    """Base message node (without proto)."""
    return ProtocolNode(
        tag="message",
        attributes={"to": to_jid, "type": message_type, "id": "test-id-123"},
        children=[],
    )


class TestEncryptedMessageNodeStructureWhatsmeow(unittest.TestCase):
    """Valida estrutura whatsmeow: dois <to> (own + recipient), device-identity após participants."""

    def test_participants_has_two_to_nodes_own_then_recipient(self):
        """Existe exatamente um <participants> com pelo menos dois <to>; primeiro = own (msg), segundo = recipient (pkmsg)."""
        own_jid = "559885700260@s.whatsapp.net"
        recipient_jid = "201223166584@s.whatsapp.net"
        fake_ciphertext = b"\x00" * 50

        enc_self = EncEntity.create_enc_node(
            enc_type=EncEntity.TYPE_MSG,
            ciphertext=fake_ciphertext,
            mediatype="text",
            type_message="text",
            jid=own_jid,
        )
        enc_recipient = EncEntity.create_enc_node(
            enc_type=EncEntity.TYPE_PKMSG,
            ciphertext=fake_ciphertext,
            mediatype="text",
            type_message="text",
            jid=recipient_jid,
        )
        enc_entities = [enc_self, enc_recipient]

        message_node = _make_message_node(recipient_jid)
        message_node = EncryptedMessageBuilder.build_encrypted_message(
            message_node=message_node,
            enc_entities=enc_entities,
            message_type="text",
            participant=None,
        )

        participants = message_node.get_child("participants")
        self.assertIsNotNone(participants, "Deve existir um node <participants>")
        self.assertGreaterEqual(
            len(participants.children),
            2,
            "participants deve ter pelo menos dois filhos (<to>)",
        )

        first_to = participants.children[0]
        self.assertEqual(first_to.tag, "to", "Primeiro filho de participants deve ser <to>")
        self.assertEqual(
            first_to.get_attribute("jid"),
            own_jid,
            "Primeiro <to> deve ser o JID do enviador (own)",
        )
        enc_first = first_to.get_child("enc")
        self.assertIsNotNone(enc_first, "Primeiro <to> deve ter filho <enc>")
        self.assertEqual(enc_first.get_attribute("type"), "msg", "Enviador deve usar enc type=msg")
        self.assertEqual(enc_first.get_attribute("v"), "2", "enc deve ter v=2")

        second_to = participants.children[1]
        self.assertEqual(second_to.tag, "to")
        self.assertEqual(
            second_to.get_attribute("jid"),
            recipient_jid,
            "Segundo <to> deve ser o JID do destinatário",
        )
        enc_second = second_to.get_child("enc")
        self.assertIsNotNone(enc_second)
        self.assertIn(
            enc_second.get_attribute("type"),
            ("msg", "pkmsg"),
            "Destinatário deve usar enc type msg ou pkmsg",
        )
        self.assertEqual(enc_second.get_attribute("v"), "2")

    def test_device_identity_after_participants_when_provided(self):
        """Após build + extras com device_identity, o node deve ter <device-identity> logo após <participants>."""
        own_jid = "559885700260@s.whatsapp.net"
        recipient_jid = "201223166584@s.whatsapp.net"
        fake_ciphertext = b"\x00" * 50

        enc_self = EncEntity.create_enc_node(
            enc_type=EncEntity.TYPE_MSG,
            ciphertext=fake_ciphertext,
            mediatype="text",
            type_message="text",
            jid=own_jid,
        )
        enc_recipient = EncEntity.create_enc_node(
            enc_type=EncEntity.TYPE_PKMSG,
            ciphertext=fake_ciphertext,
            mediatype="text",
            type_message="text",
            jid=recipient_jid,
        )
        message_node = _make_message_node(recipient_jid)
        message_node = EncryptedMessageBuilder.build_encrypted_message(
            message_node=message_node,
            enc_entities=[enc_self, enc_recipient],
            message_type="text",
            participant=None,
        )

        device_identity_bytes = b"\x01" * 185
        device_identity_b64 = base64.b64encode(device_identity_bytes).decode()
        add_message_extras(
            message_node,
            category="contact",
            tctoken=None,
            device_identity_b64=device_identity_b64,
        )

        tags = [c.tag for c in message_node.children]
        self.assertIn("participants", tags, "message deve ter <participants>")
        self.assertIn("device-identity", tags, "message deve ter <device-identity> quando fornecido")

        idx_participants = tags.index("participants")
        idx_device_identity = tags.index("device-identity")
        self.assertLess(
            idx_participants,
            idx_device_identity,
            "device-identity deve vir após participants",
        )
        # device-identity deve ser o próximo após participants (ordem whatsmeow)
        self.assertEqual(
            idx_device_identity,
            idx_participants + 1,
            "device-identity deve ser o filho imediatamente após participants",
        )

    def test_extras_order_device_identity_then_reporting_then_tctoken(self):
        """Ordem dos extras: device-identity, reporting, tctoken."""
        enc = EncEntity.create_enc_node(
            enc_type=EncEntity.TYPE_MSG,
            ciphertext=b"x",
            jid="559885700260@s.whatsapp.net",
        )
        message_node = _make_message_node("201223166584@s.whatsapp.net")
        message_node = EncryptedMessageBuilder.build_encrypted_message(
            message_node=message_node,
            enc_entities=[enc],
            message_type="text",
        )
        add_message_extras(
            message_node,
            category="contact",
            tctoken=b"tctoken_bytes_12",
            device_identity_b64=base64.b64encode(b"\x00" * 185).decode(),
        )

        tags = [c.tag for c in message_node.children]
        # participants, device-identity, reporting, tctoken
        self.assertEqual(tags[0], "participants")
        self.assertEqual(tags[1], "device-identity")
        self.assertEqual(tags[2], "reporting")
        self.assertEqual(tags[3], "tctoken")


if __name__ == "__main__":
    unittest.main()
