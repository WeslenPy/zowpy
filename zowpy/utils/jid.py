"""
JID Utilities - Utilitários para JID.
"""

from typing import Optional


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
    jid = jid.replace("@s.whatsapp.net", "")
    jid = jid.replace("@g.us", "")
    
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
        return f"{jid}@g.us"
    else:
        return f"{jid}@s.whatsapp.net"


