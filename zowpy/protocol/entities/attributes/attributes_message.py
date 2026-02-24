"""
MessageAttributes - Atributos de mensagem que agrupa todos os tipos.

Baseado em zowsuplib/yowsup/layers/protocol_messages/protocolentities/attributes/attributes_message.py
"""

from typing import Any, Optional

from .attributes_image import ImageAttributes
from .attributes_video import VideoAttributes
from .attributes_audio import AudioAttributes
from .attributes_document import DocumentAttributes
from .attributes_sticker import StickerAttributes
import os

class MessageAttributes:
    """
    Atributos de mensagem que agrupa todos os tipos de atributos.
    
    Uma mensagem pode ter apenas um tipo de atributo por vez (image, video, audio, etc.).
    """
    
    def __init__(
        self,
        conversation: Optional[str] = None,
        image: Optional[ImageAttributes] = None,
        contact: Optional[Any] = None,  # ContactAttributes - será implementado se necessário
        location: Optional[Any] = None,  # LocationAttributes - será implementado se necessário
        extended_text: Optional[Any] = None,  # ExtendedTextAttributes - será implementado se necessário
        document: Optional[DocumentAttributes] = None,
        audio: Optional[AudioAttributes] = None,
        video: Optional[VideoAttributes] = None,
        sticker: Optional[StickerAttributes] = None,
        template: Optional[Any] = None,  # TemplateAttributes - será implementado se necessário
        buttons: Optional[Any] = None,
        buttons_response: Optional[Any] = None,
        list: Optional[Any] = None,
        list_response: Optional[Any] = None,
        poll_creation: Optional[Any] = None,
        poll_update: Optional[Any] = None,
        product: Optional[Any] = None,
        interactive: Optional[Any] = None,
        reaction: Optional[Any] = None,
        sender_key_distribution_message: Optional[Any] = None,
        protocol: Optional[Any] = None,
        fromMe: bool = False,
        to: Optional[str] = None,
        message_secret: Optional[bytes] = None
    ):
        """
        Inicializa MessageAttributes.
        
        Args:
            conversation: Texto de conversa (para mensagens de texto simples)
            image: Atributos de imagem
            contact: Atributos de contato
            location: Atributos de localização
            extended_text: Atributos de texto estendido
            document: Atributos de documento
            audio: Atributos de áudio
            video: Atributos de vídeo
            sticker: Atributos de sticker
            template: Atributos de template
            buttons: Atributos de botões
            buttons_response: Atributos de resposta de botões
            list: Atributos de lista
            list_response: Atributos de resposta de lista
            poll_creation: Atributos de criação de enquete
            poll_update: Atributos de atualização de enquete
            product: Atributos de produto
            interactive: Atributos interativos
            reaction: Atributos de reação
            sender_key_distribution_message: Atributos de distribuição de chave de remetente
            protocol: Atributos de protocolo
            fromMe: Se a mensagem foi enviada por mim
            to: JID do destinatário
        """
        self._conversation = conversation
        self._image = image
        self._contact = contact
        self._location = location
        self._extended_text = extended_text
        self._document = document
        self._audio = audio
        self._video = video
        self._sticker = sticker
        self._template = template
        self._buttons = buttons
        self._buttons_response = buttons_response
        self._poll_creation = poll_creation
        self._poll_update = poll_update
        self._list = list
        self._list_response = list_response
        self._product = product
        self._interactive = interactive
        self._reaction = reaction
        self._sender_key_distribution_message = sender_key_distribution_message
        self._protocol = protocol
        self._fromMe = fromMe
        self._to = to
        self._message_secret = message_secret if isinstance(message_secret, bytes) else  os.urandom(32)
    def __str__(self):
        attrs = []
        if self.conversation is not None:
            attrs.append(("conversation", self.conversation))
        if self.image is not None:
            attrs.append(("image", self.image))
        if self.contact is not None:
            attrs.append(("contact", self.contact))
        if self.location is not None:
            attrs.append(("location", self.location))
        if self.extended_text is not None:
            attrs.append(("extended_text", self.extended_text))
        if self.document is not None:
            attrs.append(("document", self.document))
        if self.audio is not None:
            attrs.append(("audio", self.audio))
        if self.video is not None:
            attrs.append(("video", self.video))
        if self.sticker is not None:
            attrs.append(("sticker", self.sticker))
        if self.template is not None:
            attrs.append(("template", self.template))
        if self.buttons is not None:
            attrs.append(("buttons", self.buttons))
        if self.buttons_response is not None:
            attrs.append(("buttons_response", self.buttons_response))
        if self.poll_creation is not None:
            attrs.append(("poll_creation", self.poll_creation))
        if self.poll_update is not None:
            attrs.append(("poll_update", self.poll_update))
        if self.list is not None:
            attrs.append(("list", self.list))
        if self.list_response is not None:
            attrs.append(("list_response", self.list_response))
        if self.product is not None:
            attrs.append(("product", self.product))
        if self.interactive is not None:
            attrs.append(("interactive", self.interactive))
        if self.reaction is not None:
            attrs.append(("reaction", self.reaction))
        if self.sender_key_distribution_message is not None:
            attrs.append(("sender_key_distribution_message", self.sender_key_distribution_message))
        if self.protocol is not None:
            attrs.append(("protocol", self.protocol))
        if self.fromMe:
            attrs.append(("fromMe", self.fromMe))
            attrs.append(("to", self.to))

        if self._message_secret:
            attrs.append(("message_secret", self._message_secret))
        
        return "[%s]" % " ".join((map(lambda item: "%s=%s" % item, attrs)))
    
    @property
    def fromMe(self) -> bool:
        """Se a mensagem foi enviada por mim."""
        return self._fromMe
    
    @fromMe.setter
    def fromMe(self, value: bool):
        """Define se a mensagem foi enviada por mim."""
        self._fromMe = value
    
    @property
    def to(self) -> Optional[str]:
        """JID do destinatário."""
        return self._to
    
    @to.setter
    def to(self, value: Optional[str]):
        """Define JID do destinatário."""
        self._to = value
    
    @property
    def conversation(self) -> Optional[str]:
        """Texto de conversa."""
        return self._conversation
    
    @conversation.setter
    def conversation(self, value: Optional[str]):
        """Define texto de conversa."""
        self._conversation = value
    
    @property
    def image(self) -> Optional[ImageAttributes]:
        """Atributos de imagem."""
        return self._image
    
    @image.setter
    def image(self, value: Optional[ImageAttributes]):
        """Define atributos de imagem."""
        self._image = value
    
    @property
    def contact(self):
        """Atributos de contato."""
        return self._contact
    
    @contact.setter
    def contact(self, value):
        """Define atributos de contato."""
        self._contact = value
    
    @property
    def location(self):
        """Atributos de localização."""
        return self._location
    
    @location.setter
    def location(self, value):
        """Define atributos de localização."""
        self._location = value
    
    @property
    def extended_text(self):
        """Atributos de texto estendido."""
        return self._extended_text
    
    @extended_text.setter
    def extended_text(self, value):
        """Define atributos de texto estendido."""
        self._extended_text = value
    
    @property
    def document(self) -> Optional[DocumentAttributes]:
        """Atributos de documento."""
        return self._document
    
    @document.setter
    def document(self, value: Optional[DocumentAttributes]):
        """Define atributos de documento."""
        self._document = value
    
    @property
    def audio(self) -> Optional[AudioAttributes]:
        """Atributos de áudio."""
        return self._audio
    
    @audio.setter
    def audio(self, value: Optional[AudioAttributes]):
        """Define atributos de áudio."""
        self._audio = value
    
    @property
    def video(self) -> Optional[VideoAttributes]:
        """Atributos de vídeo."""
        return self._video
    
    @video.setter
    def video(self, value: Optional[VideoAttributes]):
        """Define atributos de vídeo."""
        self._video = value
    
    @property
    def sticker(self) -> Optional[StickerAttributes]:
        """Atributos de sticker."""
        return self._sticker
    
    @sticker.setter
    def sticker(self, value: Optional[StickerAttributes]):
        """Define atributos de sticker."""
        self._sticker = value
    
    @property
    def template(self):
        """Atributos de template."""
        return self._template
    
    @template.setter
    def template(self, value):
        """Define atributos de template."""
        self._template = value
    
    @property
    def buttons(self):
        """Atributos de botões."""
        return self._buttons
    
    @buttons.setter
    def buttons(self, value):
        """Define atributos de botões."""
        self._buttons = value
    
    @property
    def buttons_response(self):
        """Atributos de resposta de botões."""
        return self._buttons_response
    
    @buttons_response.setter
    def buttons_response(self, value):
        """Define atributos de resposta de botões."""
        self._buttons_response = value
    
    @property
    def poll_creation(self):
        """Atributos de criação de enquete."""
        return self._poll_creation
    
    @poll_creation.setter
    def poll_creation(self, value):
        """Define atributos de criação de enquete."""
        self._poll_creation = value
    
    @property
    def poll_update(self):
        """Atributos de atualização de enquete."""
        return self._poll_update
    
    @poll_update.setter
    def poll_update(self, value):
        """Define atributos de atualização de enquete."""
        self._poll_update = value
    
    @property
    def list(self):
        """Atributos de lista."""
        return self._list
    
    @list.setter
    def list(self, value):
        """Define atributos de lista."""
        self._list = value
    
    @property
    def list_response(self):
        """Atributos de resposta de lista."""
        return self._list_response
    
    @list_response.setter
    def list_response(self, value):
        """Define atributos de resposta de lista."""
        self._list_response = value
    
    @property
    def product(self):
        """Atributos de produto."""
        return self._product
    
    @product.setter
    def product(self, value):
        """Define atributos de produto."""
        self._product = value
    
    @property
    def interactive(self):
        """Atributos interativos."""
        return self._interactive
    
    @interactive.setter
    def interactive(self, value):
        """Define atributos interativos."""
        self._interactive = value
    
    @property
    def reaction(self):
        """Atributos de reação."""
        return self._reaction
    
    @reaction.setter
    def reaction(self, value):
        """Define atributos de reação."""
        self._reaction = value
    
    @property
    def sender_key_distribution_message(self):
        """Atributos de distribuição de chave de remetente."""
        return self._sender_key_distribution_message
    
    @sender_key_distribution_message.setter
    def sender_key_distribution_message(self, value):
        """Define atributos de distribuição de chave de remetente."""
        self._sender_key_distribution_message = value
    
    @property
    def protocol(self):
        """Atributos de protocolo."""
        return self._protocol
    
    @protocol.setter
    def protocol(self, value):
        """Define atributos de protocolo."""
        self._protocol = value

    @property
    def message_secret(self) -> Optional[bytes]:
        """Chave de segredo da mensagem."""
        return self._message_secret
    
    @message_secret.setter
    def message_secret(self, value: Optional[bytes]):
        """Define chave de segredo da mensagem."""
        self._message_secret = value
