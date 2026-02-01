"""
Protocol Structures - Estruturas simples para protocolo WhatsApp.

Estrutura moderna e simples, sem dependências complexas.
"""

import binascii
from dataclasses import dataclass, field
import random
from typing import Optional, Dict, List, Any, Union

from loguru import logger





@dataclass
class ProtocolNode:
    """
    Node de protocolo simples e moderno.
    Substitui ProtocolTreeNode com estrutura mais limpa.
    """
    WEB_MESSAGE_ID_PREFIX = "3EB0"

    _STR_MAX_LEN_DATA = 500
    _STR_INDENT = '  '
    __ID_GEN = 0
    ID_TYPE_ANDROID = 0
    ID_TYPE_IOS = 1
    _truncate_str_data = True

    tag: str
    attributes: Dict[str, str] = field(default_factory=dict)
    children: List['ProtocolNode'] = field(default_factory=list)
    data: Optional[bytes] = None

   
    def __str__(self):
        try:
            out = "<%s" % self.tag
            attrs = " ".join((map(lambda item: "%s=\"%s\"" % item, self.attributes.items())))
            children = "\n".join(map(str, self.children))
            data = self.data or b""
            len_data = len(data)

            if attrs:
                out = "%s %s" % (out, attrs)

            if children or data:
                out = "%s>" % out
                if children:
                    out = "%s\n%s%s" % (out, self._STR_INDENT, children.replace('\n', '\n' + self._STR_INDENT))
                if len_data:
                    if self._truncate_str_data and len_data > self._STR_MAX_LEN_DATA:
                        data = data[:self._STR_MAX_LEN_DATA]
                        postfix = "...[truncated %s bytes]" % (len_data - self._STR_MAX_LEN_DATA)
                    else:
                        postfix = ""
                    data = "0x%s" % binascii.hexlify(data).decode()
                    out = "%s\n%s%s%s" % (out, self._STR_INDENT, data, postfix)

                out = "%s\n</%s>" % (out, self.tag)
            else:
                out = "%s />" % out

            return out

        except Exception as e:
            logger.error(f"Error in ProtocolNode.__str__: {e}")
            return f"<{self.tag} />"


    @classmethod
    def generate_key(cls) -> str:
        import secrets
        return secrets.token_hex(8).upper()


    @staticmethod
    def _generateId(short: bool = False, type: int = ID_TYPE_ANDROID) -> str:
        """
        Gera ID único seguindo padrão do ProtocolEntity do zowsuplib.
        
        Baseado em ProtocolEntity._generateId() do zowsuplib.
        
        Args:
            short: Não usado (mantido para compatibilidade)
            type: Tipo de ID (ID_TYPE_ANDROID ou ID_TYPE_IOS)
        
        Returns:
            String com ID gerado
        """
        if type == ProtocolNode.ID_TYPE_IOS:
            alp = '0123456789ABCDEF0123456789ABCDEF'
            id = ''.join(random.sample(alp, 18))
            id = "3A" + id
        elif type == ProtocolNode.ID_TYPE_ANDROID:
            alp = '0123456789ABCDEF0123456789ABCDEF'
            id = ''.join(random.sample(alp, 32))
        else:
            # Fallback para Android se tipo inválido
            alp = '0123456789ABCDEF0123456789ABCDEF'
            id = ''.join(random.sample(alp, 32))
        
        return id
    

    
    def to_dict(self) -> Dict[str, Any]:
        """Converte node para dicionário."""
        return {
            "tag": self.tag,
            "attributes": self.attributes,
            "children": [child.to_dict() for child in self.children],
            "data": self.data.hex() if self.data else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProtocolNode':
        """Cria node a partir de dicionário."""
        children = [cls.from_dict(c) for c in data.get("children", [])]
        node_data = bytes.fromhex(data["data"]) if data.get("data") else None
        return cls(
            tag=data["tag"],
            attributes=data.get("attributes", {}),
            children=children,
            data=node_data,
        )


    def getData(self):
        return self.data

    def setData(self, data):
        self.data = data


    @staticmethod
    def tagEquals(node,string):
        return node is not None and node.tag is not None and node.tag == string


    @classmethod
    def require(node,string):
        if not ProtocolNode.tagEquals(node,string):
            raise Exception("failed require. string: "+string);


    def __getitem__(self, key):
        return self.getAttributeValue(key)

    def __setitem__(self, key, val):
        self.setAttribute(key, val)

    def __delitem__(self, key):
        self.removeAttribute(key)


    def getChild(self,identifier):

        if type(identifier) == int:
            if len(self.children) > identifier:
                return self.children[identifier]
            else:
                return None

        for c in self.children:
            if identifier == c.tag:
                return c

        return None


    def get_child(self, identifier):
        return self.getChild(identifier)

    def hasChildren(self):
        return len(self.children) > 0

    def has_children(self):
        return self.hasChildren()

    def addChild(self, childNode):
        self.children.append(childNode)

    def add_child(self, childNode):
        self.addChild(childNode)

    def addChildren(self, children):
        for c in children:
            self.addChild(c)

    def add_children(self, childNode):
        self.addChildren(childNode)

    def getAttributeValue(self,string):
        try:
            return self.attributes[string]
        except KeyError:
            return None

    def get_attribute(self, key):
        return self.getAttributeValue(key)

    def get_attribute_value(self, key):
        return self.getAttributeValue(key)

    def removeAttribute(self, key):
        if key in self.attributes:
            del self.attributes[key]


    def remove_attribute(self, key):
        self.removeAttribute(key)

    def setAttribute(self, key, value):
        self.attributes[key] = value

    def set_attribute(self, key, value):
        self.setAttribute(key, value)

    def getAllChildren(self,tag = None):
        ret = []
        if tag is None:
            return self.children

        for c in self.children:
            if tag == c.tag:
                ret.append(c)

        return ret



    def get_all_children(self, tag = None):
        return self.getAllChildren(tag)

