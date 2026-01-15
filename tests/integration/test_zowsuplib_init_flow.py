"""
Teste de integração (sem rede real) para validar o fluxo de inicialização
no estilo do zowsup-lib:

- Componentes prontos (stream + noise protocol + bridge) antes de emitir EVENT_AUTH
- EVENT_AUTH dispara handshake
- Handshake -> estado transport -> EVENT_AUTHED (handshake_completed=True)
- Server <success> (simulado) -> EVENT_AUTHED (success) -> cliente autenticado
"""

import asyncio
import base64
import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from zowpy.core.whatsapp_client import WhatsAppClient
from zowpy.db.pool import AsyncDatabasePool
from zowpy.db import init_db
from zowpy.noise.structs import KeyPair
from zowpy.protocol.auth import AsyncAuthHandler
from zowpy.protocol.structs import ProtocolNode
from zowpy.utils.tools import StorageTools


@pytest.mark.asyncio
@pytest.mark.integration
async def test_init_flow_matches_zowsuplib_semantics(tmp_path):
    phone = "5511999999999"
    db_path = tmp_path / "zowpy-test.db"
    db_pool = AsyncDatabasePool(f"sqlite+aiosqlite:///{db_path}")
    await db_pool.initialize()
    await init_db(db_pool=db_pool)

    # Config mínima para passar pelas validações do handshake
    kp = KeyPair.generate()
    config = {
        "client_static_keypair": base64.b64encode(kp.serialize()).decode(),
        "fdid": str(uuid.uuid4()),
        "expid": base64.b64encode(uuid.uuid4().bytes).decode(),
    }
    await StorageTools.writeProfileConfig(phone, json.dumps(config).encode("utf-8"), db_pool)

    # Fakes/patches para evitar rede real e handshake criptográfico real
    class FakeConnection:
        def __init__(self, endpoint, proxy=None, on_message=None):
            self.endpoint = endpoint
            self.proxy = proxy
            self.on_message = on_message
            self.sent = []

        async def connect(self, timeout: float = 30.0):
            return None

        async def send(self, data: bytes):
            self.sent.append(data)

        async def disconnect(self):
            return None

    class FakeAxolotlManager:
        # _perform_handshake lê esses campos; no zowpy atual eles não são usados no start()
        identity = None
        registration_id = 1234

        async def level_prekeys(self):
            return [1, 2, 3]

    class FakeAxolotlFactory:
        def __init__(self, db_pool=None):
            self.db_pool = db_pool

        def get_manager(self, *args, **kwargs):
            return FakeAxolotlManager()

    # Vamos validar ordering dentro do start()
    start_checks = {"called": False}

    class FakeNoiseProtocol:
        def __init__(self, protocol_state_callback=None, recovery_callback=None):
            self._protocol_state_callback = protocol_state_callback
            self._state = "init"
            self._rs = None

        @property
        def state(self):
            return self._state

        @property
        def rs(self):
            return self._rs

        async def start(self, stream, client_config, s, rs=None, mode=None, identity=None, regid=None, signedprekey=None, deviceid=None):
            # Bridge deve estar ativo ANTES do handshake começar
            assert stream is not None
            assert client_config is not None
            start_checks["called"] = True
            self._state = "transport"

            if self._protocol_state_callback:
                await self._protocol_state_callback("transport")

        async def receive(self, timeout=None):
            await asyncio.sleep(0)
            return None

    with patch("zowpy.core.whatsapp_client.AsyncConnection", FakeConnection), patch(
        "zowpy.core.whatsapp_client.AxolotlManagerFactory", FakeAxolotlFactory
    ), patch("zowpy.core.whatsapp_client.AsyncWANoiseProtocol", FakeNoiseProtocol):
        client = WhatsAppClient(phone, db_pool=db_pool, device_config="smb_android")

        # Quando handshake terminar (EVENT_AUTHED com handshake_completed=True),
        # simulamos o <success> do servidor para completar autenticação.
        async def on_authed(data):
            if data.get("handshake_completed"):
                await client.auth_handler.handle_success(ProtocolNode(tag="success"))

        client.events.on(AsyncAuthHandler.EVENT_AUTHED, on_authed)

        await client.connect()

        assert start_checks["called"] is True
        assert client.is_connected() is True

        await client.disconnect()

    await db_pool.close()


