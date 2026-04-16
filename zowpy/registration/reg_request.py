"""
Async Reg Request - Requisição de registro assíncrona.

Refatora WARegRequest para async usando aiohttp.
"""

import asyncio
import base64
import random
from typing import Optional, Dict, Any
from loguru import logger
from zowpy.config.bot_env import BotEnv
from zowpy.proto import e2e_pb2
from zowpy.db.factory import AxolotlManagerFactory


from zowpy.axolotl.ecc.curve import Curve
from zowpy.config.v1.config import Config
from zowpy.registration.parser import JSONResponseParser
from .wa_request import WARequest
try:
    import aiohttp
except ImportError:
    aiohttp = None
    logger.warning("aiohttp não disponível, funcionalidade de registration limitada")


class AsyncRegRequest(WARequest):
    """Requisição de registro assíncrona."""

    def __init__(self, phone_number: str, code: str, 
                 config: Optional[Config] = None, 
                 env: Optional[BotEnv] = None):
        super().__init__(config_or_profile=config, env=env)
        self.phone_number = phone_number
        self.code = code
        self.config = config
        self.env = env
        self.url = "https://v.whatsapp.net/v2/register"
        self.addParam("code", code)

        os_name = env.deviceEnv.getOSName() if env and getattr(env, "deviceEnv", None) else None

        if os_name == "SMB iOS":
            pass
            # logReq = WAClientLogRequest(self._config,log_obj = {
            #         "event_name":"smb_client_onboarding_journey",
            #         "is_logged_in_on_consumer_app":"0",
            #         "sequence_number":"14",
            #         "app_install_source":"unknown|unknown",
            #         "smb_onboarding_step":"20",
            #         "has_consumer_app":"1"

            #     },env=self.env)                            
            # logReq.send(preview=False)
                
        if os_name in ["SMBA", "SMB iOS"] and config is not None:
            payload = e2e_pb2.VerifiedNameCertificate()            
            details = e2e_pb2.VerifiedNameCertificate.Details()
            details.serial = random.randint(1,1000000000000000)                   
            details.issuer = "smb:wa"        
            details.verifiedName = config.pushname  
            payload.details.MergeFrom(details)                            
            try:
                # Mantém compatibilidade sem quebrar quando manager assíncrono não está pronto aqui.
                db = AxolotlManagerFactory().get_manager(config.phone, config.phone)
                payload.signature = Curve.calculateSignature(
                    db.identity.privateKey, payload.details.SerializeToString()
                )
                self.addParam("vname", str(base64.urlsafe_b64encode(payload.SerializeToString()), "utf-8"))
            except Exception:
                logger.warning("Não foi possível gerar vname no init; seguindo sem vname")

        self.addParam("entered",1)
        self.addParam("network_operator_name","SMART")
        self.addParam("sim_operator_name","SMART 5G")

        self.url = "v.whatsapp.net/v2/register"

        self.pvars = ["status", "login", "autoconf_type", "security_code_set","type", "edge_routing_info", "chat_dns_domain"
                      ,"retry_after","reason"]

        self.setParser(JSONResponseParser())