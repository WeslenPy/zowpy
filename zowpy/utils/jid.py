"""
JID Utilities - Utilitários para JID.
"""

from typing import Optional
from .constants import YowConstants


def is_group_jid( jid: str) -> bool:
    """
    Verifica se JID é de grupo.
    
    Um JID é considerado grupo se:
    - Contém "@g.us" OU
    - Tem >= 15 caracteres
    """
    return "-" in jid or ("." not in jid and ":" not in jid and len(jid) >= 15) or f"@{YowConstants.WHATSAPP_GROUP_SERVER}" in jid or jid == YowConstants.WHATSAPP_STATUS_SERVER
    


def is_lid(jid: str) -> bool:
    """Return True if jid is a LID (ends with @lid)."""
    return bool(jid and (jid.endswith(f"@{YowConstants.LID_SUFFIX}") or jid.rstrip().endswith(f"@{YowConstants.LID_SUFFIX}")))


def normalize(jid: str) -> Optional[str]:
    """
    Normaliza JID.
    
    Preserva endereços LID (@lid); não converte LID em JID.
    
    Args:
        jid: JID para normalizar
    
    Returns:
        JID normalizado ou None se inválido
    """
    if not jid:
        return None
    jid = jid.strip()
    # Preservar LID: não alterar sufixo @lid
    if f"@{YowConstants.LID_SUFFIX}" in jid:
        return jid
    # Remove @s.whatsapp.net se presente
    jid = jid.replace(f"@{YowConstants.WHATSAPP_SERVER}", "").replace("+", "")
    jid = jid.replace(f"@{YowConstants.WHATSAPP_GROUP_SERVER}", "")
    
    # Remove caracteres não numéricos
    jid = ''.join(filter(str.isdigit, jid))
    
    if not jid:
        return None
    
    return jid


def to_whatsapp_jid(jid: str, is_group: bool = False) -> str:
    """
    Converte JID para formato WhatsApp.
    
    Preserva LID (@lid); não converte LID em JID.
    
    Args:
        jid: JID para converter
        is_group: Se é grupo
    
    Returns:
        JID no formato WhatsApp ou LID inalterado
    """
    if not jid:
        raise ValueError("Invalid JID")
    jid = jid.strip()
    # Preservar LID
    if is_lid(jid):
        return jid
    jid = normalize(jid)
    if not jid:
        raise ValueError("Invalid JID")
    
    if is_group_jid(jid):
        if jid.endswith(YowConstants.WHATSAPP_BROADCAST_SERVER):return jid
        return f"{jid}@{YowConstants.WHATSAPP_GROUP_SERVER}"
    else:
        return f"{jid}@{YowConstants.WHATSAPP_SERVER}"












