"""
JID Utilities - Utilitários para JID.
"""

from typing import Optional
from .constants import YowConstants


def normalize(jid: str) -> Optional[str]:
    """
    Normaliza JID.
    
    Args:
        jid: JID para normalizar
    
    Returns:
        JID normalizado ou None se inválido
    """
    if not jid:
        return None
    
    # Remove @s.whatsapp.net se presente
    jid = jid.replace(f"@{YowConstants.WHATSAPP_SERVER}", "")
    jid = jid.replace(f"@{YowConstants.WHATSAPP_GROUP_SERVER}", "")
    
    # Remove caracteres não numéricos
    jid = ''.join(filter(str.isdigit, jid))
    
    if not jid:
        return None
    
    return jid


def to_whatsapp_jid(jid: str, is_group: bool = False) -> str:
    """
    Converte JID para formato WhatsApp.
    
    Args:
        jid: JID para converter
        is_group: Se é grupo
    
    Returns:
        JID no formato WhatsApp
    """
    jid = normalize(jid)
    if not jid:
        raise ValueError("Invalid JID")
    
    if is_group:
        return f"{jid}@{YowConstants.WHATSAPP_GROUP_SERVER}"
    else:
        return f"{jid}@{YowConstants.WHATSAPP_SERVER}"








