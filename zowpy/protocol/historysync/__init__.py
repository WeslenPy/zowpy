"""
Protocol History Sync - Sincronização de histórico do WhatsApp.

Implementa os protocolos de sincronização de histórico para multi-device.
"""

from .history_sync import HistorySync
from .attributes import (
    HistorySyncAttribute,
    HistorySyncNotificationAttribute,
    ConversationAttribute,
    WebMessageInfoAttribute,
    MessageKeyAttribute,
    PushnameAttribute,
    PastParticipantAttribute,
    PastParticipantsAttribute,
    AppStateSyncKeyAttribute,
    AppStateSyncKeyIdAttribute,
    AppStateSyncKeyDataAttribute,
    AppStateSyncKeyFingerprintAttribute,
    AppStateSyncKeyShareAttribute,
    InitialSecurityNotificationSettingSyncAttribute,
)

__all__ = [
    "HistorySync",
    "HistorySyncAttribute",
    "HistorySyncNotificationAttribute",
    "ConversationAttribute",
    "WebMessageInfoAttribute",
    "MessageKeyAttribute",
    "PushnameAttribute",
    "PastParticipantAttribute",
    "PastParticipantsAttribute",
    "AppStateSyncKeyAttribute",
    "AppStateSyncKeyIdAttribute",
    "AppStateSyncKeyDataAttribute",
    "AppStateSyncKeyFingerprintAttribute",
    "AppStateSyncKeyShareAttribute",
    "InitialSecurityNotificationSettingSyncAttribute",
]

