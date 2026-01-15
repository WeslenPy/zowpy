"""
Testes unitários para protocol/nodes.py
"""

import pytest
import asyncio
from zowpy.protocol.nodes import ProtocolTreeNode


def test_protocol_tree_node_init():
    """Testa inicialização do ProtocolTreeNode"""
    node = ProtocolTreeNode("message")
    assert node.tag == "message"
    assert node.attributes == {}
    assert node.children == []
    assert node.data is None


def test_protocol_tree_node_init_with_attributes():
    """Testa inicialização com atributos"""
    attrs = {"from": "test@whatsapp.net", "to": "other@whatsapp.net"}
    node = ProtocolTreeNode("message", attrs)
    assert node.attributes == attrs


def test_protocol_tree_node_init_with_children():
    """Testa inicialização com filhos"""
    child = ProtocolTreeNode("body")
    node = ProtocolTreeNode("message", children=[child])
    assert len(node.children) == 1
    assert node.children[0] == child


def test_protocol_tree_node_init_with_data():
    """Testa inicialização com dados"""
    data = b"test data"
    node = ProtocolTreeNode("message", data=data)
    assert node.data == data


def test_protocol_tree_node_get_attribute():
    """Testa obtenção de atributo"""
    attrs = {"from": "test@whatsapp.net"}
    node = ProtocolTreeNode("message", attrs)
    assert node.get_attribute("from") == "test@whatsapp.net"
    assert node.get_attribute("nonexistent") is None


def test_protocol_tree_node_get_child_by_index():
    """Testa obtenção de filho por índice"""
    child1 = ProtocolTreeNode("body")
    child2 = ProtocolTreeNode("header")
    node = ProtocolTreeNode("message", children=[child1, child2])
    
    assert node.get_child(0) == child1
    assert node.get_child(1) == child2
    assert node.get_child(2) is None
    assert node.get_child(-1) is None


def test_protocol_tree_node_get_child_by_tag():
    """Testa obtenção de filho por tag"""
    child1 = ProtocolTreeNode("body")
    child2 = ProtocolTreeNode("header")
    node = ProtocolTreeNode("message", children=[child1, child2])
    
    assert node.get_child("body") == child1
    assert node.get_child("header") == child2
    assert node.get_child("nonexistent") is None


def test_protocol_tree_node_has_children():
    """Testa verificação de filhos"""
    node1 = ProtocolTreeNode("message")
    assert not node1.has_children()
    
    child = ProtocolTreeNode("body")
    node2 = ProtocolTreeNode("message", children=[child])
    assert node2.has_children()


@pytest.mark.asyncio
async def test_protocol_tree_node_to_bytes():
    """Testa serialização para bytes"""
    node = ProtocolTreeNode("message")
    result = await node.to_bytes()
    assert isinstance(result, bytes)


@pytest.mark.asyncio
async def test_protocol_tree_node_from_bytes():
    """Testa deserialização de bytes"""
    data = b"test"
    node = await ProtocolTreeNode.from_bytes(data)
    assert isinstance(node, ProtocolTreeNode)

