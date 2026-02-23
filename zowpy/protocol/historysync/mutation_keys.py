

from zowpy.utils.tools import WATools


class MutationKeys(object):
    
    def __init__(self,indexKey,encKey,macKey,snapShotMacKey,patchMacKey):
        self.indexKey = indexKey
        self.encKey = encKey
        self.macKey = macKey
        self.snapShotMacKey = snapShotMacKey
        self.patchMacKey = patchMacKey

    @staticmethod
    def createFromKey(key):
        """
        Cria MutationKeys a partir de uma chave.
        :param key: Chave
        :return: MutationKeys
        """
        #从一个key生成5个key，保证sync流程用到的key
        ba = WATools.extract_and_expand(
            key = key,
            info = "WhatsApp Mutation Keys".encode(),
            output_length=160
        )

        return MutationKeys(
            indexKey = ba[0:32],
            encKey = ba[32:64],
            macKey = ba[64:96],
            snapShotMacKey= ba[96:128],        
            patchMacKey=  ba[128:]
        )





        


