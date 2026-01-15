"""
Testes unitários para utils/protobuf.py
"""

import pytest
from unittest.mock import Mock
from zowpy.utils.protobuf import serialize_message, deserialize_message


def test_serialize_message_with_serialize_to_string():
    """Testa serialização com método SerializeToString"""
    message = Mock()
    message.SerializeToString = Mock(return_value=b"serialized_data")
    
    result = serialize_message(message)
    assert result == b"serialized_data"
    message.SerializeToString.assert_called_once()


def test_serialize_message_with_serialize():
    """Testa serialização com método serialize"""
    message = Mock()
    message.serialize = Mock(return_value=b"serialized_data")
    del message.SerializeToString  # Remove o outro método
    
    result = serialize_message(message)
    assert result == b"serialized_data"
    message.serialize.assert_called_once()


def test_serialize_message_no_method():
    """Testa serialização sem método disponível"""
    message = Mock()
    del message.SerializeToString
    del message.serialize
    
    with pytest.raises(ValueError, match="does not support serialization"):
        serialize_message(message)


def test_deserialize_message_with_parse_from_string():
    """Testa deserialização com método ParseFromString"""
    message_class = Mock()
    message_instance = Mock()
    message_class.return_value = message_instance
    message_instance.ParseFromString = Mock(return_value=None)
    
    data = b"serialized_data"
    result = deserialize_message(data, message_class)
    
    assert result == message_instance
    message_instance.ParseFromString.assert_called_once_with(data)


def test_deserialize_message_with_deserialize():
    """Testa deserialização com método deserialize"""
    message_class = Mock()
    message_instance = Mock()
    message_class.return_value = message_instance
    message_instance.deserialize = Mock(return_value=None)
    del message_instance.ParseFromString  # Remove o outro método
    
    data = b"serialized_data"
    result = deserialize_message(data, message_class)
    
    assert result == message_instance
    message_instance.deserialize.assert_called_once_with(data)


def test_deserialize_message_no_method():
    """Testa deserialização sem método disponível"""
    message_class = Mock()
    message_instance = Mock()
    message_class.return_value = message_instance
    del message_instance.ParseFromString
    del message_instance.deserialize
    
    data = b"serialized_data"
    with pytest.raises(ValueError, match="does not support deserialization"):
        deserialize_message(data, message_class)

