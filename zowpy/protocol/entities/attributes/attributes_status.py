from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from zowpy.proto import e2e_pb2
import time

class StatusAttributes(object):
    def __init__(self,        
        media_type:str,
        text:Optional[str]=None,
        url:Optional[str]=None,
        text_color:Optional[str]= None,
        background_color:Optional[str] = None,
        font:Optional[int] = None,
        participants:Optional[list[str]] = None,
        caption:Optional[str] = None,
        preview_type:Optional[int] = None,):

        self.media_type = media_type
        self.text = text
        self.url = url
        self.text_color = text_color
        self.background_color = background_color
        self.font = font
        self.participants = participants
        self.caption = caption
        self.preview_type = preview_type




