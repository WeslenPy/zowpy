

from zowpy.protocol.structs import ProtocolNode


class HashState:

    def __init__(self, type,version = 0,hash=bytes(128),indexValueMap={}):
        self.type = type
        self.version = version
        self.hash = hash
        self.indexValueMap = indexValueMap
    
    def copy(self):

        return HashState(
            self.type,
            self.version,
            self.hash,
            self.indexValueMap
        )
    
    def equals(self,another):
        if len(self.indexValueMap)!=len(another.indexValueMap):
            return False
        
        for key,value in self.indexValueMap:
            if not (key in another.indexValueMap or another.indexValueMap[key]==value):
                return False

        return True        


    def hash(self):
        return self.hash     

    def toNode(self):
        
        node = ProtocolNode("collection",attributes={
            "name":self.type,
            "version":self.version            
        },children=[])

        return node
    


    


