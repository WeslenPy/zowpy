"""
Exemplo mínimo de integração ZowPy + FastAPI.

Execute:
    uvicorn examples.fastapi_example:app --reload --host 0.0.0.0 --port 8000

Depois acesse http://localhost:8000/docs para a documentação interativa.

Fluxo:
  1. POST /admin/accounts/import — importar conta (body: {"six_parts": "...", "env": "smb_android"})
  2. POST /accounts/connect — conectar (body: {"account_id": "201208868278"})
  3. POST /messages/send/text — enviar mensagem (body: {"account_id": "...", "to": "...", "text": "..."})
  4. POST /accounts/disconnect — desconectar (body: {"account_id": "..."})
"""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from zowpy import AccountManager
from zowpy.db.config import create_db
from zowpy.db.config.engine import AsyncSessionMaker

# Estado global
_manager: Optional[AccountManager] = None


def get_manager() -> AccountManager:
    if _manager is None:
        raise RuntimeError("AccountManager não inicializado")
    return _manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _manager
    await create_db()
    _manager = AccountManager(session_maker=AsyncSessionMaker)
    yield
    if _manager:
        await _manager.shutdown()
        _manager = None


app = FastAPI(title="ZowPy API (exemplo)", lifespan=lifespan)


# --- Schemas ---


class ImportAccountRequest(BaseModel):
    six_parts: str
    env: str = "smb_android"


class AccountIdRequest(BaseModel):
    account_id: str


class SendTextRequest(BaseModel):
    account_id: str
    to: str
    text: str


# --- Admin ---


@app.post("/admin/accounts/import")
async def import_account(body: ImportAccountRequest):
    """Importa conta a partir do formato 6-parts."""
    try:
        from zowpy.core.import_account import import_account_from_six_parts
        account_id = await import_account_from_six_parts(body.six_parts, env=body.env)
        return {"account_id": account_id, "status": "imported"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Accounts ---


@app.post("/accounts/connect")
async def connect_account(body: AccountIdRequest):
    """Adiciona conta ao manager e conecta ao WhatsApp."""
    manager = get_manager()
    client = await manager.add_account(body.account_id)
    await client.connect()
    return {"account_id": body.account_id, "status": "connected"}


@app.post("/accounts/disconnect")
async def disconnect_account(body: AccountIdRequest):
    """Desconecta e remove a conta do manager."""
    manager = get_manager()
    client = await manager.get_account(body.account_id)
    if not client:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    await manager.remove_account(body.account_id)
    return {"account_id": body.account_id, "status": "disconnected"}


@app.get("/accounts/{account_id}/status")
async def account_status(account_id: str):
    """Retorna se a conta está conectada."""
    manager = get_manager()
    client = await manager.get_account(account_id)
    if not client:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    connected = client._client is not None and client._client.is_connected()
    return {"account_id": account_id, "connected": connected}


# --- Messages ---


@app.post("/messages/send/text")
async def send_text(body: SendTextRequest):
    """Envia mensagem de texto. 'to' pode ser número ou JID (ex: 120363423929565689@g.us)."""
    manager = get_manager()
    client = await manager.get_account(body.account_id)
    if not client:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    if not client._client or not client._client.is_connected():
        raise HTTPException(status_code=503, detail="Conta não conectada")
    try:
        message_id = await client.send_text(body.to, body.text)
        return {"message_id": message_id, "to": body.to}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Health ---


@app.get("/health")
async def health():
    return {"status": "ok"}
