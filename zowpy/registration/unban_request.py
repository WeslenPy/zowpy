"""
GraphQL unban / ban appeal (graph.whatsapp.com).

Fluxo independente de WARequest (endpoint e formato de corpo diferentes).
"""

from __future__ import annotations

import inspect
import random
from typing import Any, Dict, Mapping, Optional, Sequence, Union

import httpx
from loguru import logger

from zowpy.config.bot_env import BotEnv
from zowpy.config.v1.config import Config
from zowpy.profile.profile import AsyncProfile
from zowpy.utils.phone import PhoneUtils

from .constants import PayloadManager, URLManager
from .parser import MessageContent, ResponseManager

_GRAPHQL_JSON = "application/json"

# Versão WA usada só quando nem ``version`` nem ``DeviceEnv.getVersion()`` existem.
_FALLBACK_WA_VERSION = "2.24.1.78"

DEFAULT_APPEAL_REASONS: tuple[str, ...] = (
    "Conta bloqueada por engano; não violo os Termos de Serviço.",
    "Uso apenas pessoal e familiar; solicito revisão do bloqueio.",
    "Possível denúncia falsa ou envio em massa não autorizado por mim.",
    "Número recuperado de operadora; sou o legítimo titular da linha.",
    "Aparelho trocado recentemente; pode ter ocorrido atividade suspeita automática.",
    "Conta comercial legítima; anexos e conversas podem ser verificados.",
    "Não envio spam nem conteúdo proibido; peço segunda análise humana.",
    "Bloqueio após troca de chip/SIM; não houve uso indevido intencional.",
    "Dispositivo roubado e recuperado; já alterei senhas e segurança.",
    "Uso em conformidade com as políticas; solicito desbloqueio para trabalho.",
)


def _format_mcc_mnc(mcc: Any, mnc: Any) -> Optional[str]:
    if mcc is None or mnc is None:
        return None
    try:
        return f"{int(mcc):03d}-{int(mnc):02d}"
    except (ValueError, TypeError):
        return f"{mcc}-{mnc}"


class AsyncUnbanRequest:
    """
    Cliente assíncrono para ``POST .../graphql`` (appeal / suporte).

    Opcionalmente recebe :class:`Config` ou :class:`AsyncProfile` para preencher
    ``PayloadManager.variables`` (lg/lc, ``debug_info`` com dados do aparelho).

    O texto de recurso (motivo do desbanimento) vem de ``DEFAULT_APPEAL_REASONS``
    escolhido aleatoriamente a cada ``unban``, salvo se ``appeal_description`` for
    passado explicitamente ou ``appeal_reasons`` substituir a lista padrão.

    ``version`` (string tipo ``2.24.1.78``): se omitida, usa ``env.deviceEnv.getVersion()``
    quando ``env`` (:class:`BotEnv`) for passado; senão, fallback interno.
    """

    def __init__(
        self,
        *,
        config: Optional[Config] = None,
        appeal_description: Optional[str] = None,
        appeal_reasons: Optional[Sequence[str]] = None,
        version: Optional[str] = None,
        env: Optional[BotEnv] = None,
        lg: str = "pt",
        lc: str = "BR",
        context: str = "blocked_ban_appeals",
    ) -> None:
        self._config = config
        self._appeal_description = appeal_description
        self._appeal_reasons = appeal_reasons
        self._version = version
        self._env = env
        self._lg = lg
        self._lc = lc
        self._context = context
        
        
    async def _ensure_config(self) -> Optional[Config]:
        if self._config is not None:
            return self._config
        raise ValueError("Config is required")

    @staticmethod
    def _debug_overrides_from_config(cfg: Config) -> Dict[str, Any]:
        """Mapeia campos do Config para chaves do debug_info do GraphQL."""
        out: Dict[str, Any] = {}
        if cfg.manufacturer:
            out["Manufacturer"] = cfg.manufacturer
        device_label = cfg.device_name or cfg.device
        if device_label:
            out["Device"] = device_label
            out["Model"] = cfg.device_model_type or device_label
        if cfg.os_version:
            out["OS"] = str(cfg.os_version)
        elif cfg.os_name:
            out["OS"] = str(cfg.os_name)
        radio = _format_mcc_mnc(cfg.mcc, cfg.mnc)
        if radio:
            out["Radio MCC-MNC"] = radio
        sim = _format_mcc_mnc(cfg.sim_mcc, cfg.sim_mnc)
        if sim:
            out["SIM MCC-MNC"] = sim
        if cfg.platform:
            out.setdefault("useragent", f"WhatsApp client {cfg.platform}")
        return out

    def _pick_appeal_description(self) -> str:
        if self._appeal_description is not None:
            return self._appeal_description
        if not self._appeal_reasons:
            return "Solicito revisão do bloqueio da conta."
        return random.choice(self._appeal_reasons)

    def _resolve_version(self) -> str:
        if self._version is not None and str(self._version).strip():
            return str(self._version).strip()
        device_env = self._env.deviceEnv
        v = device_env.getVersion()
        return str(v).strip() if v is not None else _FALLBACK_WA_VERSION

    async def _variables_json(self, request_token: str) -> str:
        cfg = await self._ensure_config()

        description = self._pick_appeal_description()
        version = self._resolve_version()
        lg, lc = self._lg, self._lc
        context = self._context
        debug_overrides: Optional[Dict[str, Any]] = None

        if cfg is not None:
            if cfg.cc is not None:
                lg, lc = PhoneUtils.getLGLC(str(cfg.cc))
            overrides = self._debug_overrides_from_config(cfg)
            if overrides:
                debug_overrides = overrides

        os_name: Optional[str] = None
        if cfg is not None and cfg.os_name:
            os_name = str(cfg.os_name)
        elif self._env is not None and getattr(self._env, "deviceEnv", None) is not None:
            os_name = str(self._env.deviceEnv.getOSName() or "") or None

        return PayloadManager.variables(
            description=description,
            request_token=request_token,
            version=version,
            lg=lg,
            lc=lc,
            context=context,
            os_name=os_name,
            debug_overrides=debug_overrides,
        )

    @staticmethod
    def _proxy_url(proxy: Optional[Union[str, Mapping[str, str], Any]]) -> Optional[str]:
        if proxy is None:
            return None
        if isinstance(proxy, str):
            return proxy
        if isinstance(proxy, Mapping):
            return str(proxy.get("https") or proxy.get("http") or "")
        return getattr(proxy, "url", None)

    async def unban(
        self,
        token: str,
        *,
        proxy: Optional[Union[str, Mapping[str, str], Any]] = None,
        timeout: float = 30.0,
    ) -> MessageContent:
        """
        Envia pedido GraphQL de appeal usando o token (request_token) informado.

        :param token: request_token / token do fluxo de appeal
        :param proxy: URL de proxy (ex. ``http://host:8080``) ou mapa ``{"https": "..."}``
        :param timeout: timeout HTTP em segundos
        """
        variables_graph = await self._variables_json(token)
        
        logger.debug(f"variables_graph: {variables_graph}")
        payload: dict[str, Any] = {
            "access_token": PayloadManager.access_token(),
            "Content-Type": _GRAPHQL_JSON,
            "doc_id": PayloadManager.doc_id(),
            "variables": variables_graph,
            "lang": "pt_BR",
        }
        url = f"{URLManager.wa_graphql()}/graphql"
        headers = {
            "Content-Type": _GRAPHQL_JSON,
            "Host": URLManager.wa_graphql_host(),
        }
        proxy_url = self._proxy_url(proxy) or None

        try:
            async with httpx.AsyncClient(proxy=proxy_url, timeout=timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            logger.error("AsyncUnbanRequest.unban falhou na rede: {}", exc)
            raise

        rm = ResponseManager(response)
        body = rm.get_json()
        
        logger.debug(f"body: {body}")
        
        
        
        if not isinstance(body, dict):
            return MessageContent({}, rm)

        data = body.get("data")
        data = data if isinstance(data, dict) else {}

        support = data.get("whatsapp_support_process_ban_appeal_request")
        support = support if isinstance(support, dict) else {}

        if body.get("errors"):
            support = {**support, "graphql_errors": body["errors"]}

        msg_data = support if support else data
        return MessageContent(msg_data, rm)
