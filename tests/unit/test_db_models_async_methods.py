"""
Testes unitários para métodos async dos modelos de banco de dados.
Testa todos os métodos async implementados seguindo o padrão do trustedcontact.py
"""

import pytest
import tempfile
import os
from time import time

from zowpy.db.config.engine import AsyncSessionMaker
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from zowpy.db.config.base import Model
from zowpy.db.models.account import Account
from zowpy.db.models.trustedcontact import TrustedContact
from zowpy.db.models.contact import Contact
from zowpy.db.models.broadcast import Broadcast
from zowpy.db.models.prekey import PreKey
from zowpy.db.models.signedprekey import SignedPreKey
from zowpy.db.models.senderkey import SenderKey
from zowpy.db.models.sessionkey import SessionKey
from zowpy.db.models.identity import Identity
from zowpy.db.models.poll import Poll
from zowpy.db.models.polloption import PollOption
from zowpy.db.models.appstatekey import AppStateKey
from zowpy.utils.constants import YowConstants
from zowpy.db.exceptions import InvalidKeyIdException


@pytest.fixture
async def db_pool():
    """Fixture que cria um banco de dados temporário para os testes"""
    temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = temp_file.name
    temp_file.close()
    
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    
    # Inicializa banco de dados (cria tabelas)
    async with session_maker() as session:
        async with engine.begin() as conn:
            await conn.run_sync(Model.metadata.create_all)
        await session.commit()
    
    yield session_maker
    
    # Cleanup
    await engine.dispose()
    try:
        os.unlink(db_path)
    except Exception:
        pass


@pytest.fixture
async def test_account(db_pool):
    """Fixture que cria uma conta de teste"""
    async with db_pool() as session:
        account = Account(phone="5511999999999")
        session.add(account)
        await session.commit()
        await session.refresh(account)
        yield account


@pytest.fixture
async def session(db_pool):
    """Fixture que fornece uma sessão async"""
    async with db_pool() as session:
        yield session


# ============ TrustedContact Tests ============

@pytest.mark.asyncio
async def test_trusted_contact_update_get_remove(db_pool, test_account, session):
    """Testa métodos async de TrustedContact"""
    jid = f"5511888888888@{YowConstants.WHATSAPP_SERVER}"
    token = b"test_token_12345"
    
    # Test update_trusted_contact
    result = await TrustedContact.update_trusted_contact(
        session, test_account.id, jid, token
    )
    assert result is True
    
    # Test get_tc_token
    retrieved_token = await TrustedContact.get_tc_token(
        session, test_account.id, jid
    )
    assert retrieved_token == token
    
    # Test remove_trusted_contact
    result = await TrustedContact.remove_trusted_contact(
        session, test_account.id, jid
    )
    assert result is True
    
    # Verify it's removed
    retrieved_token = await TrustedContact.get_tc_token(
        session, test_account.id, jid
    )
    assert retrieved_token is None


@pytest.mark.asyncio
async def test_trusted_contact_validation(db_pool, test_account, session):
    """Testa validações de JID no TrustedContact"""
    invalid_jid = "invalid_jid"
    token = b"test_token"
    
    # Should return False for invalid JID
    result = await TrustedContact.update_trusted_contact(
        session, test_account.id, invalid_jid, token
    )
    assert result is False
    
    # Should return False for None token
    valid_jid = f"5511888888888@{YowConstants.WHATSAPP_SERVER}"
    result = await TrustedContact.update_trusted_contact(
        session, test_account.id, valid_jid, None
    )
    assert result is False


# ============ Contact Tests ============

@pytest.mark.asyncio
async def test_contact_add_find_remove(db_pool, test_account, session):
    """Testa métodos async de Contact"""
    jid = f"5511888888888@{YowConstants.WHATSAPP_SERVER}"
    name = "Test Contact"
    
    # Test add_contact
    result = await Contact.add_contact(session, test_account.id, jid, name)
    assert result == jid
    
    # Test find_contact
    found = await Contact.find_contact(session, test_account.id, jid)
    assert found is True
    
    # Test is_new_contact
    is_new = await Contact.is_new_contact(session, test_account.id, jid)
    assert is_new is False
    
    # Test get_all_contacts
    all_contacts = await Contact.get_all_contacts(session, test_account.id)
    assert jid in all_contacts
    
    # Test remove_contact
    result = await Contact.remove_contact(session, test_account.id, jid)
    assert result is True
    
    # Verify it's removed
    found = await Contact.find_contact(session, test_account.id, jid)
    assert found is False


@pytest.mark.asyncio
async def test_contact_validation(db_pool, test_account, session):
    """Testa validações de JID no Contact"""
    invalid_jid = "invalid_jid"
    
    result = await Contact.add_contact(session, test_account.id, invalid_jid, "Name")
    assert result is None
    
    found = await Contact.find_contact(session, test_account.id, invalid_jid)
    assert found is False


# ============ Broadcast Tests ============

@pytest.mark.asyncio
async def test_broadcast_phash():
    """Testa método estático phash"""
    jids = ["user1@whatsapp.net", "user2@whatsapp.net", "user3@whatsapp.net"]
    phash = Broadcast.phash_sha256(jids)
    assert phash.startswith("2:")
    assert len(phash) > 2
    
    # Should be deterministic
    phash2 = Broadcast.phash_sha256(jids)
    assert phash == phash2


@pytest.mark.asyncio
async def test_broadcast_add_find(db_pool, test_account, session):
    """Testa métodos async de Broadcast"""
    jids = ["5511888888888@s.whatsapp.net", "5511777777777@s.whatsapp.net"]
    sender_jid = f"{test_account.phone}@{YowConstants.WHATSAPP_SERVER}"
    name = "Test Broadcast"
    
    # Test add_broadcast
    bcid, phash = await Broadcast.add_broadcast(
        session, test_account.id, jids, sender_jid, name
    )
    assert bcid is not None
    assert phash is not None
    
    # Test find_participants_by_bcid
    participants = await Broadcast.find_participants_by_bcid(
        session, test_account.id, bcid
    )
    assert isinstance(participants, list)
    assert sender_jid not in participants
    
    # Test find_broadcast_by_phash
    found_bcid, found_phash = await Broadcast.find_broadcast_by_phash(
        session, test_account.id, phash
    )
    assert found_bcid == bcid
    assert found_phash == phash


# ============ PreKey Tests ============

@pytest.mark.asyncio
async def test_prekey_store_load_remove(db_pool, test_account, session):
    """Testa métodos async de PreKey"""
    prekey_id = 1
    record = b"test_prekey_record_data"
    
    # Test store_prekey
    await PreKey.store_prekey(session, test_account.id, prekey_id, record)
    
    # Test contains_prekey
    exists = await PreKey.contains_prekey(session, test_account.id, prekey_id)
    assert exists is True
    
    # Test load_prekey
    from zowpy.axolotl.state.prekeyrecord import PreKeyRecord
    loaded_prekey = await PreKey.load_prekey(session, test_account.id, prekey_id)
    assert isinstance(loaded_prekey, PreKeyRecord)
    # Compare serialized versions since record is bytes
    assert loaded_prekey.serialize() == record
    
    # Test remove_prekey
    await PreKey.remove_prekey(session, test_account.id, prekey_id)
    
    # Verify it's removed
    exists = await PreKey.contains_prekey(session, test_account.id, prekey_id)
    assert exists is False
    
    # Should raise InvalidKeyIdException
    with pytest.raises(InvalidKeyIdException):
        await PreKey.load_prekey(session, test_account.id, prekey_id)


@pytest.mark.asyncio
async def test_prekey_load_pending(db_pool, test_account, session):
    """Testa carregamento de prekeys pendentes"""
    from zowpy.axolotl.state.prekeyrecord import PreKeyRecord
    # Add some prekeys
    for i in range(5):
        prekey_record = PreKeyRecord()
        record = prekey_record.serialize()
        await PreKey.store_prekey(session, test_account.id, i, record)
    
    # Test load_pending_prekeys
    pending = await PreKey.load_pending_prekeys(session, test_account.id)
    assert len(pending) == 5
    
    # Test load_unsent_pending_prekeys (all should be unsent initially)
    unsent = await PreKey.load_unsent_pending_prekeys(session, test_account.id)
    assert len(unsent) == 5
    
    # Mark some as sent
    await PreKey.set_as_sent(session, test_account.id, [0, 1, 2])
    
    # Should only return unsent ones
    unsent = await PreKey.load_unsent_pending_prekeys(session, test_account.id)
    assert len(unsent) == 2


@pytest.mark.asyncio
async def test_prekey_max_id_clear(db_pool, test_account, session):
    """Testa load_max_prekey_id e clear_prekeys"""
    from zowpy.axolotl.state.prekeyrecord import PreKeyRecord
    
    # Add prekeys with various IDs
    for i in [1, 5, 10, 15, 20]:
        prekey_record = PreKeyRecord()
        record = prekey_record.serialize()
        await PreKey.store_prekey(session, test_account.id, i, record)
    
    # Test load_max_prekey_id
    max_id = await PreKey.load_max_prekey_id(session, test_account.id)
    assert max_id == 20
    
    # Test clear_prekeys
    await PreKey.clear_prekeys(session, test_account.id)
    
    # Verify all are removed
    pending = await PreKey.load_pending_prekeys(session, test_account.id)
    assert len(pending) == 0


# ============ SignedPreKey Tests ============

@pytest.mark.asyncio
async def test_signed_prekey_store_load_remove(db_pool, test_account, session):
    """Testa métodos async de SignedPreKey"""
    from zowpy.axolotl.state.signedprekeyrecord import SignedPreKeyRecord
    
    prekey_id = 1
    timestamp = int(time())
    record = SignedPreKeyRecord().serialize()
    
    # Test store_signed_prekey
    await SignedPreKey.store_signed_prekey(
        session, test_account.id, prekey_id, timestamp, record
    )
    
    # Test contains_signed_prekey
    exists = await SignedPreKey.contains_signed_prekey(
        session, test_account.id, prekey_id
    )
    assert exists is True
    
    # Test load_signed_prekey
    loaded = await SignedPreKey.load_signed_prekey(
        session, test_account.id, prekey_id
    )
    assert isinstance(loaded, SignedPreKeyRecord)
    assert loaded.serialize() == record
    
    # Test remove_signed_prekey
    result = await SignedPreKey.remove_signed_prekey(
        session, test_account.id, prekey_id
    )
    assert result is True
    
    # Should raise InvalidKeyIdException
    with pytest.raises(InvalidKeyIdException):
        await SignedPreKey.load_signed_prekey(session, test_account.id, prekey_id)


@pytest.mark.asyncio
async def test_signed_prekey_load_all(db_pool, test_account, session):
    """Testa load_signed_prekeys"""
    from zowpy.axolotl.state.signedprekeyrecord import SignedPreKeyRecord
    
    # Add multiple signed prekeys
    for i in range(3):
        record = SignedPreKeyRecord().serialize()
        await SignedPreKey.store_signed_prekey(
            session, test_account.id, i, int(time()), record
        )
    
    # Test load_signed_prekeys
    all_keys = await SignedPreKey.load_signed_prekeys(session, test_account.id)
    assert len(all_keys) == 3


# ============ SenderKey Tests ============

@pytest.mark.asyncio
async def test_sender_key_store_load(db_pool, test_account, session):
    """Testa métodos async de SenderKey"""
    from zowpy.axolotl.groups.state.senderkeyrecord import SenderKeyRecord
    
    group_id = "120363123456789012@g.us"
    sender_id = "5511888888888"
    record = SenderKeyRecord().serialize()
    
    # Test store_sender_key
    await SenderKey.store_sender_key(
        session, test_account.id, group_id, sender_id, record
    )
    
    # Test load_sender_key
    loaded = await SenderKey.load_sender_key(
        session, test_account.id, group_id, sender_id
    )
    assert isinstance(loaded, SenderKeyRecord)
    assert len(loaded.serialize()) > 0
    
    # Test update existing
    new_record = SenderKeyRecord().serialize()
    await SenderKey.store_sender_key(
        session, test_account.id, group_id, sender_id, new_record
    )
    
    loaded = await SenderKey.load_sender_key(
        session, test_account.id, group_id, sender_id
    )
    assert loaded.serialize() == new_record


@pytest.mark.asyncio
async def test_sender_key_load_nonexistent(db_pool, test_account, session):
    """Testa load_sender_key com chave inexistente"""
    from zowpy.axolotl.groups.state.senderkeyrecord import SenderKeyRecord
    
    group_id = "nonexistent@g.us"
    sender_id = "5511999999999"
    
    loaded = await SenderKey.load_sender_key(
        session, test_account.id, group_id, sender_id
    )
    assert isinstance(loaded, SenderKeyRecord)
    # Empty record should be returned
    assert len(loaded.serialize()) == 0


# ============ SessionKey Tests ============

@pytest.mark.asyncio
async def test_session_store_load_delete(db_pool, test_account, session):
    """Testa métodos async de SessionKey"""
    from zowpy.axolotl.state.sessionrecord import SessionRecord
    
    recipient_id = 5511888888888
    device_id = 0
    record = SessionRecord().serialize()
    
    # Test store_session
    await SessionKey.store_session(
        session, test_account.id, recipient_id, device_id, record
    )
    
    # Test contains_session
    exists = await SessionKey.contains_session(
        session, test_account.id, recipient_id, device_id
    )
    assert exists is True
    
    # Test load_session
    loaded = await SessionKey.load_session(
        session, test_account.id, recipient_id, device_id
    )
    assert isinstance(loaded, SessionRecord)
    assert loaded.serialize() == record
    
    # Test delete_session
    await SessionKey.delete_session(
        session, test_account.id, recipient_id, device_id
    )
    
    # Verify it's deleted
    exists = await SessionKey.contains_session(
        session, test_account.id, recipient_id, device_id
    )
    assert exists is False


@pytest.mark.asyncio
async def test_session_sub_devices(db_pool, test_account, session):
    """Testa get_sub_device_sessions"""
    from zowpy.axolotl.state.sessionrecord import SessionRecord
    
    recipient_id = 5511888888888
    record = SessionRecord().serialize()
    
    # Add multiple device sessions
    for device_id in [0, 1, 2]:
        await SessionKey.store_session(
            session, test_account.id, recipient_id, device_id, record
        )
    
    # Test get_sub_device_sessions
    devices = await SessionKey.get_sub_device_sessions(
        session, test_account.id, recipient_id
    )
    assert set(devices) == {0, 1, 2}
    
    # Test delete_all_sessions
    await SessionKey.delete_all_sessions(session, test_account.id, recipient_id)
    
    devices = await SessionKey.get_sub_device_sessions(
        session, test_account.id, recipient_id
    )
    assert len(devices) == 0


@pytest.mark.asyncio
async def test_session_get_all_accounts(db_pool, test_account, session):
    """Testa get_all_accounts"""
    from zowpy.axolotl.state.sessionrecord import SessionRecord
    
    recipient_id = 5511888888888
    record = SessionRecord().serialize()
    
    # Add session
    await SessionKey.store_session(
        session, test_account.id, recipient_id, 0, record
    )
    
    # Test get_all_accounts
    accounts = await SessionKey.get_all_accounts(
        session, test_account.id, recipient_id
    )
    assert len(accounts) > 0
    assert any(recipient_id in acc for acc in accounts)


# ============ Identity Tests ============

@pytest.mark.asyncio
async def test_identity_store_local_data(db_pool, test_account, session):
    """Testa store_local_data, get_local_registration_id, get_identity_key_pair"""
    from zowpy.axolotl.util.keyhelper import KeyHelper
    from zowpy.axolotl.identitykeypair import IdentityKeyPair
    
    # Generate identity and registration ID
    identity = KeyHelper.generateIdentityKeyPair()
    registration_id = KeyHelper.generateRegistrationId(True)
    
    # Test store_local_data
    await Identity.store_local_data(
        session, test_account.id, registration_id, identity, 0
    )
    
    # Test get_local_registration_id
    retrieved_reg_id = await Identity.get_local_registration_id(
        session, test_account.id
    )
    assert retrieved_reg_id == registration_id
    
    # Test get_identity_key_pair
    retrieved_identity = await Identity.get_identity_key_pair(
        session, test_account.id
    )
    assert isinstance(retrieved_identity, IdentityKeyPair)


@pytest.mark.asyncio
async def test_identity_save_is_trusted(db_pool, test_account, session):
    """Testa save_identity e is_trusted_identity"""
    from zowpy.axolotl.identitykey import IdentityKey
    from zowpy.axolotl.ecc.djbec import DjbECPublicKey
    
    recipient_id = 5511888888888
    device_id = 0
    
    # Create identity key
    pub_key_bytes = b'\x05' + b'\x00' * 32  # EC public key format
    pub_key = DjbECPublicKey(pub_key_bytes[1:])
    identity_key = IdentityKey(pub_key)
    
    # Test save_identity
    await Identity.save_identity(
        session, test_account.id, recipient_id, device_id, identity_key
    )
    
    # Test is_trusted_identity (should return True if keys match)
    is_trusted = await Identity.is_trusted_identity(
        session, test_account.id, recipient_id, device_id, identity_key
    )
    assert is_trusted is True
    
    # Test with different key (should return False)
    pub_key_bytes2 = b'\x05' + b'\x01' * 32
    pub_key2 = DjbECPublicKey(pub_key_bytes2[1:])
    identity_key2 = IdentityKey(pub_key2)
    
    is_trusted = await Identity.is_trusted_identity(
        session, test_account.id, recipient_id, device_id, identity_key2
    )
    assert is_trusted is False


@pytest.mark.asyncio
async def test_identity_trusted_nonexistent(db_pool, test_account, session):
    """Testa is_trusted_identity com identidade inexistente"""
    from zowpy.axolotl.identitykey import IdentityKey
    from zowpy.axolotl.ecc.djbec import DjbECPublicKey
    
    recipient_id = 9999999999
    device_id = 0
    pub_key_bytes = b'\x05' + b'\x00' * 32
    pub_key = DjbECPublicKey(pub_key_bytes[1:])
    identity_key = IdentityKey(pub_key)
    
    # Should return True (trust by default if no identity stored)
    is_trusted = await Identity.is_trusted_identity(
        session, test_account.id, recipient_id, device_id, identity_key
    )
    assert is_trusted is True


# ============ Poll Tests ============

@pytest.mark.asyncio
async def test_poll_store_delete(db_pool, test_account, session):
    """Testa store_poll e delete_poll"""
    poll_msg_id = 12345
    name = "Test Poll"
    enc_key = b"encryption_key_12345"
    options = ["Option 1", "Option 2", "Option 3"]
    
    # Test store_poll
    await Poll.store_poll(
        session, test_account.id, poll_msg_id, name, enc_key, options
    )
    
    # Test get_poll_enc_key
    retrieved_key = await Poll.get_poll_enc_key(
        session, test_account.id, poll_msg_id
    )
    assert retrieved_key == enc_key
    
    # Test decrypt_options
    import hashlib
    option_sha256_list = [hashlib.sha256(opt.encode()).digest() for opt in options]
    decrypted = await Poll.decrypt_options(
        session, test_account.id, poll_msg_id, option_sha256_list
    )
    assert decrypted == options
    
    # Test delete_poll
    await Poll.delete_poll(session, test_account.id, poll_msg_id)
    
    # Verify it's deleted
    retrieved_key = await Poll.get_poll_enc_key(
        session, test_account.id, poll_msg_id
    )
    assert retrieved_key is None


@pytest.mark.asyncio
async def test_poll_decrypt_invalid_sha256(db_pool, test_account, session):
    """Testa decrypt_options com SHA256 inválido"""
    poll_msg_id = 12346
    name = "Test Poll"
    enc_key = b"encryption_key"
    options = ["Option 1", "Option 2"]
    
    await Poll.store_poll(
        session, test_account.id, poll_msg_id, name, enc_key, options
    )
    
    # Test with invalid SHA256
    invalid_sha256_list = [b"invalid_sha256"]
    decrypted = await Poll.decrypt_options(
        session, test_account.id, poll_msg_id, invalid_sha256_list
    )
    assert decrypted == ["ITEM ERROR"]


# ============ AppStateKey Tests ============

@pytest.mark.asyncio
async def test_app_state_key_add_get_delete(db_pool, test_account, session):
    """Testa métodos async de AppStateKey"""
    from zowpy.protocol.historysync.attributes import (
        AppStateSyncKeyAttribute,
        AppStateSyncKeyIdAttribute,
        AppStateSyncKeyDataAttribute,
    )
    
    # Create test keys
    keys = []
    for i in range(3):
        key = AppStateSyncKeyAttribute(
            key_id=AppStateSyncKeyIdAttribute(key_id=f"key_id_{i}".encode()),
            key_data=AppStateSyncKeyDataAttribute(
                key_data=f"key_data_{i}".encode(),
                fingerprint=None,
                timestamp=int(time()) + i
            )
        )
        keys.append(key)
    
    # Test add_app_state_keys
    await AppStateKey.add_app_state_keys(session, test_account.id, keys)
    
    # Test get_one_app_state_key
    one_key = await AppStateKey.get_one_app_state_key(session, test_account.id)
    assert one_key is not None
    assert isinstance(one_key, AppStateSyncKeyAttribute)
    
    # Test get_app_state_key by key_id
    key_id = keys[0].key_id.key_id
    retrieved_key = await AppStateKey.get_app_state_key(
        session, test_account.id, key_id
    )
    assert retrieved_key is not None
    assert retrieved_key.key_id.key_id == key_id
    
    # Test delete_app_state_key
    await AppStateKey.delete_app_state_key(session, test_account.id, key_id)
    
    # Verify it's deleted
    retrieved_key = await AppStateKey.get_app_state_key(
        session, test_account.id, key_id
    )
    assert retrieved_key is None


@pytest.mark.asyncio
async def test_app_state_key_get_nonexistent(db_pool, test_account, session):
    """Testa get_app_state_key com key_id inexistente"""
    key_id = b"nonexistent_key_id"
    retrieved_key = await AppStateKey.get_app_state_key(
        session, test_account.id, key_id
    )
    assert retrieved_key is None


# ============ Error Handling Tests ============

@pytest.mark.asyncio
async def test_methods_require_session(db_pool, test_account):
    """Testa que métodos requerem session como primeiro parâmetro"""
    jid = f"5511888888888@{YowConstants.WHATSAPP_SERVER}"
    
    # Now session is required as first parameter (not optional)
    # Tests will fail if called incorrectly at runtime due to TypeError
    # This test is kept for documentation purposes
    pass

