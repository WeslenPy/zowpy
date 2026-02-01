import unittest
from zowpy.protocol.entities.iq_trust_contact import TrustContactIqProtocolEntity
from zowpy.protocol.structs import ProtocolNode
from zowpy.utils.constants import YowConstants

class TestTrustContactIqProtocolEntity(unittest.TestCase):
    def test_to_protocol_node(self):
        # Dados de teste
        jids = ["5511999999999@s.whatsapp.net", "5511888888888@s.whatsapp.net"]
        timestamp = 1737849600
        iq_id = "test_iq_id"
        
        # Cria a entidade
        entity = TrustContactIqProtocolEntity(
            jids=jids,
            timestamp=timestamp,
            iq_id=iq_id
        )
        
        # Converte para node
        node = entity.to_protocol_node()
        
        # Validações básicas do IQ
        self.assertEqual(node.tag, "iq")
        self.assertEqual(node.get_attribute("id"), iq_id)
        self.assertEqual(node.get_attribute("xmlns"), "privacy")
        self.assertEqual(node.get_attribute("type"), "set")
        self.assertEqual(node.get_attribute("to"), YowConstants.WHATSAPP_SERVER)
        
        # Valida o node <tokens>
        tokens_node = node.get_child("tokens")
        self.assertIsNotNone(tokens_node)
        
        # Valida os nodes <token>
        children = tokens_node.children
        self.assertEqual(len(children), 2)
        
        # Primeiro token
        token1 = children[0]
        self.assertEqual(token1.tag, "token")
        self.assertEqual(token1.get_attribute("jid"), jids[0])
        self.assertEqual(token1.get_attribute("type"), "trusted_contact")
        self.assertEqual(token1.get_attribute("t"), str(timestamp))
        
        # Segundo token
        token2 = children[1]
        self.assertEqual(token2.tag, "token")
        self.assertEqual(token2.get_attribute("jid"), jids[1])
        self.assertEqual(token2.get_attribute("type"), "trusted_contact")
        self.assertEqual(token2.get_attribute("t"), str(timestamp))

    def test_to_protocol_node_single_jid_string(self):
        # Teste com string única separada por vírgula
        jid_str = "5511999999999@s.whatsapp.net, 5511888888888@s.whatsapp.net"
        timestamp = 1737849600
        
        entity = TrustContactIqProtocolEntity(
            jids=jid_str,
            timestamp=timestamp
        )
        
        node = entity.to_protocol_node()
        tokens_node = node.get_child("tokens")
        self.assertEqual(len(tokens_node.children), 2)
        self.assertEqual(tokens_node.children[0].get_attribute("jid"), "5511999999999@s.whatsapp.net")
        self.assertEqual(tokens_node.children[1].get_attribute("jid"), "5511888888888@s.whatsapp.net")

if __name__ == "__main__":
    unittest.main()
