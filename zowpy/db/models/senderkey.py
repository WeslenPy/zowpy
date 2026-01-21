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
    select,
)
from sqlalchemy.orm import relationship
from zowpy.db.common.model import BaseModel
from zowpy.db.config.base import Model


class SenderKey(Model,BaseModel):
    """
    Port of the `sender_keys` table from LiteSenderKeyStore.
    """

    __tablename__ = "sender_keys"

    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    group_id = Column(String(255), nullable=False)
    sender_id = Column(String(255), nullable=False)
    record = Column(LargeBinary, nullable=False)

    account = relationship("Account", back_populates="sender_keys", lazy="raise")

    __table_args__ = (
        Index("ix_sender_keys_account_group_sender", "account_id", "group_id", "sender_id", unique=True),
    )

    @classmethod
    async def store_sender_key(cls, session: AsyncSession, account_id: int, group_id: str, sender_id: str, record: bytes):

        try:
            # Try to find existing record
            query = select(cls).where(
                cls.account_id == account_id,
                cls.group_id == group_id,
                cls.sender_id == sender_id
            )
            result = await session.execute(query)
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update existing
                existing.record = record
            else:
                # Create new
                new_sender_key = cls(
                    account_id=account_id,
                    group_id=group_id,
                    sender_id=sender_id,
                    record=record
                )
                session.add(new_sender_key)
            
            await session.commit()
        except Exception as e:
            logger.error(f"Error storing sender key: {e}")
            await session.rollback()
            raise

    @classmethod
    async def load_sender_key(cls, session: AsyncSession, account_id: int, group_id: str, sender_id: str):

        try:
            query = select(cls.record).where(
                cls.account_id == account_id,
                cls.group_id == group_id,
                cls.sender_id == sender_id
            )
            result = await session.execute(query)
            record = result.scalar()
            if not record:
                from zowpy.axolotl.groups.state.senderkeyrecord import SenderKeyRecord
                return SenderKeyRecord()
            from zowpy.axolotl.groups.state.senderkeyrecord import SenderKeyRecord
            return SenderKeyRecord(serialized=record)
        except Exception as e:
            logger.error(f"Error loading sender key: {e}")
            from zowpy.axolotl.groups.state.senderkeyrecord import SenderKeyRecord
            return SenderKeyRecord()
