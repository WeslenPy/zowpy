# Integração do ZowPy em uma API FastAPI

Este documento descreve como integrar o **ZowPy** (cliente WhatsApp assíncrono) em uma aplicação **FastAPI**, cobrindo ciclo de vida, múltiplas contas, proxy, webhooks e boas práticas.

---

## 1. Visão geral

O ZowPy expõe:

- **`ZowPyClient`**: cliente por conta (envio de mensagens, grupos, mídia, eventos).
- **`AccountManager`**: gerenciador de múltiplas contas (`add_account`, `connect_all`, `disconnect_all`, `shutdown`).

A integração com FastAPI deve:

1. Inicializar banco de dados e (opcionalmente) `AccountManager` no **startup**.
2. Encerrar clientes, desconectar contas e finalizar o engine do banco no **shutdown**.
3. Expor rotas para conectar, desconectar, enviar mensagens, gerenciar grupos, proxy etc.

---

## 2. Dependências

Adicione ao `requirements.txt` (ou `pyproject.toml`):

```text
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
zowpy
```

As dependências do ZowPy (aiosqlite/asyncpg, aiohttp, sqlalchemy, etc.) já vêm com o pacote.

---

## 3. Estrutura sugerida do projeto

```text
my_api/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI app, lifespan
│   ├── config.py         # Settings (DB, etc.)
│   ├── zowpy_app.py      # Estado global: AccountManager, clientes
│   └── routers/
│       ├── __init__.py
│       ├── accounts.py   # Connect, disconnect, status
│       ├── messages.py   # Send text, media
│       ├── groups.py     # Grupos
│       └── proxy.py      # Proxy
├── requirements.txt
└── .env
```

---

## 4. Configuração e estado global

### 4.1 Config (`app/config.py`)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    zowpy_db_url: str = "sqlite+aiosqlite:///./zowpy.db"
    # Ou PostgreSQL: "postgresql+asyncpg://user:pass@localhost/zowpy"

    class Config:
        env_file = ".env"
```

### 4.2 Estado ZowPy (`app/zowpy_app.py`)

```python
from typing import Optional
from zowpy import AccountManager, ZowPyClient
from zowpy.db.config.engine import AsyncSessionMaker

_manager: Optional[AccountManager] = None

def get_manager() -> AccountManager:
    if _manager is None:
        raise RuntimeError("AccountManager não inicializado")
    return _manager

async def init_zowpy(session_maker: Optional[AsyncSessionMaker] = None):
    global _manager
    from zowpy.db.config import create_db
    await create_db()
    _manager = AccountManager(session_maker=session_maker or AsyncSessionMaker)

async def shutdown_zowpy():
    global _manager
    if _manager:
        await _manager.shutdown()
        _manager = None
```

---

## 5. Ciclo de vida FastAPI (startup/shutdown)

Use o **lifespan** do FastAPI para inicializar e finalizar o ZowPy:

```python
# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.config import Settings
from app.zowpy_app import init_zowpy, shutdown_zowpy

settings = Settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_zowpy()
    yield
    # Shutdown
    await shutdown_zowpy()

app = FastAPI(lifespan=lifespan)


class HealthResponse(BaseModel):
    """Resposta do health check."""
    status: str = Field(default="ok", description="Status do serviço")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()
```

Isso garante que, ao encerrar a aplicação, `AccountManager.shutdown()` rode (incluindo `disconnect_all` e `engine.dispose`), evitando threads e conexões órfãs.

---

## 6. Rotas de contas (connect / disconnect / status)

### 6.1 Schemas Pydantic (accounts)

| Schema | Uso | Campos |
|--------|-----|--------|
| `ConnectRequest` | Request body `POST /connect` | `account_id: str` |
| `ConnectResponse` | Response `POST /connect` | `account_id: str`, `status: Literal["connected"]` |
| `DisconnectRequest` | Request body `POST /disconnect` | `account_id: str` |
| `DisconnectResponse` | Response `POST /disconnect` | `account_id: str`, `status: Literal["disconnected"]` |
| `AccountStatusResponse` | Response `GET /{account_id}/status` | `account_id: str`, `connected: bool` |

### 6.2 Router de contas

```python
# app/routers/accounts.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

from app.zowpy_app import get_manager

router = APIRouter(prefix="/accounts", tags=["accounts"])


# --- Request schemas ---

class ConnectRequest(BaseModel):
    """Body para conectar uma conta."""
    account_id: str = Field(..., description="ID da conta (número de telefone, ex: 5511999999999)")


class DisconnectRequest(BaseModel):
    """Body para desconectar uma conta."""
    account_id: str = Field(..., description="ID da conta a desconectar")


# --- Response schemas ---

class ConnectResponse(BaseModel):
    """Resposta ao conectar conta."""
    account_id: str = Field(..., description="ID da conta conectada")
    status: Literal["connected"] = Field(default="connected", description="Status da operação")


class DisconnectResponse(BaseModel):
    """Resposta ao desconectar conta."""
    account_id: str = Field(..., description="ID da conta desconectada")
    status: Literal["disconnected"] = Field(default="disconnected", description="Status da operação")


class AccountStatusResponse(BaseModel):
    """Resposta do status da conta."""
    account_id: str = Field(..., description="ID da conta")
    connected: bool = Field(..., description="True se a conta está conectada ao WhatsApp")


# --- Endpoints ---

@router.post("/connect", response_model=ConnectResponse)
async def connect_account(body: ConnectRequest) -> ConnectResponse:
    manager = get_manager()
    client = await manager.add_account(body.account_id)
    await client.connect()
    return ConnectResponse(account_id=body.account_id)

@router.post("/disconnect", response_model=DisconnectResponse)
async def disconnect_account(body: DisconnectRequest) -> DisconnectResponse:
    manager = get_manager()
    client = await manager.get_account(body.account_id)
    if not client:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    await manager.remove_account(body.account_id)
    return DisconnectResponse(account_id=body.account_id)

@router.get("/{account_id}/status", response_model=AccountStatusResponse)
async def account_status(account_id: str) -> AccountStatusResponse:
    manager = get_manager()
    client = await manager.get_account(account_id)
    if not client:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    connected = client._client is not None and client._client.is_connected()
    return AccountStatusResponse(account_id=account_id, connected=connected)
```

---

## 7. Rotas de mensagens

### 7.1 Schemas Pydantic (messages)

| Schema | Uso | Campos |
|--------|-----|--------|
| `SendTextRequest` | Request `POST /send/text` | `account_id: str`, `to: str`, `text: str` |
| `SendTextResponse` | Response `POST /send/text` | `message_id: str`, `to: str` |
| `SendImageRequest` | Request `POST /send/image` | `account_id: str`, `to: str`, `url: str`, `caption: str \| None` |
| `SendImageResponse` | Response `POST /send/image` | `message_id: str`, `to: str` |

### 7.2 Envio de texto e mídia

```python
# app/routers/messages.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.zowpy_app import get_manager

router = APIRouter(prefix="/messages", tags=["messages"])


# --- Request schemas ---

class SendTextRequest(BaseModel):
    """Body para envio de mensagem de texto."""
    account_id: str = Field(..., description="ID da conta que envia")
    to: str = Field(
        ...,
        description="JID ou número do destinatário (ex: 5511999999999 ou 120363423929565689@g.us)"
    )
    text: str = Field(..., description="Texto da mensagem")


class SendImageRequest(BaseModel):
    """Body para envio de imagem por URL."""
    account_id: str = Field(..., description="ID da conta que envia")
    to: str = Field(..., description="JID ou número do destinatário")
    url: str = Field(..., description="URL da imagem")
    caption: Optional[str] = Field(None, description="Legenda da imagem (opcional)")


# --- Response schemas ---

class SendTextResponse(BaseModel):
    """Resposta ao enviar texto."""
    message_id: str = Field(..., description="ID da mensagem enviada")
    to: str = Field(..., description="Destinatário")


class SendImageResponse(BaseModel):
    """Resposta ao enviar imagem."""
    message_id: str = Field(..., description="ID da mensagem enviada")
    to: str = Field(..., description="Destinatário")


# --- Endpoints ---

@router.post("/send/text", response_model=SendTextResponse)
async def send_text(body: SendTextRequest) -> SendTextResponse:
    manager = get_manager()
    client = await manager.get_account(body.account_id)
    if not client:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    if not client._client or not client._client.is_connected():
        raise HTTPException(status_code=503, detail="Conta não conectada")
    try:
        message_id = await client.send_text(body.to, body.text)
        return SendTextResponse(message_id=message_id, to=body.to)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send/image", response_model=SendImageResponse)
async def send_image(body: SendImageRequest) -> SendImageResponse:
    manager = get_manager()
    client = await manager.get_account(body.account_id)
    if not client:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    if not client._client or not client._client.is_connected():
        raise HTTPException(status_code=503, detail="Conta não conectada")
    try:
        msg_id = await client.send_image(body.to, body.url, caption=body.caption)
        return SendImageResponse(message_id=msg_id, to=body.to)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 8. Rotas de grupos

### 8.1 Schemas Pydantic (groups)

| Schema | Uso | Campos |
|--------|-----|--------|
| `CreateGroupRequest` | Request `POST /create` | `account_id: str`, `subject: str`, `participants: list[str]` |
| `CreateGroupResponse` | Response `POST /create` | `group_jid: str` |
| `JoinLinkRequest` | Request `POST /join-link` | `account_id: str`, `invite_link: str` |
| `JoinLinkResponse` | Response `POST /join-link` | `group_jid: str` |
| `ListGroupsResponse` | Response `GET /list` | `groups: list[dict]` (estrutura retornada pelo ZowPy) |

### 8.2 Router de grupos

```python
# app/routers/groups.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Any

from app.zowpy_app import get_manager

router = APIRouter(prefix="/groups", tags=["groups"])


# --- Request schemas ---

class CreateGroupRequest(BaseModel):
    """Body para criar grupo."""
    account_id: str = Field(..., description="ID da conta")
    subject: str = Field(..., description="Nome do grupo")
    participants: List[str] = Field(
        ...,
        description="Lista de JIDs ou números dos participantes iniciais"
    )


class JoinLinkRequest(BaseModel):
    """Body para entrar em grupo por link de convite."""
    account_id: str = Field(..., description="ID da conta")
    invite_link: str = Field(
        ...,
        description="Link de convite (ex: https://chat.whatsapp.com/xxxx)"
    )


# --- Response schemas ---

class CreateGroupResponse(BaseModel):
    """Resposta ao criar grupo."""
    group_jid: str = Field(..., description="JID do grupo criado (ex: 120363423929565689@g.us)")


class JoinLinkResponse(BaseModel):
    """Resposta ao entrar em grupo por link."""
    group_jid: str = Field(..., description="JID do grupo")


class ListGroupsResponse(BaseModel):
    """Resposta ao listar grupos."""
    groups: List[Any] = Field(
        ...,
        description="Lista de grupos (cada item com jid, subject, participants, etc.)"
    )


# --- Endpoints ---

@router.post("/create", response_model=CreateGroupResponse)
async def create_group(body: CreateGroupRequest) -> CreateGroupResponse:
    manager = get_manager()
    client = await manager.get_account(body.account_id)
    if not client:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    if not client._client or not client._client.is_connected():
        raise HTTPException(status_code=503, detail="Conta não conectada")
    try:
        group_jid = await client.create_group(body.subject, body.participants)
        return CreateGroupResponse(group_jid=group_jid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/join-link", response_model=JoinLinkResponse)
async def join_group_with_link(body: JoinLinkRequest) -> JoinLinkResponse:
    manager = get_manager()
    client = await manager.get_account(body.account_id)
    if not client:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    if not client._client or not client._client.is_connected():
        raise HTTPException(status_code=503, detail="Conta não conectada")
    try:
        group_jid = await client.join_group_with_link(body.invite_link)
        return JoinLinkResponse(group_jid=group_jid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=ListGroupsResponse)
async def list_groups(
    account_id: str,
    include_participants: bool = True
) -> ListGroupsResponse:
    manager = get_manager()
    client = await manager.get_account(account_id)
    if not client:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    if not client._client or not client._client.is_connected():
        raise HTTPException(status_code=503, detail="Conta não conectada")
    try:
        groups = await client.list_groups(include_participants=include_participants)
        return ListGroupsResponse(groups=groups)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 9. Rotas de proxy

### 9.1 Schemas Pydantic (proxy)

| Schema | Uso | Campos |
|--------|-----|--------|
| `SetProxyRequest` | Request `POST /set` | `account_id: str`, `proxy_string: str`, `proxy_type: Literal["http", "socks5"]` |
| `SetProxyResponse` | Response `POST /set` | `account_id: str`, `status: Literal["proxy set"]` |
| `RemoveProxyRequest` | Request `POST /remove` | `account_id: str` |
| `RemoveProxyResponse` | Response `POST /remove` | `account_id: str`, `status: Literal["proxy removed"]` |
| `ProxyStatusResponse` | Response `GET /status` | `account_id: str`, `has_proxy: bool`, `proxy: dict \| None` |

### 9.2 Router de proxy

```python
# app/routers/proxy.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Literal, Any, Dict

from app.zowpy_app import get_manager

router = APIRouter(prefix="/proxy", tags=["proxy"])


# --- Request schemas ---

class SetProxyRequest(BaseModel):
    """Body para configurar proxy."""
    account_id: str = Field(..., description="ID da conta")
    proxy_string: str = Field(
        ...,
        description="Formato: host:port ou host:port:username:password"
    )
    proxy_type: Literal["http", "socks5"] = Field(
        default="http",
        description="Tipo do proxy"
    )


class RemoveProxyRequest(BaseModel):
    """Body para remover proxy."""
    account_id: str = Field(..., description="ID da conta")


# --- Response schemas ---

class SetProxyResponse(BaseModel):
    """Resposta ao configurar proxy."""
    account_id: str = Field(..., description="ID da conta")
    status: Literal["proxy set"] = Field(default="proxy set", description="Status da operação")


class RemoveProxyResponse(BaseModel):
    """Resposta ao remover proxy."""
    account_id: str = Field(..., description="ID da conta")
    status: Literal["proxy removed"] = Field(
        default="proxy removed",
        description="Status da operação"
    )


class ProxyStatusResponse(BaseModel):
    """Resposta do status do proxy."""
    account_id: str = Field(..., description="ID da conta")
    has_proxy: bool = Field(..., description="True se há proxy configurado")
    proxy: Optional[Dict[str, Any]] = Field(
        None,
        description="Dados do proxy (host, port, type, etc.) ou None se não houver"
    )


# --- Endpoints ---

@router.post("/set", response_model=SetProxyResponse)
async def set_proxy(body: SetProxyRequest) -> SetProxyResponse:
    manager = get_manager()
    client = await manager.get_account(body.account_id)
    if not client:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    try:
        ok = await client.set_proxy(body.proxy_string, proxy_type=body.proxy_type)
        if not ok:
            raise HTTPException(status_code=400, detail="Falha ao configurar proxy (ex.: teste falhou)")
        return SetProxyResponse(account_id=body.account_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/remove", response_model=RemoveProxyResponse)
async def remove_proxy(body: RemoveProxyRequest) -> RemoveProxyResponse:
    manager = get_manager()
    client = await manager.get_account(body.account_id)
    if not client:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    await client.remove_proxy()
    return RemoveProxyResponse(account_id=body.account_id)


@router.get("/status", response_model=ProxyStatusResponse)
async def proxy_status(account_id: str) -> ProxyStatusResponse:
    manager = get_manager()
    client = await manager.get_account(account_id)
    if not client:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    has_proxy = await client.get_proxy_status()
    proxy_info = await client.get_proxy() if has_proxy else None
    return ProxyStatusResponse(account_id=account_id, has_proxy=has_proxy, proxy=proxy_info)
```

---

## 10. Webhooks / eventos (mensagens recebidas)

O ZowPy usa um **AsyncEventEmitter** internamente. Você pode registrar handlers `on_message`, `on_connected`, `on_disconnected` e encaminhar para um webhook HTTP (ou fila).

### 10.1 Cliente único com webhook

```python
# Exemplo: ao receber mensagem, envia POST para um webhook
import httpx

async def setup_webhook_for_account(client: ZowPyClient, webhook_url: str):
    @client.on_message
    async def on_msg(message: dict):
        try:
            async with httpx.AsyncClient() as http:
                await http.post(webhook_url, json=message, timeout=10.0)
        except Exception as e:
            logger.exception(f"Erro ao enviar webhook: {e}")

# Ao conectar a conta:
# await setup_webhook_for_account(client, "https://seu-servidor.com/webhook/whatsapp")
```

### 10.2 Server-Sent Events (SSE) para mensagens

Para entregar mensagens em tempo real via SSE. O endpoint retorna `StreamingResponse` (`text/event-stream`), não JSON. Cada evento `data` é um objeto JSON (mensagem ZowPy).

**Formato do evento SSE (exemplo):**

- `data: {"id": "...", "from": "...", "text": "...", "type": "text", ...}\n\n` — mensagem recebida
- `data: {"error": "account not found"}\n\n` — erro
- `: keepalive\n\n` — comentário para manter conexão viva

```python
# app/routers/events.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import asyncio
import json

from app.zowpy_app import get_manager

router = APIRouter(prefix="/events", tags=["events"])

async def stream_messages(account_id: str):
    manager = get_manager()
    client = await manager.get_account(account_id)
    if not client:
        yield f"data: {json.dumps({'error': 'account not found'})}\n\n"
        return
    queue: asyncio.Queue = asyncio.Queue()

    @client.on_message
    async def on_msg(message: dict):
        await queue.put(message)

    try:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield f"data: {json.dumps(msg)}\n\n"
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
    except asyncio.CancelledError:
        pass

@router.get("/{account_id}/messages/stream")
async def stream_account_messages(account_id: str):
    """Stream SSE de mensagens recebidas. Response: text/event-stream."""
    return StreamingResponse(
        stream_messages(account_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
```

---

## 11. Importação de contas (6-parts)

Antes de conectar, a conta precisa ser importada. Você pode expor um endpoint administrativo.

### 11.1 Schemas Pydantic (admin)

| Schema | Uso | Campos |
|--------|-----|--------|
| `ImportAccountRequest` | Request `POST /accounts/import` | `six_parts: str`, `env: str` |
| `ImportAccountResponse` | Response `POST /accounts/import` | `account_id: str`, `status: Literal["imported"]` |

### 11.2 Router admin

```python
# app/routers/admin.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

from zowpy.core.import_account import import_account_from_six_parts

router = APIRouter(prefix="/admin", tags=["admin"])


# --- Request schemas ---

class ImportAccountRequest(BaseModel):
    """Body para importar conta no formato 6-parts."""
    six_parts: str = Field(
        ...,
        description="String no formato: phone,pk1,sk1,pk2,sk2,sixth (separados por vírgula)"
    )
    env: str = Field(
        default="smb_android",
        description="Ambiente do dispositivo (ex: smb_android, android, ios)"
    )


# --- Response schemas ---

class ImportAccountResponse(BaseModel):
    """Resposta ao importar conta."""
    account_id: str = Field(..., description="ID da conta importada (número de telefone)")
    status: Literal["imported"] = Field(default="imported", description="Status da operação")


# --- Endpoints ---

@router.post("/accounts/import", response_model=ImportAccountResponse)
async def import_account(body: ImportAccountRequest) -> ImportAccountResponse:
    try:
        account_id = await import_account_from_six_parts(body.six_parts, env=body.env)
        return ImportAccountResponse(account_id=account_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 12. Aplicação completa (exemplo)

```python
# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.zowpy_app import init_zowpy, shutdown_zowpy
from app.routers import accounts, messages, groups, proxy, events, admin


class HealthResponse(BaseModel):
    """Resposta do health check."""
    status: str = Field(default="ok", description="Status do serviço")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_zowpy()
    yield
    await shutdown_zowpy()

app = FastAPI(title="ZowPy API", lifespan=lifespan)

app.include_router(accounts.router)
app.include_router(messages.router)
app.include_router(groups.router)
app.include_router(proxy.router)
app.include_router(events.router)
app.include_router(admin.router)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()
```

---

## 13. Tratamento de erros

- **`ConnectionError`**: falha ao conectar (ex.: sem conta importada, proxy inválido).
- **`ZowPyError`**: outros erros do ZowPy (ex.: timeout em `wait_for_message`).

Exemplo de handler global:

```python
from fastapi import Request
from fastapi.responses import JSONResponse

from zowpy.api.errors import ZowPyError

@app.exception_handler(ConnectionError)
async def connection_error_handler(request: Request, exc: ConnectionError):
    return JSONResponse(status_code=503, content={"detail": str(exc)})

@app.exception_handler(ZowPyError)
async def zowpy_error_handler(request: Request, exc: ZowPyError):
    return JSONResponse(status_code=500, content={"detail": str(exc)})
```

---

## 14. Boas práticas

1. **Sempre usar `AccountManager.shutdown`** no shutdown da API para desconectar todas as contas e finalizar o engine do banco.
2. **Evitar manter contas conectadas sem necessidade**; desconectar quando não houver uso.
3. **Proxy**: configurar com `set_proxy` antes de `connect`; logs indicam quando a conexão usa proxy.
4. **Importar conta** com `import_account_from_six_parts` antes da primeira conexão.
5. **Webhooks**: tratar falhas de entrega (retry, dead-letter) para não perder eventos.
6. **Um `AccountManager` por aplicação**; compartilhar entre rotas via estado global ou injeção de dependência.

---

## 15. Resumo dos schemas por endpoint

| Método | Rota | Request schema | Response schema |
|--------|------|----------------|-----------------|
| `GET` | `/health` | — | `HealthResponse` |
| `POST` | `/accounts/connect` | `ConnectRequest` | `ConnectResponse` |
| `POST` | `/accounts/disconnect` | `DisconnectRequest` | `DisconnectResponse` |
| `GET` | `/accounts/{account_id}/status` | — (path) | `AccountStatusResponse` |
| `POST` | `/messages/send/text` | `SendTextRequest` | `SendTextResponse` |
| `POST` | `/messages/send/image` | `SendImageRequest` | `SendImageResponse` |
| `POST` | `/groups/create` | `CreateGroupRequest` | `CreateGroupResponse` |
| `POST` | `/groups/join-link` | `JoinLinkRequest` | `JoinLinkResponse` |
| `GET` | `/groups/list` | — (query: `account_id`, `include_participants`) | `ListGroupsResponse` |
| `POST` | `/proxy/set` | `SetProxyRequest` | `SetProxyResponse` |
| `POST` | `/proxy/remove` | `RemoveProxyRequest` | `RemoveProxyResponse` |
| `GET` | `/proxy/status` | — (query: `account_id`) | `ProxyStatusResponse` |
| `GET` | `/events/{account_id}/messages/stream` | — (path) | `StreamingResponse` (SSE) |
| `POST` | `/admin/accounts/import` | `ImportAccountRequest` | `ImportAccountResponse` |

---

## 16. Referência rápida da API ZowPy

| Método | Descrição |
|--------|-----------|
| `AccountManager.add_account(account_id)` | Adiciona conta |
| `AccountManager.get_account(account_id)` | Obtém cliente |
| `AccountManager.remove_account(account_id)` | Remove e desconecta |
| `AccountManager.connect_all()` | Conecta todas |
| `AccountManager.disconnect_all()` | Desconecta todas |
| `AccountManager.shutdown()` | Desconecta, limpa e finaliza engine |
| `ZowPyClient.connect()` | Conecta conta |
| `ZowPyClient.disconnect()` | Desconecta conta |
| `ZowPyClient.send_text(to, text)` | Envia texto |
| `ZowPyClient.send_image(to, url, caption?)` | Envia imagem |
| `ZowPyClient.send_audio(to, url, ptt?)` | Envia áudio |
| `ZowPyClient.send_document(to, url)` | Envia documento |
| `ZowPyClient.send_sticker(to, url)` | Envia figurinha |
| `ZowPyClient.create_group(subject, participants)` | Cria grupo |
| `ZowPyClient.list_groups()` | Lista grupos |
| `ZowPyClient.join_group_with_link(link)` | Entra por link |
| `ZowPyClient.set_proxy(proxy_string, proxy_type?)` | Configura proxy |
| `ZowPyClient.remove_proxy()` | Remove proxy |
| `ZowPyClient.get_proxy_status()` | Verifica se tem proxy |
| `ZowPyClient.on_message(handler)` | Handler de mensagens |
| `ZowPyClient.wait_for_message(...)` | Aguarda mensagem com filtros |

---

## 17. Exemplo mínimo (um único arquivo)

Um exemplo executável está em `examples/fastapi_example.py`. Para rodar:

```bash
# Na raiz do projeto zowpy
uvicorn examples.fastapi_example:app --reload --host 0.0.0.0 --port 8000
```

Fluxo típico:

1. **POST /admin/accounts/import** — importar conta (6-parts).
2. **POST /accounts/connect** — adicionar conta ao manager e conectar.
3. **POST /messages/send/text** — enviar mensagem.
4. **POST /accounts/disconnect** — desconectar e remover do manager.

---

## 18. Executando a API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Documentação interativa: **http://localhost:8000/docs**.
