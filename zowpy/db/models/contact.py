from __future__ import annotations
from time import time

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base
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
    delete,
    select,
)
from sqlalchemy.orm import relationship
from zowpy.utils.constants import YowConstants
from zowpy.db.common.model import BaseModel
from zowpy.db.config.base import Model

class Contact(Model,BaseModel):
    """
    Port of the `contact` table from LiteContactStore.
    """

    __tablename__ = "contacts"

    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=True)
    jid = Column(String(255), nullable=False)
    timestamp = Column(BigInteger, nullable=False)

    account = relationship("Account", back_populates="contacts", lazy="raise")

    __table_args__ = (
        Index("ix_contacts_account_jid", "account_id", "jid", unique=True),
    )

    @classmethod
    async def add_contact(cls, session: AsyncSession, account_id: int, jid: str, name: str | None = None):

        if not (jid.endswith(YowConstants.WHATSAPP_SERVER) or jid.endswith(YowConstants.LID_SUFFIX)):
            return None

        if name is None:
            name = ""

        if not await cls.find_contact(session, account_id, jid):
            new_contact = cls(
                account_id=account_id,
                jid=jid,
                name=name,
                timestamp=int(time())
            )
            session.add(new_contact)
            await session.commit()
            return jid
        return None

    @classmethod
    async def find_contact(cls, session: AsyncSession, account_id: int, jid: str):

        if not (jid.endswith(YowConstants.WHATSAPP_SERVER) or jid.endswith(YowConstants.LID_SUFFIX)):
            return False

        try:
            query = select(cls.jid).where(cls.account_id == account_id, cls.jid == jid)
            result = await session.execute(query)
            return result.scalar() is not None
        except Exception as e:
            logger.error(f"Error finding contact: {e}")
            return False

    @classmethod
    async def is_new_contact(cls, session: AsyncSession, account_id: int, jid: str):
        if jid.endswith(f"@{YowConstants.WHATSAPP_SERVER}") or jid.endswith(f"@{YowConstants.WHATSAPP_GROUP_SERVER}"):
            return not await cls.find_contact(session, account_id, jid)
        return False

    @classmethod
    async def remove_contact(cls, session: AsyncSession, account_id: int, jid: str):

        try:
            query = delete(cls).where(cls.account_id == account_id, cls.jid == jid)
            await session.execute(query)
            await session.commit()
            return True
        except Exception as e:
            logger.error(f"Error removing contact: {e}")
            await session.rollback()
            return False

    @classmethod
    async def get_all_contacts(cls, session: AsyncSession, account_id: int):

        try:
            query = select(cls.jid).where(cls.account_id == account_id)
            result = await session.execute(query)
            rows = result.all()
            return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"Error getting all contacts: {e}")
            return []