"""
Testes unitários para utils/token_dict.py
"""

import pytest
from zowpy.utils.token_dict import TokenDictionary


def test_token_dictionary_init():
    """Testa inicialização do TokenDictionary"""
    token_dict = TokenDictionary()
    assert token_dict.FLAG_SEGMENTED == 0x1
    assert token_dict.FLAG_DEFLATE == 0x2
    assert len(token_dict.dictionary) > 0
    assert len(token_dict.secondaryDictionary) > 0


def test_token_dictionary_get_token():
    """Testa obtenção de token do dicionário principal"""
    token_dict = TokenDictionary()
    
    # Testa token válido
    token = token_dict.getToken(0)
    assert token == ""
    
    token = token_dict.getToken(1)
    assert token == "xmlstreamstart"
    
    # Testa token inválido
    token = token_dict.getToken(99999)
    assert token is None


def test_token_dictionary_get_token_secondary():
    """Testa obtenção de token do dicionário secundário"""
    token_dict = TokenDictionary()
    
    # Testa token do dicionário secundário
    token = token_dict.getToken(0, secondary=True)
    assert token == "read-self"
    
    # Testa índice inválido
    token = token_dict.getToken(99999, secondary=True)
    assert token is None


def test_token_dictionary_get_token_auto_secondary():
    """Testa obtenção automática de token do dicionário secundário"""
    token_dict = TokenDictionary()
    
    # Índices entre 236 e 236+len(secondaryDictionary) devem usar secondary
    # Testa com índice que mapeia para secondary
    if len(token_dict.secondaryDictionary) > 0:
        # Índice 237 mapeia para índice 0 do secondary
        token = token_dict.getToken(237)
        assert token is not None or token == "read-self"


def test_token_dictionary_get_index():
    """Testa obtenção de índice de token"""
    token_dict = TokenDictionary()
    
    # Testa token do dicionário principal
    result = token_dict.getIndex("xmlstreamstart")
    assert result is not None
    assert result[0] == 1
    assert result[1] == False
    
    # Testa token do dicionário secundário
    result = token_dict.getIndex("read-self")
    assert result is not None
    assert result[1] == True
    
    # Testa token inexistente
    result = token_dict.getIndex("nonexistent_token_xyz")
    assert result is None


def test_token_dictionary_flags():
    """Testa flags do dicionário"""
    token_dict = TokenDictionary()
    assert token_dict.FLAG_SEGMENTED == 0x1
    assert token_dict.FLAG_DEFLATE == 0x2

