

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
import datetime as dt
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    Index,
    select,
)
from sqlalchemy.orm import load_only, relationship
from zowpy.db.common.model import BaseModel
from zowpy.db.config.base import Model

class Account(Model,BaseModel):
    """
    Represents a WhatsApp account (one phone number).

    This is the root entity used to tie together all Axolotl / protocol
    data that previously lived in separate axolotl.db files per account.
    """

    __tablename__ = "accounts"

    phone = Column(String(32), unique=True, nullable=False, index=True)
    pushname = Column(String(255), nullable=True)
    env = Column(String(32), nullable=True)  # android, smb_android, ios, smb_ios, ...

    # Status fields
    is_logged_in = Column(Boolean, nullable=False, default=False, index=True)
    master = Column(Boolean, nullable=False, default=False)
    has_restriction = Column(Boolean, nullable=False, default=False, index=True)
    is_initialized = Column(Boolean, nullable=False, default=False, index=True)

    # Proxy configuration
    proxy_host = Column(String(255), nullable=True)
    proxy_type = Column(String(255), nullable=True, default="http")
    proxy_port = Column(Integer, nullable=True)
    proxy_username = Column(String(255), nullable=True)
    proxy_password = Column(String(255), nullable=True)

    # Relationships
    identities = relationship(
        "Identity",
        back_populates="account",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    prekeys = relationship(
        "PreKey",
        back_populates="account",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    signed_prekeys = relationship(
        "SignedPreKey",
        back_populates="account",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    sessions = relationship(
        "SessionKey",
        back_populates="account",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    sender_keys = relationship(
        "SenderKey",
        back_populates="account",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    polls = relationship(
        "Poll",
        back_populates="account",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    app_state_keys = relationship(
        "AppStateKey",
        back_populates="account",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    contacts = relationship(
        "Contact",
        back_populates="account",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    broadcasts = relationship(
        "Broadcast",
        back_populates="account",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    trusted_contacts = relationship(
        "TrustedContact",
        back_populates="account",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    task_msgs = relationship(
        "TaskMsg",
        back_populates="account",
        cascade="all, delete-orphan",
        lazy="raise",
    )

 
    account_state = relationship(
        "AccountState",
        back_populates="account",
        cascade="all, delete-orphan",
        lazy="raise",
    )



    @classmethod
    async def get_env_by_phone(cls, session: AsyncSession, phone: str) -> str | None:
        """
        Busca o ambiente de uma conta pelo número de telefone.
        """
        result = await session.execute(select(cls).options(load_only(cls.env)).filter_by(phone=phone))
        account = result.scalar_one_or_none()
        if account:
            return account.env
        return None



    @classmethod
    async def get_by_phone(cls, session: AsyncSession, phone: str) -> Account:
        """
        Busca uma conta pelo número de telefone.
        """
        result = await session.execute(select(cls).filter_by(phone=phone))
        return result.scalar_one_or_none()



    @classmethod
    async def get_or_create_account(cls, session: AsyncSession, phone: str) -> Account:
        """
        Busca ou cria uma conta com o número de telefone fornecido.
        """
        account = await cls.get_by_phone(session, phone)
        if account is None:
            account = cls(phone=phone)
            session.add(account)
            await session.commit()
            await session.refresh(account)
        return account