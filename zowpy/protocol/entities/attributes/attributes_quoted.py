from typing import Optional


class QuotedAttributes(object):

    def __init__(self,reply_message_id, participant, text:Optional[str]=None):
        self._text = text or ""
        self._reply_message_id = reply_message_id
        self._participant =participant

    def __str__(self):
        attrs = []
        if self._text is not None:
            attrs.append(("text", self.text))
        if self._reply_message_id is not None:
            attrs.append(("reply_message_id", self.reply_message_id))
        if self._participant is not None:
            attrs.append(("participant", self.participant))   

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        self._text = value

    @property
    def reply_message_id(self):
        return self._reply_message_id

    @reply_message_id.setter
    def reply_message_id(self, value):
        self._reply_message_id = value

    @property
    def participant(self):
        return self._participant

    @participant.setter
    def participant(self, value):
        self._participant = value

