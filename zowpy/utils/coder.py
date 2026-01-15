import math
import binascii
import sys
import zlib

from zowpy.protocol.nodes import ProtocolTreeNode

from ..protocol.structs import ProtocolNode


class ReadDecoder:
    def __init__(self, tokenDictionary):
        self.tokenDictionary = tokenDictionary

    def getProtocolNode(self, data):

        if type(data) is list:
            data = bytearray(data)
                
        if data[0] & self.tokenDictionary.FLAG_DEFLATE != 0:
            data = bytearray(b'\x00' + zlib.decompress(bytes(data[1:])))
        if data[0] & self.tokenDictionary.FLAG_SEGMENTED != 0:
            raise ValueError("server to client stanza fragmentation not supported")
        return self.nextTreeInternal(data[1:])

    def getToken(self, index, data):
        token = self.tokenDictionary.getToken(index)
        if not token:
            index = self.readInt8(data)
            token = self.tokenDictionary.getToken(index, True)
            if not token:
                raise ValueError("Invalid token %s" % token)

        return token

    def getTokenDouble(self, n, n2):
        pos = n2 + n * 256
        token = self.tokenDictionary.getToken(pos, True)
        if not token:
            raise ValueError("Invalid token %s" % pos)

        return token

    def streamStart(self, data):
        self.streamStarted = True
        tag = data.pop(0)
        size = self.readListSize(tag, data)
        tag = data.pop(0)

        if tag != 1:
            if tag == 236:
                tag = data.pop(0) + 237
            token = self.getToken(tag, data)#self.tokenDictionary.getToken(tag)
            raise Exception("expecting STREAM_START in streamStart, instead got token: %s" % token)
        attribCount = (size - 2 + size % 2) / 2
        self.readAttributes(attribCount, data)

    def readNibble(self, data):
        _byte = self.readInt8(data)
        ignoreLastNibble = bool(_byte & 0x80)
        size = (_byte & 0x7f)
        nrOfNibbles = size * 2 - int(ignoreLastNibble)
        dataArr = self.readArray(size, data)
        string = ''
        for i in range(0, nrOfNibbles):
            _byte = dataArr[int(math.floor(i/2))]
            _shift = 4 * (1 - i % 2)
            dec = (_byte & (15 << _shift)) >> _shift

            if dec in (0,1,2,3,4,5,6,7,8,9):
                string += str(dec)
            elif dec in (10, 11):
                string += chr(dec - 10 + 45)
            else:
                raise Exception("Bad nibble %s" % dec)
        return string

    def readPacked8(self, n, data):
        size = self.readInt8(data)
        remove = 0
        if (size & 0x80) != 0 and n == 251:
            remove = 1
        size = size & 0x7F
        text = bytearray(self.readArray(size, data))
        hexData = binascii.hexlify(str(text) if sys.version_info < (2,7) else text).upper()
        dataSize = len(hexData)
        out = []
        if remove == 0:
            for i in range(0, dataSize):
                char = chr(hexData[i]) if type(hexData[i]) is int else hexData[i] #python2/3 compat
                val = ord(binascii.unhexlify("0%s" % char))
                if i == (dataSize - 1) and val > 11 and n != 251: continue
                out.append(self.unpackByte(n, val))
        else:
            out =  map(ord, list(hexData[0: -remove])) if sys.version_info < (3,0) else list(hexData[0: -remove])

        return out

    def unpackByte(self, n, n2):
        if n == 251:
            return self.unpackHex(n2)
        if n == 255:
            return self.unpackNibble(n2)
        raise ValueError("bad packed type %s" % n)

    def unpackHex(self, n):
        if n in range(0, 10):
            return n + 48
        if n in range(10, 16):
            return 65 + (n - 10)

        raise ValueError("bad hex %s" % n)

    def unpackNibble(self, n):
        if n in range(0, 10):
            return n + 48
        if n in (10, 11):
            return 45 + (n - 10)
        raise ValueError("bad nibble %s" % n)


    def readHeader(self, data, offset = 0):
        ret = 0
        if len(data) >= (3 + offset):
            b0 = data[offset]
            b1 = data[offset + 1]
            b2 = data[offset + 2]
            ret = b0 + (b1 << 16) + (b2 << 8)

        return ret

    def readInt8(self, data):
        if len(data) == 0:
            raise IndexError("Cannot read from empty bytearray")
        return data.pop(0)

    def readInt16(self, data):
        intTop = data.pop(0)
        intBot = data.pop(0)
        value = (intTop << 8) + intBot
        if value is not None:
            return value
        else:
            return ""

    def readInt20(self, data):
         int1 = data.pop(0)
         int2 = data.pop(0)
         int3 = data.pop(0)
         return ((int1 & 0xF) << 16) | (int2 << 8) | int3

    def readInt24(self, data):
        int1 = data.pop(0)
        int2 = data.pop(0)
        int3 = data.pop(0)
        value = (int1 << 16) + (int2 << 8) + (int3 << 0)
        return value

    def readInt31(self, data):
        data.pop(0)
        int1 = data.pop(0)
        int2 = data.pop(0)
        int3 = data.pop(0)
        return (int1 << 24) | (int1 << 16) | int2 << 8 | int3

    def readListSize(self,token, data):
        size = 0
        if token == 0:
            size = 0
        else:
            if token == 248:
                size = self.readInt8(data)
            else:
                if token == 249:
                    size = self.readInt16(data)
                else:
                    raise Exception("invalid list size in readListSize: token " + str(token))
        return size

    def readAttributes(self, attribCount, data):
        attribs = {}
        for i in range(0, int(attribCount)):
            key = self.readString(self.readInt8(data), data)
            value = self.readString(self.readInt8(data), data)
            attribs[key]=value
        return attribs

    def readString(self,token, data):
        if token == -1:
            raise Exception("-1 token in readString")

        if 2 < token < 236:
            return self.getToken(token, data)

        if token == 0:
            return None

        if token in (236, 237, 238, 239):
            return self.getTokenDouble(token - 236, self.readInt8(data))

        if token == 247:
            xx = self.readInt8(data)
            device_no = self.readInt8(data)
            user = self.readString(data.pop(0),data)
            if xx==1:
                #xx=1时是lid
                jid = "{}:{}@lid".format(user,device_no)
            else:
                #其余情况，暂时按照普通id处置
                jid = "{}.{}:{}@s.whatsapp.net".format(user,xx,device_no)
            return jid

        if token == 250:
            user = self.readString(data.pop(0), data)
            server = self.readString(data.pop(0), data)
            if user is not None and server is not None:
                return user + "@" + server
            if server is not None:
                return server
            raise Exception("readString couldn't reconstruct jid")

        if token in (251, 255):
            return "".join(map(chr, self.readPacked8(token, data)))

        if token == 252:
            size8 = self.readInt8(data)
            buf8 = self.readArray(size8, data)
            return "".join(map(chr, buf8))

        if token == 253:
            size20 = self.readInt20(data)
            buf20 = self.readArray(size20, data)
            return "".join(map(chr, buf20))

        if token == 254:
            size31 = self.readInt31(data)
            buf31 = self.readArray(size31, data)
            return "".join(map(chr, buf31))


        raise Exception("readString couldn't match token "+str(token))

    def readArray(self, length, data):
        if len(data) < length:
            raise IndexError(f"Cannot read {length} bytes from bytearray of length {len(data)}")
        out = list(data[:length])
        del data[:length]
        return out

    def nextTreeInternal(self, data):
        size = self.readListSize(self.readInt8(data), data)
        token = self.readInt8(data)
        if token == 1:
            token = self.readInt8(data)

        if token == 2:
            return None

        tag = self.readString(token, data)

        if size == 0 or tag is None:
            raise ValueError("nextTree sees 0 list or null tag")

        attribCount = (size - 2 + size % 2)/2
        attribs = self.readAttributes(attribCount, data)
        if size % 2 ==1:
            return ProtocolNode(tag=tag, attributes=attribs)

        read2 = self.readInt8(data)

        nodeData = None
        nodeChildren = None
        if self.isListTag(read2):
            nodeChildren = self.readList(read2, data)
        elif read2 == 252:
            size = self.readInt8(data)
            nodeData = bytes(self.readArray(size, data))
        elif read2 == 253:
            size = self.readInt20(data)
            nodeData = bytes(self.readArray(size, data))
        elif read2 == 254:
            size = self.readInt31(data)
            nodeData = bytes(self.readArray(size, data))
        elif read2 in (255, 251):
            nodeData = self.readPacked8(read2, data)
        else:
            nodeData = self.readString(read2, data)
        return ProtocolNode(tag=tag, attributes=attribs, children=nodeChildren, data=nodeData)

    def readList(self,token, data):
        size = self.readListSize(token, data)
        listx = []
        for i in range(0,size):
            listx.append(self.nextTreeInternal(data))

        return listx;

    def isListTag(self, b):
        return b in (248, 0, 249)



class WriteEncoder:

    def __init__(self, tokenDictionary):
        self.tokenDictionary = tokenDictionary

    def protocolNodeToBytes(self, node):
        """Codifica ProtocolNode para bytes."""
        outBytes = [0] # flags
        self.writeInternal(node, outBytes)                                
        return outBytes
    
    # Alias para compatibilidade
    def protocolTreeNodeToBytes(self, node):
        """Alias para compatibilidade com código antigo."""
        return self.protocolNodeToBytes(node)

    def writeInternal(self, node:ProtocolTreeNode, data):
        # Support both hasChildren() and has_children() for compatibility
        has_children = node.has_children()
        
        x = 1 + \
        (0 if node.attributes is None else len(node.attributes) * 2) + \
        (0 if not has_children else 1) + \
        (0 if node.data is None else 1)

        self.writeListStart(x, data)    

        self.writeString(node.tag, data)
        self.writeAttributes(node.attributes, data)

        if node.data is not None:            
            self.writeBytes(node.data, data)

        if has_children:

            self.writeListStart(len(node.children), data);    
            for c in node.children:
                self.writeInternal(c, data)         

    def writeAttributes(self, attributes, data):
        if attributes is not None:
            for key, value in attributes.items():
                self.writeString(key, data)
                self.writeString(value, data, True)


    def writeBytes(self, bytes_, data, packed = False):
        bytes__ = []
        for b in bytes_:
            if type(b) is int:
                bytes__.append(b)
            else:
                bytes__.append(ord(b))


        size = len(bytes__)
        toWrite = bytes__
        if size >= 0x100000:
            data.append(254)
            self.writeInt31(size, data)
        elif size >= 0x100:
            data.append(253)
            self.writeInt20(size, data)
        else:
            r = None
            if packed:
                if size < 128:
                    r = self.tryPackAndWriteHeader(255, bytes__, data)
                    if r is None:
                        r = self.tryPackAndWriteHeader(251, bytes__, data)

            if r is None:
                data.append(252)
                self.writeInt8(size, data)
            else:
                toWrite = r

        data.extend(toWrite)

    def writeInt8(self, v, data):
        data.append(v & 0xFF)


    def writeInt16(self, v, data):
        data.append((v & 0xFF00) >> 8)
        data.append((v & 0xFF) >> 0)

    def writeInt20(self, v, data):
        data.append((0xF0000 & v) >> 16)
        data.append((0xFF00 & v) >> 8)
        data.append((v & 0xFF) >> 0)

    def writeInt24(self, v, data):
        data.append((v & 0xFF0000) >> 16)
        data.append((v & 0xFF00) >> 8)
        data.append((v & 0xFF) >> 0)

    def writeInt31(self, v, data):
        data.append((0x7F000000 & v) >> 24)
        data.append((0xFF0000 & v) >> 16)
        data.append((0xFF00 & v) >> 8)
        data.append((v & 0xFF) >> 0)

    def writeInt32(self, v, data):
        data.append((0xFF000000 & v) >> 24)
        data.append((0xFF0000 & v) >> 16)
        data.append((0xFF00 & v) >> 8)
        data.append((v & 0xFF) >> 0)

    def writeListStart(self, i, data):
        if i == 0:
            data.append(0)
        elif i < 256:
            data.append(248)
            self.writeInt8(i, data)
        else:
            data.append(249)
            self.writeInt16(i, data)

    def writeToken(self, token, data):
        if token <= 255 and token >=0:
            data.append(token)
        else:
            raise ValueError("Invalid token: %s" % token)


    def writeString(self, tag, data, packed = False): 

        tok = self.tokenDictionary.getIndex(tag)

                
        if tok:
            index, secondary = tok
            if not secondary:

                self.writeToken(index, data)
            else:
                quotient = index // 256
                if quotient == 0:
                    double_byte_token = 236
                elif quotient == 1:
                    double_byte_token = 237
                elif quotient == 2:
                    double_byte_token = 238
                elif quotient == 3:
                    double_byte_token = 239
                else:
                    raise ValueError("Double byte dictionary token out of range")

                self.writeToken(double_byte_token, data)
                self.writeToken(index % 256, data)
        else:            
            at = '@'.encode() if type(tag) == bytes else '@'
            try:                
                atIndex = tag.index(at)
                if atIndex < 1:
                    raise ValueError("atIndex < 1")
                else:
                    server = tag[atIndex+1:]
                    user = tag[0:atIndex]          
                    self.writeJid(user, server, data)
            except ValueError:
                self.writeBytes(self.encodeString(tag), data, packed)
    

    def encodeString(self, string):
        res = []

        if type(string) == bytes:
            for char in string:
                res.append(char)
        else:
            for char in string:
                res.append(ord(char))
        return res

    def writeJid(self, user, server, data):
        if user.find(":") != -1:
            if server=="lid":
                device_no = user.split("@")[0].split(":")[1]
                data.append(247)
                data.append(1)
                data.append(int(device_no))                                
                user = user.split(":")[0]                                   
                self.writeString(user,data,True)            
            else:
                device_no = user.split("@")[0].split(":")[1]
                data.append(247)
                data.append(0)
                data.append(int(device_no))                
                user = user.split(".")[0]
                self.writeString(user,data,True)
        else:
            if server=="lid":                
                data.append(247)
                data.append(1)
                data.append(0)                     
                user = user.split("@")[0]
                self.writeString(user,data,True)
            else:
                data.append(250)
                if user is not None:
                    self.writeString(user, data,True)
                else:
                    self.writeToken(0, data)
                self.writeString(server, data)

            
    def tryPackAndWriteHeader(self, v, headerData, data):
        size = len(headerData)
        if size >= 128:
            return None
        arr = [0] * int((size + 1) / 2)
        for i in range(0, size):
            packByte = self.packByte(v, headerData[i])
            if packByte == -1:
                arr = []
                break
            n2 = int(i / 2)
            arr[n2] |= (packByte << 4 * (1 - i % 2))

        if len(arr) > 0:
            if size % 2 == 1:
                arr[-1] |= 15 #0xF
            data.append(v)
            self.writeInt8(size %2 << 7 | len(arr), data)
            return arr
        return None
    
    def packByte(self, v, n2):
        if v == 251:
            return self.packHex(n2)
        if v == 255:
            return self.packNibble(n2)
        return -1

    def packHex(self, n):
        if n in range(48, 58):
            return n - 48
        if n in range(65, 71):
            return 10 + (n - 65)
        return -1

    def packNibble(self, n):
        if n in (45, 46):
            return 10 + (n - 45)

        if n in range(48, 58):
            return n - 48

        return -1


