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


class TrustedContact(Model,BaseModel):
    """
    Port of the `trusted_contact` table from LiteTrustedContactStore.
    """

    __tablename__ = "trusted_contacts"

    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    jid = Column(String(255), nullable=False)
    incoming_tc_token = Column(LargeBinary(length=4294967295), nullable=False)
    timestamp = Column(BigInteger, nullable=False)

    account = relationship("Account", back_populates="trusted_contacts", lazy="raise")

    __table_args__ = (
        Index("ix_trusted_contacts_account_jid", "account_id", "jid", unique=True),
    )



    @classmethod
    async def update_trusted_contact(cls, session: AsyncSession, account_id: int, jid: str, tctoken: None | bytes = None):

        if not (jid.endswith(YowConstants.WHATSAPP_SERVER) or jid.endswith(YowConstants.LID_SUFFIX)):
            return False

        if tctoken is None:
            return False

        await cls.remove_trusted_contact(session, account_id, jid)

        new_trusted_contact = cls(account_id=account_id, jid=jid, incoming_tc_token=tctoken,timestamp=int(time()))
        session.add(new_trusted_contact)
        await session.commit()
        return True


    @classmethod
    async def get_tc_token(cls, session: AsyncSession, account_id: int, jid: str, lid: str=None):
        
        try:
            query = select(cls.incoming_tc_token).where(cls.account_id == account_id, cls.jid.in_([jid, lid]))
            result =  await session.execute(query)
            return result.scalar()
            
        except Exception as e:
            logger.error(f"Error getting trusted contact token: {e}")
            return None
    

    @classmethod
    async def remove_trusted_contact(cls, session: AsyncSession, account_id: int, jid: str):
        
        try:
            query = delete(cls).where(cls.account_id == account_id, cls.jid == jid)
            await session.execute(query)
            await session.commit()
            return True
        except Exception as e:
            logger.error(f"Error removing trusted contact: {e}")
            await session.rollback()
            return False