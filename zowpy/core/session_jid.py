"""
Helpers para JID e sessão: decodificação, filtro por sessão existente e deduplicação.

Usado por ensure_sessions_and_send_to_contacts, _get_keys_for_recipient e
ensure_sessions_and_send_to_group para evitar duplicação de lógica e inconsistência.
"""

from typing import List, Set, Tuple, Union

from zowpy.utils.tools import WATools


def jid_to_recipient_device(jid: str) -> Tuple[Union[int, str], int]:
    """
    Decodifica JID para (recipient_id, device_id) com normalização numérica.

    Usa WATools.jidDecode no username; retorna recipient_id como int quando
    for numérico (para consistência com o store).
    """
    username = str(jid).split("@")[0]
    r, _, d = WATools.jidDecode(username)
    return (int(r), d) if (isinstance(r, str) and str(r).isdigit()) else (r, d)


def existing_sessions_set(jids_maps) -> Set[Tuple[Union[int, str], int]]:
    """
    Monta o set de (recipient_id, device_id) a partir do retorno de session_exists_bulk.

    jids_maps: iterable de (recipient_id, deviceid) retornado por session_exists_bulk.
    """
    out = set()
    for recipient_id, deviceid in jids_maps:
        r = (
            int(recipient_id)
            if (isinstance(recipient_id, str) and str(recipient_id).isdigit())
            else recipient_id
        )
        out.add((r, deviceid))
    return out


def jids_without_session(
    jids: List[str],
    jids_maps,
) -> List[str]:
    """
    Retorna os JIDs que não têm sessão segundo jids_maps (retorno de session_exists_bulk).
    """
    existing = existing_sessions_set(jids_maps)
    return [jid for jid in jids if jid_to_recipient_device(jid) not in existing]


def deduplicate_jids_by_recipient_device(jids: List[str]) -> List[str]:
    """
    Mantém um JID por (recipient_id, device_id); ordem preservada, primeira ocorrência.
    """
    seen: Set[Tuple[Union[int, str], int]] = set()
    result: List[str] = []
    for jid in jids:
        rd = jid_to_recipient_device(jid)
        if rd not in seen:
            seen.add(rd)
            result.append(jid)
    return result
