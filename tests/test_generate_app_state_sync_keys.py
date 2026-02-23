"""
Testes para generate_app_state_sync_keys do WhatsAppClient.
"""

import pytest
from unittest.mock import MagicMock, patch

from zowpy.core.client import WhatsAppClient
from zowpy.protocol.historysync.attributes import AppStateSyncKeyAttribute


@pytest.fixture
def client():
    """Client com config mockada (device_list). AsyncEventEmitter é mockado para não exigir event loop."""
    with patch("zowpy.core.client.AsyncEventEmitter", MagicMock()):
        c = WhatsAppClient(account_id="1234567890")
    c.config = MagicMock()
    c.config.device_list = []
    return c


def test_generate_app_state_sync_keys_returns_list_of_n(client):
    """generate_app_state_sync_keys(n) retorna lista com n elementos."""
    keys = client.generate_app_state_sync_keys(n=5)
    assert isinstance(keys, list)
    assert len(keys) == 5


def test_generate_app_state_sync_keys_default_n_is_10(client):
    """Sem argumento n, retorna 10 chaves."""
    keys = client.generate_app_state_sync_keys()
    assert len(keys) == 10


def test_generate_app_state_sync_keys_each_item_is_AppStateSyncKeyAttribute(client):
    """Cada elemento retornado é AppStateSyncKeyAttribute."""
    keys = client.generate_app_state_sync_keys(n=3)
    for key in keys:
        assert isinstance(key, AppStateSyncKeyAttribute)


def test_generate_app_state_sync_keys_key_id_is_6_bytes(client):
    """Cada chave tem key_id com 6 bytes."""
    keys = client.generate_app_state_sync_keys(n=3)
    for key in keys:
        assert key.key_id is not None
        assert isinstance(key.key_id.key_id, bytes)
        assert len(key.key_id.key_id) == 6


def test_generate_app_state_sync_keys_key_data_has_public_key_and_fingerprint(client):
    """Cada chave tem key_data com key_data (bytes), fingerprint e timestamp."""
    keys = client.generate_app_state_sync_keys(n=3)
    for i, key in enumerate(keys):
        assert key.key_data is not None
        assert isinstance(key.key_data.key_data, bytes)
        assert len(key.key_data.key_data) > 0
        assert key.key_data.fingerprint is not None
        assert key.key_data.fingerprint.current_index == i
        assert isinstance(key.key_data.timestamp, int)
        assert key.key_data.timestamp > 0


def test_generate_app_state_sync_keys_uses_config_device_list(client):
    """device_list do config é repassado ao fingerprint."""
    client.config.device_list = [1, 2, 3]
    keys = client.generate_app_state_sync_keys(n=2)
    for key in keys:
        assert key.key_data.fingerprint.device_indexes == [1, 2, 3]


def test_generate_app_state_sync_keys_device_list_none_uses_empty_list(client):
    """Se config.device_list for None, fingerprint usa lista vazia."""
    client.config.device_list = None
    keys = client.generate_app_state_sync_keys(n=1)
    assert keys[0].key_data.fingerprint.device_indexes == []
