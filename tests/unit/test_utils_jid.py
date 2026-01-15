"""
Testes unitários para utils/jid.py
"""

import pytest
from zowpy.utils.jid import normalize, to_whatsapp_jid


def test_normalize_empty():
    """Testa normalização de JID vazio"""
    assert normalize("") is None
    assert normalize(None) is None


def test_normalize_whatsapp_jid():
    """Testa normalização de JID do WhatsApp"""
    jid = "1234567890@s.whatsapp.net"
    result = normalize(jid)
    assert result == "1234567890"


def test_normalize_group_jid():
    """Testa normalização de JID de grupo"""
    jid = "123456789@g.us"
    result = normalize(jid)
    assert result == "123456789"


def test_normalize_with_non_digits():
    """Testa normalização removendo caracteres não numéricos"""
    jid = "123-456-7890"
    result = normalize(jid)
    assert result == "1234567890"


def test_normalize_only_non_digits():
    """Testa normalização com apenas caracteres não numéricos"""
    jid = "abc@def"
    result = normalize(jid)
    assert result is None


def test_to_whatsapp_jid_regular():
    """Testa conversão para JID regular do WhatsApp"""
    jid = "1234567890"
    result = to_whatsapp_jid(jid)
    assert result == "1234567890@s.whatsapp.net"


def test_to_whatsapp_jid_group():
    """Testa conversão para JID de grupo"""
    jid = "123456789"
    result = to_whatsapp_jid(jid, is_group=True)
    assert result == "123456789@g.us"


def test_to_whatsapp_jid_with_suffix():
    """Testa conversão de JID que já tem sufixo"""
    jid = "1234567890@s.whatsapp.net"
    result = to_whatsapp_jid(jid)
    assert result == "1234567890@s.whatsapp.net"


def test_to_whatsapp_jid_invalid():
    """Testa conversão de JID inválido"""
    with pytest.raises(ValueError, match="Invalid JID"):
        to_whatsapp_jid("")
    
    with pytest.raises(ValueError, match="Invalid JID"):
        to_whatsapp_jid("abc")

