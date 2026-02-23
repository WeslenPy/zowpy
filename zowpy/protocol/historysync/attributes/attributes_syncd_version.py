from ....proto import protocol_pb2




class SyncdVersionAttribute(object):
    def __init__(self, version):
        self.version = version
    

    def encode(self):
        pb_obj = protocol_pb2.SyncdVersion()

        if self.version is not None:
            pb_obj.version = self.version

        return pb_obj

    @staticmethod
    def decodeFrom(pb_obj):
        version = pb_obj.version if pb_obj.HasField("version") else None

        return SyncdVersionAttribute(
            version = version
        )



