from __future__ import annotations

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
    exists,
)
from sqlalchemy.orm import relationship
from zowpy.db.common.model import BaseModel
from zowpy.db.config.base import Model

class SessionKey(Model,BaseModel):
    """
    Port of the `sessions` table from LiteSessionStore.
    """

    __tablename__ = "sessions"

    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    recipient_id = Column(BigInteger, nullable=False)
    recipient_type = Column(Integer, nullable=False, default=0)
    device_id = Column(Integer, nullable=False)
    record = Column(LargeBinary(length=4294967295), nullable=False)
    timestamp = Column(BigInteger, nullable=True)

    account = relationship("Account", back_populates="sessions", lazy="raise")

    __table_args__ = (
        Index("ix_sessions_account_recipient_device", "account_id", "recipient_id", "device_id", unique=True),
    )

    @classmethod
    async def load_session(cls, session: AsyncSession, account_id: int, recipient_id: int, device_id: int):

        try:
            query = select(cls.record).where(
                cls.account_id == account_id,
                cls.recipient_id == recipient_id,
                cls.device_id == device_id
            )
            result = await session.execute(query)
            record = result.scalar()
            if record:
                from zowpy.axolotl.state.sessionrecord import SessionRecord
                return SessionRecord(serialized=record)
            from zowpy.axolotl.state.sessionrecord import SessionRecord
            return SessionRecord()
        except Exception as e:
            logger.error(f"Error loading session: {e}")
            from zowpy.axolotl.state.sessionrecord import SessionRecord
            return SessionRecord()

    @classmethod
    async def get_sub_device_sessions(cls, session: AsyncSession, account_id: int, recipient_id: int):

        try:
            query = select(cls.device_id).where(
                cls.account_id == account_id,
                cls.recipient_id == recipient_id
            )
            result = await session.execute(query)
            rows = result.all()
            return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"Error getting sub device sessions: {e}")
            return []

    @classmethod
    async def store_session(cls, session: AsyncSession, account_id: int, recipient_id: int, device_id: int, record: bytes):
        try:
            # Delete existing first
            await cls.delete_session(session, account_id, recipient_id, device_id)
            
            new_session = cls(
                account_id=account_id,
                recipient_id=recipient_id,
                recipient_type=0,
                device_id=device_id,
                record=record
            )
            session.add(new_session)
            await session.commit()
        except Exception as e:
            logger.error(f"Error storing session: {e}")
            await session.rollback()
            raise

    @classmethod
    async def contains_session(cls, session: AsyncSession, account_id: int, recipient_id: int, device_id: int):

        try:
            query = select(exists().where(
                cls.account_id == account_id,
                cls.recipient_id == recipient_id,
                cls.device_id == device_id
            ))
            result = await session.execute(query)
            return result.scalar() or False
        except Exception as e:
            logger.error(f"Error checking session existence: {e}")
            return False

    @classmethod
    async def delete_session(cls, session: AsyncSession, account_id: int, recipient_id: int, device_id: int):

        try:
            query = delete(cls).where(
                cls.account_id == account_id,
                cls.recipient_id == recipient_id,
                cls.device_id == device_id
            )
            await session.execute(query)
            await session.commit()
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            await session.rollback()
            raise

    @classmethod
    async def delete_all_sessions(cls, session: AsyncSession, account_id: int, recipient_id: int):

        try:
            query = delete(cls).where(
                cls.account_id == account_id,
                cls.recipient_id == recipient_id
            )
            await session.execute(query)
            await session.commit()
        except Exception as e:
            logger.error(f"Error deleting all sessions: {e}")
            await session.rollback()
            raise

    @classmethod
    async def get_all_accounts(cls, session: AsyncSession, account_id: int, recipient_id: int):

        try:
            query = select(
                cls.recipient_id,
                cls.recipient_type,
                cls.device_id
            ).where(
                cls.account_id == account_id,
                cls.recipient_id == recipient_id
            )
            result = await session.execute(query)
            rows = result.all()
            return ["%d.%d:%d" % (r[0], r[1], r[2]) for r in rows]
        except Exception as e:
            logger.error(f"Error getting all accounts: {e}")
            return []
