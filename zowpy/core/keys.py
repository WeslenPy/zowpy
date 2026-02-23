"""
Parsing da resposta de Get Keys (IQ encrypt): extração de PreKeyBundle por usuário.

Funções puras para facilitar testes e manter o client focado em orquestração.
"""

import binascii
import sys
from typing import List, Optional, Tuple

from ..protocol.structs import ProtocolNode
from ..axolotl.state.prekeybundle import PreKeyBundle
from ..axolotl.identitykey import IdentityKey
from ..axolotl.ecc.djbec import DjbECPublicKey


def _bytes_to_int(val) -> int:
    if sys.version_info >= (3, 0):
        val_enc = val.encode("latin-1") if type(val) is str else val
    else:
        val_enc = val
    return int(binascii.hexlify(val_enc), 16)


def _enc_str(string):
    if sys.version_info >= (3, 0) and type(string) is str:
        return string.encode("latin-1")
    return string


def parse_prekey_bundle_from_user_node(
    user_node: ProtocolNode,
) -> Tuple[Optional[PreKeyBundle], Optional[Exception]]:
    """
    Extrai PreKeyBundle de um node <user> da resposta de get keys.

    Returns:
        (bundle, None) em sucesso; (None, error) se faltar parâmetros ou der erro.
    """
    registration_node = user_node.get_child("registration")
    identity_node = user_node.get_child("identity")
    signed_prekey_node = user_node.get_child("skey")
    prekey_node = user_node.get_child("key")

    if not registration_node or not identity_node or not signed_prekey_node:
        return (None, Exception("Faltam parâmetros obrigatórios na resposta"))

    try:
        registration_id = _bytes_to_int(registration_node.data)
        identity_key = IdentityKey(DjbECPublicKey(_enc_str(identity_node.data)))

        signed_prekey_id = _bytes_to_int(signed_prekey_node.get_child("id").data)
        signed_prekey_pub = DjbECPublicKey(
            _enc_str(signed_prekey_node.get_child("value").data)
        )
        signed_prekey_sig = _enc_str(
            signed_prekey_node.get_child("signature").data
        )

        prekey_id = None
        prekey_public = None
        if prekey_node:
            prekey_id = _bytes_to_int(prekey_node.get_child("id").data)
            prekey_public = DjbECPublicKey(
                _enc_str(prekey_node.get_child("value").data)
            )

        bundle = PreKeyBundle(
            registration_id,
            1,
            prekey_id,
            prekey_public,
            signed_prekey_id,
            signed_prekey_pub,
            signed_prekey_sig,
            identity_key,
        )
        return (bundle, None)
    except Exception as e:
        return (None, e)


def parse_get_keys_response(
    list_node: ProtocolNode,
) -> List[Tuple[str, Optional[PreKeyBundle], Optional[Exception]]]:
    """
    Percorre os <user> do node <list> e retorna lista de (jid, bundle ou None, error ou None).

    Se o <user> tem <error>, retorna (jid, None, Exception). Senão tenta extrair o bundle.
    """
    result: List[Tuple[str, Optional[PreKeyBundle], Optional[Exception]]] = []
    for user_node in list_node.children:
        if user_node.tag != "user":
            continue
        jid = user_node.get_attribute("jid")
        if not jid:
            continue

        error_child = user_node.get_child("error")
        if error_child:
            code = error_child.get_attribute("code")
            text = error_child.get_attribute("text")
            result.append((jid, None, Exception(f"Erro {code}: {text}")))
            continue

        bundle, err = parse_prekey_bundle_from_user_node(user_node)
        result.append((jid, bundle, err))
    return result
