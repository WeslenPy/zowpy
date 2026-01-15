"""
Testes unitários para `zowpy.db.manager.AxolotlManager`.

Nota: estes testes validam a API/contratos básicos sem depender de DB real.
"""

from unittest.mock import MagicMock, patch, AsyncMock

from zowpy.db.manager import AxolotlManager


def test_axolotl_manager_init_reads_identity_and_registration():
    store = MagicMock()
    store.getIdentityKeyPair.return_value = MagicMock()
    store.getLocalRegistrationId.return_value = 12345

    manager = AxolotlManager(store, "5511999999999")
    assert manager.identity is not None
    assert manager.registration_id == 12345


async def test_axolotl_manager_level_prekeys_generates_when_below_threshold():
    store = MagicMock()
    store.getIdentityKeyPair.return_value = MagicMock()
    store.getLocalRegistrationId.return_value = 12345

    # Abaixo do threshold
    store.loadPreKeys.return_value = []

    prekey_store = MagicMock()
    prekey_store.loadMaxPreKeyId.return_value = 10
    prekey_store.setAsSent.return_value = None
    store.preKeyStore = prekey_store

    store.storePreKey.return_value = None

    manager = AxolotlManager(store, "5511999999999")

    fake_prekeys = [MagicMock(getId=MagicMock(return_value=i)) for i in range(11, 14)]
    with patch("zowpy.db.manager.KeyHelper.generatePreKeys", new_callable=AsyncMock, return_value=fake_prekeys):
        prekeys = await manager.level_prekeys(force=False)

    assert prekeys == fake_prekeys
    assert store.storePreKey.called

