"""
Testes unitários para utils/coder.py
"""

import pytest
import zlib
from zowpy.utils.coder import ReadDecoder, WriteEncoder
from zowpy.utils.token_dict import TokenDictionary

# ProtocolTreeNode pode ser importado de diferentes lugares dependendo da estrutura
# Vamos usar um mock ou criar um node simples para os testes
try:
    from zowpy.protocol.nodes import ProtocolTreeNode
except ImportError:
    # Fallback: criar uma classe simples para testes
    class ProtocolTreeNode:
        def __init__(self, tag, attributes=None, children=None, data=None):
            self.tag = tag
            self.attributes = attributes or {}
            self.children = children or []
            self.data = data
        
        def hasChildren(self):
            return len(self.children) > 0


def test_read_decoder_init():
    """Testa inicialização do ReadDecoder"""
    token_dict = TokenDictionary()
    decoder = ReadDecoder(token_dict)
    assert decoder.tokenDictionary == token_dict


def test_read_decoder_read_int8():
    """Testa leitura de inteiro de 8 bits"""
    token_dict = TokenDictionary()
    decoder = ReadDecoder(token_dict)
    data = bytearray([42, 100])
    
    result = decoder.readInt8(data)
    assert result == 42
    assert len(data) == 1
    assert data[0] == 100


def test_read_decoder_read_int16():
    """Testa leitura de inteiro de 16 bits"""
    token_dict = TokenDictionary()
    decoder = ReadDecoder(token_dict)
    data = bytearray([0x12, 0x34])
    
    result = decoder.readInt16(data)
    assert result == 0x1200 + 0x34
    assert len(data) == 0


def test_read_decoder_read_int20():
    """Testa leitura de inteiro de 20 bits"""
    token_dict = TokenDictionary()
    decoder = ReadDecoder(token_dict)
    data = bytearray([0x0F, 0x12, 0x34])
    
    result = decoder.readInt20(data)
    assert result == ((0x0F & 0xF) << 16) | (0x12 << 8) | 0x34
    assert len(data) == 0


def test_read_decoder_read_int24():
    """Testa leitura de inteiro de 24 bits"""
    token_dict = TokenDictionary()
    decoder = ReadDecoder(token_dict)
    data = bytearray([0x12, 0x34, 0x56])
    
    result = decoder.readInt24(data)
    assert result == (0x12 << 16) + (0x34 << 8) + 0x56
    assert len(data) == 0


def test_read_decoder_read_array():
    """Testa leitura de array"""
    token_dict = TokenDictionary()
    decoder = ReadDecoder(token_dict)
    data = bytearray([1, 2, 3, 4, 5])
    
    result = decoder.readArray(3, data)
    assert result == [1, 2, 3]
    assert len(data) == 2
    assert list(data) == [4, 5]


def test_read_decoder_is_list_tag():
    """Testa verificação de tag de lista"""
    token_dict = TokenDictionary()
    decoder = ReadDecoder(token_dict)
    
    assert decoder.isListTag(248) == True
    assert decoder.isListTag(0) == True
    assert decoder.isListTag(249) == True
    assert decoder.isListTag(100) == False


def test_write_encoder_init():
    """Testa inicialização do WriteEncoder"""
    token_dict = TokenDictionary()
    encoder = WriteEncoder(token_dict)
    assert encoder.tokenDictionary == token_dict


def test_write_encoder_write_int8():
    """Testa escrita de inteiro de 8 bits"""
    token_dict = TokenDictionary()
    encoder = WriteEncoder(token_dict)
    data = []
    
    encoder.writeInt8(42, data)
    assert data == [42]


def test_write_encoder_write_int16():
    """Testa escrita de inteiro de 16 bits"""
    token_dict = TokenDictionary()
    encoder = WriteEncoder(token_dict)
    data = []
    
    encoder.writeInt16(0x1234, data)
    assert len(data) == 2
    assert data[0] == 0x12
    assert data[1] == 0x34


def test_write_encoder_write_int20():
    """Testa escrita de inteiro de 20 bits"""
    token_dict = TokenDictionary()
    encoder = WriteEncoder(token_dict)
    data = []
    
    encoder.writeInt20(0x12345, data)
    assert len(data) == 3


def test_write_encoder_write_int24():
    """Testa escrita de inteiro de 24 bits"""
    token_dict = TokenDictionary()
    encoder = WriteEncoder(token_dict)
    data = []
    
    encoder.writeInt24(0x123456, data)
    assert len(data) == 3
    assert data[0] == 0x12
    assert data[1] == 0x34
    assert data[2] == 0x56


def test_write_encoder_write_int31():
    """Testa escrita de inteiro de 31 bits"""
    token_dict = TokenDictionary()
    encoder = WriteEncoder(token_dict)
    data = []
    
    encoder.writeInt31(0x12345678, data)
    assert len(data) == 4


def test_write_encoder_write_list_start():
    """Testa escrita de início de lista"""
    token_dict = TokenDictionary()
    encoder = WriteEncoder(token_dict)
    data = []
    
    # Lista vazia
    encoder.writeListStart(0, data)
    assert data == [0]
    
    # Lista pequena (< 256)
    data = []
    encoder.writeListStart(100, data)
    assert data[0] == 248
    assert data[1] == 100
    
    # Lista grande (>= 256)
    data = []
    encoder.writeListStart(300, data)
    assert data[0] == 249
    assert len(data) == 3  # 249 + 2 bytes para 300


def test_write_encoder_write_token():
    """Testa escrita de token"""
    token_dict = TokenDictionary()
    encoder = WriteEncoder(token_dict)
    data = []
    
    encoder.writeToken(42, data)
    assert data == [42]
    
    # Token inválido
    with pytest.raises(ValueError):
        encoder.writeToken(256, data)
    
    with pytest.raises(ValueError):
        encoder.writeToken(-1, data)


def test_write_encoder_protocol_tree_node_to_bytes():
    """Testa codificação de ProtocolTreeNode"""
    token_dict = TokenDictionary()
    encoder = WriteEncoder(token_dict)
    
    node = ProtocolTreeNode("message", {"from": "test"})
    result = encoder.protocolTreeNodeToBytes(node)
    
    assert isinstance(result, list)
    assert len(result) > 0
    assert result[0] == 0  # Flags byte

