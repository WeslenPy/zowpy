import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

# Mock ProtocolNode e YowConstants antes de importar o client para evitar dependências circulares ou faltantes
class ProtocolNode:
    ID_TYPE_ANDROID = 1
    def __init__(self, tag, attributes=None, children=None, data=None):
        self.tag = tag
        self.attributes = attributes or {}
        self.children = children or []
        self.data = data
    def get_child(self, tag):
        for child in self.children:
            if child.tag == tag: return child
        return None
    def get_attribute(self, name):
        return self.attributes.get(name)

class YowConstants:
    WHATSAPP_SERVER = "s.whatsapp.net"
    WHATSAPP_GROUP_SERVER = "g.us"

# Patching necessário para evitar erros de importação de módulos não instalados no ambiente de teste
with patch.dict('sys.modules', {
    'zargo': MagicMock(),
    'zargo.utils': MagicMock(),
    'zargo.utils.jid': MagicMock(),
    'zowpy.protocol.structs': MagicMock(ProtocolNode=ProtocolNode),
    'zowpy.utils.constants': MagicMock(YowConstants=YowConstants)
}):
    from zowpy.core.client import WhatsAppClient as ZowClient

class TestSendMessageWithSync(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Mock do transport e loop
        self.loop = asyncio.get_event_loop()
        self.client = ZowClient(
            account_id="5573924570346"
        )
        
        # Mocks necessários
        self.client.contact_handler = MagicMock()
        self.client.contact_handler.trust_contact = AsyncMock()
        self.client.axolotl_manager = MagicMock()
        self.client._send_to_contacts_with_sessions = AsyncMock()
        self.client._get_keys_for_jids = AsyncMock(return_value=([], {}))

    async def test_ensure_sessions_and_send_to_contacts_with_sync(self):
        # Dados de teste
        target_jid = "559885700260@s.whatsapp.net"
        synced_devices = ["559885700260:0@s.whatsapp.net", "559885700260:1@s.whatsapp.net"]
        
        # Configura mocks
        self.client.contact_handler.sync_devices = AsyncMock(return_value=synced_devices)
        # Mock _get_keys_for_jids para retornar os JIDs sincronizados como se tivessem obtido chaves com sucesso
        self.client._get_keys_for_jids = AsyncMock(return_value=(synced_devices, {}))
        self.client.axolotl_manager.session_exists_bulk = AsyncMock(return_value=[]) # Nenhuma sessão inicial
        
        # Cria node de mensagem fake
        proto_node = ProtocolNode(tag="proto", attributes={"mediatype": "text"}, data=b"fake_proto")
        message_node = ProtocolNode(tag="message", attributes={"to": target_jid}, children=[proto_node])
        
        # Executa o método
        await self.client.ensure_sessions_and_send_to_contacts(message_node, [target_jid])
        
        # Verificações
        # 1. sync_devices deve ser chamado com o JID original
        self.client.contact_handler.sync_devices.assert_called_once_with([target_jid])
        
        # 2. session_exists_bulk deve ser chamado com os JIDs sincronizados
        self.client.axolotl_manager.session_exists_bulk.assert_called_once_with(synced_devices)
        
        # 3. _send_to_contacts_with_sessions deve ser chamado com os JIDs sincronizados
        self.assertTrue(self.client._send_to_contacts_with_sessions.called)
        called_jids = self.client._send_to_contacts_with_sessions.call_args[0][1]
        self.assertEqual(len(called_jids), 2)
        self.assertIn("559885700260:0@s.whatsapp.net", called_jids)
        self.assertIn("559885700260:1@s.whatsapp.net", called_jids)

    async def test_sync_devices_error_fallback(self):
        # Testa se o fluxo continua mesmo se o sync falhar
        target_jid = "559885700260@s.whatsapp.net"
        
        # Configura mock para falhar
        self.client.contact_handler.sync_devices = AsyncMock(side_effect=Exception("Sync failed"))
        self.client.axolotl_manager.session_exists_bulk = AsyncMock(return_value=[("559885700260", 0)])
        
        # Cria node de mensagem fake
        proto_node = ProtocolNode(tag="proto", attributes={"mediatype": "text"}, data=b"fake_proto")
        message_node = ProtocolNode(tag="message", attributes={"to": target_jid}, children=[proto_node])
        
        # Executa o método
        await self.client.ensure_sessions_and_send_to_contacts(message_node, [target_jid])
        
        # Deve ter chamado session_exists_bulk com o JID original
        self.client.axolotl_manager.session_exists_bulk.assert_called_once_with([target_jid])
        self.assertTrue(self.client._send_to_contacts_with_sessions.called)

if __name__ == "__main__":
    unittest.main()
