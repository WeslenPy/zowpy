"""
WARequest compatibility layer for registration endpoints.

Refactor of zowsup WARequest adapted to zowpy package layout.
"""

from __future__ import annotations

import base64
import inspect
import struct
import uuid
from typing import Any, Iterable, Optional, Union
from urllib.parse import quote as urllib_quote

import httpx
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from zowpy.db.manager import AxolotlManager

from zowpy.config.bot_env import BotEnv
from zowpy.profile.profile import AsyncProfile

from ..axolotl.ecc.curve import Curve
from ..config.v1.config import Config
from ..utils.phone import PhoneUtils
from ..utils.tools import WATools
from loguru import logger

from .parser import JSONResponseParser, ResponseParser
from zowpy.db.config.engine import AsyncSessionMaker


def _profile_key_from_config(config: Config) -> str:
    """Nome lógico do perfil (phone ou login) para AsyncProfile / DB."""
    key = config.phone or config.login
    if not key:
        raise ValueError("Config precisa de phone ou login para identificar o perfil")
    return str(key)


class WARequest(object):
    OK = 200
    ENC_PUBKEY = Curve.decodePoint(
        bytearray([
            5, 142, 140, 15, 116, 195, 235, 197, 215, 166, 134, 92, 108,
            60, 132, 56, 86, 176, 97, 33, 204, 232, 234, 119, 77, 34, 251,
            111, 18, 37, 18, 48, 45
        ])
    )

    def __init__(
        self,
        config_or_profile: Optional[Union[Config, AsyncProfile]] = None,
        env: Optional[BotEnv] = None,
        session_maker: Optional[Any] = None,
    ):
        self.pvars = []
        self.port = 443
        self.type = "GET"
        self.parser = None
        self.params: list[tuple[str, Any]] = []
        self.headers: dict[str, str] = {}

        self.sent = False
        self.response: Optional[httpx.Response] = None
        self.env = env
        self._profile: Optional[AsyncProfile] = None
        self._config_or_profile = config_or_profile
        self._config: Optional[Config] = None
        self._axolotlmanager: Optional[AxolotlManager] = None
        self._base_params_added = False
        self._axolotl_params_added = False
        self._p_in: str = ""
        self._session_maker = session_maker if session_maker is not None else AsyncSessionMaker

        if config_or_profile is None:
            return

        if isinstance(config_or_profile, Config):
            self._config = config_or_profile
            self._profile = AsyncProfile(
                _profile_key_from_config(self._config),
                config=self._config,
                session_maker=self._session_maker,
            )
            self._bootstrap_from_config(self._config)
        else:
            self._profile = config_or_profile
            self._config = getattr(self._profile, "_config", None)
            if self._config is not None:
                self._bootstrap_from_config(self._config)

    def _bootstrap_from_config(self, config: Config) -> None:
        
        self._p_in = str(config.phone)[len(str(config.cc)) :]
        if config.expid is None:
            config.expid = WATools.generateDeviceId()

        if config.fdid is None:
            device_env = getattr(self.env, "deviceEnv", None) if self.env is not None else None
            if device_env is not None:
                config.fdid = WATools.generatePhoneId(device_env)
            else:
                # Fallback compatible with old behavior when env was required.
                config.fdid = str(uuid.uuid4())

        if config.client_static_keypair is None:
            config.client_static_keypair = WATools.generateKeyPair()

        self._populate_default_params(config)
        self._base_params_added = True

    async def _ensure_axolotl_manager(self) -> AxolotlManager:
        """
        Obtém e cacheia o AxolotlManager a partir do AsyncProfile.
        Obrigatório para montar os parâmetros criptográficos e_* da registration.
        """
        if self._axolotlmanager is not None:
            return self._axolotlmanager

        if self._profile is None:
            raise RuntimeError(
                "WARequest exige config_or_profile=AsyncProfile com axolotl_manager disponível "
                "(somente Config isolado não fornece identity/prekeys para e_*)."
            )

        self._axolotlmanager = await self._profile.axolotl_manager
        return self._axolotlmanager

    def _populate_default_params(self, config: Config) -> None:
        self.addParam("cc", config.cc)
        self.addParam("in", self._p_in)
        lg, lc = PhoneUtils.getLGLC(str(config.cc))
        self.addParam("lg", lg)
        self.addParam("lc", lc)

        self.addParam("authkey", self.b64encode(config.client_static_keypair.public.data))
        self.addParam("fdid", config.fdid)
        self.addParam("expid", self.b64encode(config.expid))
        self.addParam("rc", "0")

        if config.id:
            self.addParam("id", config.id)

    async def _await_if_needed(self, value: Any) -> Any:
        if inspect.isawaitable(value):
            return await value
        return value

    async def _ensure_initialized(self) -> None:
        if self._base_params_added:
            return

        # Com profile e sem config em memória: carrega Config (ex.: DB via AsyncProfile.config)
        if self._profile is not None and self._config is None:
            loaded = await self._await_if_needed(self._profile.config)
            if loaded is None:
                raise RuntimeError(
                    f"Não foi possível carregar Config para o perfil "
                    f"{getattr(self._profile, '_profile_name', '?')!r}"
                )
            self._config = loaded

        # Com config e sem profile: cria perfil ligado ao Config (axolotl / persistência)
        if self._config is not None and self._profile is None:
            self._profile = AsyncProfile(
                _profile_key_from_config(self._config),
                config=self._config,
                session_maker=self._session_maker,
            )

        if self._config is None:
            return

        if not self._base_params_added:
            self._bootstrap_from_config(self._config)

    async def _ensure_axolotl_params(self) -> None:
        if self._axolotl_params_added:
            return

        manager = await self._ensure_axolotl_manager()

        required_attrs = ("registration_id", "identity", "load_latest_signed_prekey")
        missing = [a for a in required_attrs if not hasattr(manager, a)]
        if missing:
            raise RuntimeError(
                f"AxolotlManager incompatível com WARequest: faltam atributos {missing!r}"
            )

        registration_id = await self._await_if_needed(manager.registration_id)
        self.addParam(
            "e_regid",
            self.b64encode(struct.pack(">I", registration_id)),
        )
        self.addParam("e_keytype", self.b64encode(b"\x05"))
        identity = await self._await_if_needed(manager.identity)
        identity_pub = identity.getPublicKey().serialize()[1:]
        self.addParam("e_ident", self.b64encode(identity_pub))

        signedprekey = await self._await_if_needed(
            manager.load_latest_signed_prekey(generate=True)
        )
        self.addParam("e_skey_id", self.b64encode(struct.pack(">I", signedprekey.getId())[1:]))
        self.addParam("e_skey_val", self.b64encode(signedprekey.getKeyPair().publicKey.serialize()[1:]))
        self.addParam("e_skey_sig", self.b64encode(signedprekey.getSignature()))
        self._axolotl_params_added = True

    def setParsableVariables(self, pvars: Iterable[str]) -> None:
        self.pvars = list(pvars)

    def onResponse(self, name: str, value: Any) -> None:
        if name == "status":
            self.status = value
        elif name == "result":
            self.result = value

    def addParamIf(self, name: str, value: Any, condition: bool) -> None:
        if condition:
            self.addParam(name, value)

    def addParam(self, name: str, value: Any) -> None:
        self.params.append((name, value))

    def getParam(self, name: str) -> Optional[Any]:
        for k, v in self.params:
            if k == name:
                return v
        return None

    def removeParam(self, name: str) -> None:
        self.params = [(k, v) for (k, v) in self.params if k != name]

    def addHeaderField(self, name: str, value: str) -> None:
        self.headers[name] = value

    def clearParams(self) -> None:
        self.params = []

    def getUserAgent(self) -> str:
        if self.env is not None and getattr(self.env, "deviceEnv", None) is not None:
            return self.env.deviceEnv.getUserAgent()
        return "zowpy/registration"

    async def send(
        self,
        parser: Optional[ResponseParser] = None,
        encrypt: bool = True,
        preview: bool = False,
        cert: Optional[Any] = None,
        proxy: Optional[Any] = None,
    ) -> Optional[dict[str, Any]]:
        logger.debug(
            f"send(parser={None if parser is None else '[omitted]'}, encrypt={encrypt}, preview={preview})"
        )
        await self._ensure_initialized()
        await self._ensure_axolotl_params()
        if self.type == "POST":
            return await self.sendPostRequest(parser, proxy=proxy)
        return await self.sendGetRequest(parser, encrypt, preview=preview, cert=cert, proxy=proxy)

    def setParser(self, parser: ResponseParser) -> None:
        if isinstance(parser, ResponseParser):
            self.parser = parser
        else:
            logger.error("Invalid parser")

    def _finalize_json_body(self, raw: Any) -> dict[str, Any]:
        """Aplica JSONResponseParser + pvars quando configurado; senão retorna o dict bruto."""
        if not isinstance(raw, dict):
            if raw is None:
                return {}
            return {"_raw": raw}
        if self.parser is not None and isinstance(self.parser, JSONResponseParser) and self.pvars:
            try:
                parsed = self.parser.parse(raw, self.pvars)
                return parsed if parsed else dict(raw)
            except Exception as exc:
                logger.warning("Falha ao parsear resposta de registration: {}", exc)
                return dict(raw)
        return dict(raw)

    def getConnectionParameters(self) -> tuple[str, int, str]:
        if not getattr(self, "url", None):
            return "", self.port, "/"

        try:
            url = self.url.split("://", 1)
            url = url[0] if len(url) == 1 else url[1]
            host, path = url.split("/", 1)
        except ValueError:
            host = url
            path = ""
        path = "/" + path
        return host, self.port, path

    def encryptParams(self, params: list[tuple[str, Any]], key: Any) -> list[tuple[str, bytes]]:
        keypair = Curve.generateKeyPair()
        encodedparams = self.urlencodeParams(params)
        cipher = AESGCM(Curve.calculateAgreement(key, keypair.privateKey))
        ciphertext = cipher.encrypt(
            b"\x00\x00\x00\x00" + struct.pack(">Q", 0), encodedparams.encode(), b""
        )
        payload = base64.b64encode(keypair.publicKey.serialize()[1:] + ciphertext)
        return [("ENC", payload)]

    async def sendGetRequest(
        self,
        parser: Optional[ResponseParser] = None,
        encrypt_params: bool = True,
        preview: bool = False,
        cert: Optional[Any] = None,
        proxy: Optional[Any] = None,
    ) -> Optional[dict[str, Any]]:
        logger.debug(
            f"sendGetRequest(parser={None if parser is None else '[omitted]'}, encrypt_params={encrypt_params}, preview={preview})"
        )
        self.response = None

        if encrypt_params:
            logger.debug("Encrypting parameters")
            logger.debug(f"pre-encrypt (encoded) parameters =\n{self.urlencodeParams(self.params)}")
            params = self.encryptParams(self.params, self.ENC_PUBKEY)
        else:
            params = self.params

        parser = parser or self.parser or ResponseParser()

        headers = dict(
            list(
                {
                    "Accept": "text/json",
                    "WaMsysRequest": "1",
                    "request_token": str(uuid.uuid4()),
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Connection": "Keep-Alive",
                    "Accept-Encoding": "gzip",
                    "User-Agent": self.getUserAgent(),
                }.items()
            )
            + list(self.headers.items())
        )

        host, port, path = self.getConnectionParameters()
        self.response = await WARequest.sendRequest(
            host, port, path, headers, params, "GET", preview=preview, proxy=proxy
        )
        if preview:
            logger.info("Preview request, skip response handling and return None")
            return None
        if self.response.status_code != WARequest.OK:
            logger.error(f"Request not successful, status was {self.response.status_code}")
            return {}
        return self._finalize_json_body(self.response.json())

    async def sendPostRequest(
        self, parser: Optional[ResponseParser] = None, proxy: Optional[Any] = None
    ) -> dict[str, Any]:
        self.response = None
        params = self.params
        parser = parser or self.parser or ResponseParser()
        headers = dict(
            list(
                {
                    "User-Agent": self.getUserAgent(),
                    "Accept": parser.getMeta(),
                    "Content-Type": "application/x-www-form-urlencoded",
                }.items()
            )
            + list(self.headers.items())
        )

        host, port, path = self.getConnectionParameters()
        self.response = await WARequest.sendRequest(
            host, port, path, headers, params, "POST", proxy=proxy
        )
        if self.response.status_code != WARequest.OK:
            logger.error(f"Request not successful, status was {self.response.status_code}")
            return {}

        self.sent = True
        return self._finalize_json_body(self.response.json())

    def b64encode(self, value: bytes) -> bytes:
        return base64.urlsafe_b64encode(value)

    @classmethod
    def urlencode(cls, value: Any) -> str:
        if not isinstance(value, (str, bytes)):
            value = str(value)

        out = ""
        for char in value:
            if isinstance(char, int):
                char = bytearray([char])
            quoted = urllib_quote(char, safe="")
            out += quoted if quoted[0] != "%" else quoted.lower()

        return out.replace("-", "%2d").replace("_", "%5f").replace("~", "%7e")

    @classmethod
    def urlencodeParams(cls, params: list[tuple[str, Any]]) -> str:
        merged = []
        for k, v in params:
            merged.append("%s=%s" % (k, cls.urlencode(v)))
        return "&".join(merged)

    @staticmethod
    def _build_proxy_dict(proxy: Any) -> Optional[dict[str, str]]:
        if proxy is None:
            return None
        if isinstance(proxy, dict):
            return proxy
        if isinstance(proxy, str):
            return {"http": proxy, "https": proxy}

        required = ("username", "password", "host", "port")
        if all(hasattr(proxy, attr) for attr in required):
            uri = "socks5://%s:%s@%s:%d" % (
                proxy.username,
                proxy.password,
                proxy.host,
                proxy.port,
            )
            return {"http": uri, "https": uri}
        return None

    @classmethod
    async def sendRequest(
        cls,
        host: str,
        port: int,
        path: str,
        headers: dict[str, str],
        params: list[tuple[str, Any]],
        reqType: str = "GET",
        preview: bool = False,
        tls_adapter: Optional[Any] = None,
        proxy: Optional[Any] = None,
    ) -> httpx.Response:
        logger.debug(
            f"sendRequest(host={host}, port={port}, path={path}, reqType={reqType}, preview={preview})"
        )
        
        encoded_params = cls.urlencodeParams(params)
        logger.debug(f"encoded_params: {encoded_params}")
        rawpath = path
        path = path + "?" + encoded_params if reqType == "GET" and encoded_params else path
        proxies = cls._build_proxy_dict(proxy)
        url = f"https://{host}{path}"
        proxy_url = None
        if proxies is not None:
            proxy_url = proxies.get("https") or proxies.get("http")
            
        logger.debug(f"url: {url}")

        if proxy_url is not None:
            logger.debug(f"PROXY REQUEST TO {rawpath}")
            async with httpx.AsyncClient(proxy=proxy_url, timeout=30.0) as client:
                response = await client.request(reqType, url, headers=headers)
        else:
            logger.debug(f"REQUEST TO {rawpath}")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(reqType, url, headers=headers)

        logger.debug(f"response: {response.text}")

        return response
