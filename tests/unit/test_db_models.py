"""
Testes unitários para db/models.py (schema unificado).
"""

from zowpy.db.models import (
    Account,
    Identity,
    Session,
    PreKey,
    SignedPreKey,
    ProfileConfig,
    ClientConfig,
    Contact,
    Group,
)


def test_account_model():
    assert Account.__tablename__ == "accounts"
    assert hasattr(Account, "phone")
    assert hasattr(Account, "env")
    assert hasattr(Account, "is_logged_in")
    assert hasattr(Account, "is_initialized")


def test_identity_model():
    assert Identity.__tablename__ == "identities"
    assert hasattr(Identity, "account_id")
    assert hasattr(Identity, "recipient_id")
    assert hasattr(Identity, "device_id")
    assert hasattr(Identity, "public_key")
    assert hasattr(Identity, "private_key")


def test_session_model():
    assert Session.__tablename__ == "sessions"
    assert hasattr(Session, "account_id")
    assert hasattr(Session, "recipient_id")
    assert hasattr(Session, "device_id")
    assert hasattr(Session, "record")


def test_prekey_model():
    assert PreKey.__tablename__ == "prekeys"
    assert hasattr(PreKey, "account_id")
    assert hasattr(PreKey, "prekey_id")
    assert hasattr(PreKey, "record")


def test_signed_prekey_model():
    assert SignedPreKey.__tablename__ == "signed_prekeys"
    assert hasattr(SignedPreKey, "account_id")
    assert hasattr(SignedPreKey, "prekey_id")
    assert hasattr(SignedPreKey, "record")


def test_profile_config_model():
    assert ProfileConfig.__tablename__ == "profile_configs"
    assert hasattr(ProfileConfig, "account_id")
    assert hasattr(ProfileConfig, "name")
    assert hasattr(ProfileConfig, "data")


def test_client_config_model():
    assert ClientConfig.__tablename__ == "client_configs"
    assert hasattr(ClientConfig, "account_id")
    assert hasattr(ClientConfig, "config_data")


def test_contact_model():
    assert Contact.__tablename__ == "contacts"
    assert hasattr(Contact, "account_id")
    assert hasattr(Contact, "jid")


def test_group_model():
    assert Group.__tablename__ == "groups"
    assert hasattr(Group, "group_jid")

