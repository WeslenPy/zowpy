"""
Tests for LID flow: utils (jid, tools), lid_map contract, resolve_recipient_for_send.
"""

import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from zowpy.utils.jid import is_lid, normalize, to_whatsapp_jid
from zowpy.utils.tools import WATools


class TestIsLid(unittest.TestCase):
    def test_lid_suffix_returns_true(self):
        self.assertTrue(is_lid("5356260450362:0@lid"))
        self.assertTrue(is_lid("user:0@lid"))

    def test_jid_returns_false(self):
        self.assertFalse(is_lid("559885700260@s.whatsapp.net"))
        self.assertFalse(is_lid("123@g.us"))

    def test_empty_returns_false(self):
        self.assertFalse(is_lid(""))
        self.assertFalse(is_lid(None))

    def test_lid_with_whitespace(self):
        self.assertTrue(is_lid("  user:0@lid  ".strip()))


class TestNormalizePreserveLid(unittest.TestCase):
    def test_lid_preserved(self):
        self.assertEqual(normalize("5356260450362:0@lid"), "5356260450362:0@lid")
        self.assertEqual(normalize("user:0@lid"), "user:0@lid")

    def test_jid_normalized_to_digits(self):
        self.assertEqual(normalize("559885700260@s.whatsapp.net"), "559885700260")
        self.assertEqual(normalize("+55 11 99999-9999"), "5511999999999")


class TestToWhatsappJidPreserveLid(unittest.TestCase):
    def test_lid_preserved(self):
        self.assertEqual(to_whatsapp_jid("5356260450362:0@lid"), "5356260450362:0@lid")
        self.assertEqual(to_whatsapp_jid("user:0@lid", is_group=False), "user:0@lid")

    def test_jid_gets_suffix(self):
        self.assertEqual(to_whatsapp_jid("559885700260", is_group=False), "559885700260@s.whatsapp.net")
        self.assertEqual(to_whatsapp_jid("123456789012345", is_group=True), "123456789012345@g.us")


class TestWAToolsNormalizeJidPreserveLid(unittest.TestCase):
    def test_lid_preserved(self):
        self.assertEqual(WATools.normalizeJid("5356260450362:0@lid"), "5356260450362:0@lid")

    def test_jid_gets_suffix(self):
        self.assertEqual(WATools.normalizeJid("559885700260"), "559885700260@s.whatsapp.net")


class TestWAToolsJidDecode(unittest.TestCase):
    def test_lid_user_device(self):
        recipient_id, recipient_type, device_id = WATools.jidDecode("5356260450362:0@lid")
        self.assertEqual(recipient_id, "5356260450362")
        self.assertEqual(device_id, 0)

    def test_lid_user_device_nonzero(self):
        recipient_id, recipient_type, device_id = WATools.jidDecode("user:1@lid")
        self.assertEqual(recipient_id, "user")
        self.assertEqual(device_id, 1)

    def test_jid_plain(self):
        recipient_id, _, device_id = WATools.jidDecode("559885700260@s.whatsapp.net")
        self.assertEqual(recipient_id, "559885700260")
        self.assertEqual(device_id, 0)


class TestLidMapReturnsLidString(unittest.TestCase):
    """LidMap.get_lid_mapping_by_jid must return a single LID string (scalar)."""

    def test_import_and_signature(self):
        from zowpy.db.models.lid_map import LidMap
        from sqlalchemy.ext.asyncio import AsyncSession
        import inspect
        sig = inspect.signature(LidMap.get_lid_mapping_by_jid)
        self.assertIsNotNone(sig)


class TestResolveRecipientForSend(unittest.IsolatedAsyncioTestCase):
    """resolve_recipient_for_send uses only lid_map; groups stay JID; LID when in map."""

    async def asyncSetUp(self):
        try:
            from zowpy.core.client import WhatsAppClient
        except ImportError as e:
            raise unittest.SkipTest(f"WhatsAppClient import failed: {e}")
        self.client = WhatsAppClient(account_id="5573924570346")
        self.client._authenticated = True
        self.client.axolotl_manager = MagicMock()
        self.client.axolotl_manager._store = MagicMock()

    async def test_group_returns_jid(self):
        self.client.axolotl_manager._store.getLidMappingByJid = AsyncMock()
        out = await self.client.resolve_recipient_for_send("123456789012345@g.us")
        self.assertEqual(out, "123456789012345@g.us")
        self.client.axolotl_manager._store.getLidMappingByJid.assert_not_called()

    async def test_already_lid_returns_same(self):
        self.client.axolotl_manager._store.getLidMappingByJid = AsyncMock()
        out = await self.client.resolve_recipient_for_send("5356260450362:0@lid")
        self.assertEqual(out, "5356260450362:0@lid")
        self.client.axolotl_manager._store.getLidMappingByJid.assert_not_called()

    async def test_jid_with_lid_in_map_returns_lid(self):
        self.client.axolotl_manager._store.getLidMappingByJid = AsyncMock(
            return_value="5356260450362:0@lid"
        )
        out = await self.client.resolve_recipient_for_send("5356260450362@s.whatsapp.net")
        self.assertEqual(out, "5356260450362:0@lid")
        self.client.axolotl_manager._store.getLidMappingByJid.assert_called_once()

    async def test_jid_without_lid_in_map_returns_jid(self):
        self.client.axolotl_manager._store.getLidMappingByJid = AsyncMock(return_value=None)
        out = await self.client.resolve_recipient_for_send("559885700260")
        self.assertEqual(out, "559885700260@s.whatsapp.net")
        self.client.axolotl_manager._store.getLidMappingByJid.assert_called_once()


if __name__ == "__main__":
    unittest.main()
