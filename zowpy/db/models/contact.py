from __future__ import annotations
from time import time
from typing import Optional

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

    jid = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    lid = Column(String(255), nullable=True)

    pushname = Column(String(255), nullable=True)
    profile_picture_url = Column(String(255), nullable=True)
    business_name = Column(String(255), nullable=True)
    verified_name = Column(String(255), nullable=True)
    verified_level = Column(String(255), nullable=True)
    notify = Column(String(255), nullable=True)
    sender_pn = Column(String(255), nullable=True)

    timestamp = Column(BigInteger, nullable=False)

    account = relationship("Account", back_populates="contacts", lazy="raise")

    __table_args__ = (
        Index("ix_contacts_account_jid", "account_id", "jid", unique=True),
    )

    @classmethod
    async def add_contact(cls, 
        session: AsyncSession, 
        account_id: int, 
        jid: str, 
        name: str | None = None,
        lid: str | None = None,
        pushname: str | None = None,
        profile_picture_url: str | None = None,
        business_name: str | None = None,
        verified_name: str | None = None,
        verified_level: str | None = None,
        notify: str | None = None,
        sender_pn: str | None = None,
        ):

        if not (jid.endswith(YowConstants.WHATSAPP_SERVER) or jid.endswith(YowConstants.LID_SUFFIX)):
            return None

        if name is None:
            name = ""

        if lid is None:
            lid = ""

        if not await cls.find_contact(session, account_id, jid):
            new_contact = cls(
                account_id=account_id,
                jid=jid,
                name=name,
                lid=lid,
                timestamp=int(time()),
                pushname=pushname,
                profile_picture_url=profile_picture_url,
                business_name=business_name,
                verified_name=verified_name,
                verified_level=verified_level,
                notify=notify,
                sender_pn=sender_pn,
            )
            session.add(new_contact)
            await session.commit()
            return jid
        return None


    @classmethod
    async def update_contact(cls, session: AsyncSession, account_id: int, jid: str, name: Optional[str] = None, lid: Optional[str] = None):
        if not await cls.find_contact(session, account_id, jid):
            return None
        contact = await cls.find_contact(session, account_id, jid)
        contact.name = name
        contact.lid = lid
        session.add(contact)
        await session.commit()
        return jid


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