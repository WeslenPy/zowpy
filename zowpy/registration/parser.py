"""
Parsers de resposta para registration (v2 exists/code/register).

Padrão zowpy: tipagem explícita, loguru, compatível com httpx.Response.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, Mapping, Optional, Union

from httpx import Response
from loguru import logger


class ResponseManager:
    """Envolve httpx.Response com acesso tipado a corpo e cabeçalhos."""

    def __init__(self, response: Optional[Response] = None) -> None:
        self.response = response

    @property
    def headers(self) -> dict:
        return {} if not self.response else dict(self.response.headers)

    @property
    def status_code(self) -> int:
        return 500 if not self.response else self.response.status_code

    @property
    def is_json(self) -> bool:
        if not self.response:
            return False
        ct = self.response.headers.get("Content-Type", "")
        return "json" in ct.lower()

    def get_json(self) -> dict:
        if not self.response:
            return {}
        try:
            data = self.response.json()
            return data if isinstance(data, dict) else {"_data": data}
        except Exception as e:
            logger.debug("ResponseManager.get_json falhou: {}", e)
            return {}

    def get_text(self) -> str:
        if not self.response:
            return ""
        try:
            return self.response.text
        except Exception as e:
            logger.debug("ResponseManager.get_text falhou: {}", e)
            return ""


class MessageContent:
    """Campos comuns das respostas JSON de registration."""

    def __init__(self, data: dict, response: ResponseManager) -> None:
        self.data = data
        self.response = response

    @property
    def status_code(self) -> int:
        return self.response.status_code

    @property
    def reason(self) -> str:
        return (self.data.get("reason", "") or "").upper()

    @property
    def status(self) -> str:
        return (self.data.get("status", "fail") or "fail").upper()

    @property
    def violation_type(self) -> str:
        return self.data.get("violation_type", "21") or "21"

    @property
    def token(self) -> str:
        return self.data.get("appeal_token", "") or ""

    @property
    def phone(self) -> str:
        return self.data.get("login", "") or ""

    @property
    def sms_wait(self) -> Any:
        return self.data.get("sms_wait", "") or ""

    @property
    def type_account(self) -> str:
        return self.data.get("type", "") or ""

    @property
    def lid(self) -> str:
        return self.data.get("lid", "") or ""

    @property
    def send_sms_eligible(self) -> Any:
        return self.data.get("send_sms_eligible", "") or ""

    @property
    def wa_old_eligible(self) -> Any:
        return self.data.get("wa_old_eligible", "") or ""

    @property
    def wa_old_wait(self) -> Any:
        return self.data.get("wa_old_wait", "") or ""

    @property
    def send_sms_wait(self) -> Any:
        return self.data.get("send_sms_wait", "") or ""

    @property
    def cert(self) -> Any:
        return self.data.get("cert", "") or ""

    @property
    def possible_migration(self) -> Any:
        return self.data.get("possible_migration", "") or ""


class ResponseParser:
    """Parser base (Accept / meta)."""

    def __init__(self, meta: str = "*") -> None:
        self.meta = meta

    def parse(self, data: Any, pvars: Any) -> Any:
        return data

    def getMeta(self) -> str:
        return self.meta

    @staticmethod
    def getVars(pvars: Any) -> Dict[str, str]:
        if isinstance(pvars, Mapping):
            return {str(k): str(v) for k, v in pvars.items()}
        if isinstance(pvars, Iterable) and not isinstance(pvars, (str, bytes)):
            return {str(p): str(p) for p in pvars}
        return {}


class JSONResponseParser(ResponseParser):
    """
    Extrai campos aninhados de um JSON usando chaves com notação por ponto.

    - ``pvars`` como lista: cada nome vira caminho e chave de saída
 (ex.: ``["status", "edge_routing_info"]``).
    - ``pvars`` como dict: chave de saída -> caminho no JSON (ex.
      ``{"st": "status", "edge": "edge_routing_info"}``).
    """

    def __init__(self) -> None:
        super().__init__(meta="text/json")

    def parse(self, data: Union[str, bytes, dict, list], pvars: Any) -> Dict[str, Any]:
        root = self._normalize_root(data)
        if root is None:
            return {}

        var_map = self.getVars(pvars)
        parsed: Dict[str, Any] = {}
        for out_key, path in var_map.items():
            parsed[out_key] = self.query(root, path)
        return parsed

    def parse_response(self, response: Response, pvars: Any) -> Dict[str, Any]:
        """Conveniência: corpo da resposta httpx + mesmas regras de ``parse``."""
        try:
            body = response.json()
        except Exception as e:
            logger.warning("JSONResponseParser.parse_response: corpo não é JSON: {}", e)
            return {}
        return self.parse(body, pvars)

    @staticmethod
    def _normalize_root(data: Union[str, bytes, dict, list]) -> Optional[Union[dict, list]]:
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            return data
        if isinstance(data, (str, bytes)):
            if not data:
                return {}
            try:
                text = data.decode("utf-8") if isinstance(data, bytes) else data
                loaded = json.loads(text)
                if isinstance(loaded, dict):
                    return loaded
                if isinstance(loaded, list):
                    return loaded
                return {"_value": loaded}
            except json.JSONDecodeError as e:
                logger.warning("JSONResponseParser: JSON inválido: {}", e)
                return {}
        return None

    def query(self, d: Any, key: str) -> Any:
        if d is None or not key:
            return None
        keys = key.split(".", 1)
        curr_key = keys[0]

        if isinstance(d, dict):
            if curr_key not in d:
                return None
            item = d[curr_key]
            if len(keys) == 1:
                return item
            if isinstance(item, dict):
                return self.query(item, keys[1])
            if isinstance(item, list):
                rest = keys[1]
                return [self.query(i, rest) for i in item if isinstance(i, (dict, list))]
            return None

        if isinstance(d, list):
            return [self.query(i, key) for i in d]

        return None
