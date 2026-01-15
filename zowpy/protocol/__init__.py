"""WhatsApp protocol handlers."""

from .messages import AsyncMessageHandler
from .iq import AsyncIQHandler
from .presence import AsyncPresenceHandler
from .receipts import AsyncReceiptHandler
from .groups import AsyncGroupsHandler
from .media import AsyncMediaHandler
from .contacts import AsyncContactsHandler
from .notifications import AsyncNotificationsHandler
from .profiles import AsyncProfilesHandler
from .privacy import AsyncPrivacyHandler
from .chatstate import AsyncChatstateHandler
from .calls import AsyncCallsHandler
from .ib import AsyncIBHandler
from .devices import AsyncDevicesHandler
from .acks import AsyncAcksHandler
from .auth import AsyncAuthHandler
from .coder import AsyncCoder, AsyncEncoder, AsyncDecoder
from .structs import ProtocolNode
from .historysync import HistorySync

# Alias para compatibilidade com código antigo
ProtocolTreeNode = ProtocolNode

__all__ = [
    "AsyncMessageHandler",
    "AsyncIQHandler",
    "AsyncPresenceHandler",
    "AsyncReceiptHandler",
    "AsyncGroupsHandler",
    "AsyncMediaHandler",
    "AsyncContactsHandler",
    "AsyncNotificationsHandler",
    "AsyncProfilesHandler",
    "AsyncPrivacyHandler",
    "AsyncChatstateHandler",
    "AsyncCallsHandler",
    "AsyncIBHandler",
    "AsyncDevicesHandler",
    "AsyncAcksHandler",
    "AsyncAuthHandler",
    "AsyncCoder",
    "AsyncEncoder",
    "AsyncDecoder",
    "ProtocolNode",
    "ProtocolTreeNode",  # Alias para compatibilidade
    "HistorySync",
]
