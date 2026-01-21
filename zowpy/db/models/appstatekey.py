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
    desc,
)
from sqlalchemy.orm import relationship
from zowpy.db.common.model import BaseModel
from zowpy.db.config.base import Model


class AppStateKey(Model,BaseModel):
    """
    Port of the `app_state_keys` table from LiteAppStateStore.
    """

    __tablename__ = "app_state_keys"

    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    key_id = Column(LargeBinary, nullable=False)
    key_data = Column(LargeBinary, nullable=False)
    fingerprint = Column(LargeBinary, nullable=True)
    timestamp = Column(BigInteger, nullable=False)

    account = relationship("Account", back_populates="app_state_keys", lazy="raise")

    __table_args__ = (
        Index("ix_app_state_keys_account_key_id", "account_id", "key_id", unique=True),
    )

    @classmethod
    async def add_app_state_keys(cls, session: AsyncSession, account_id: int, keys):

        try:
            now = int(time())
            for key in keys:
                new_key = cls(
                    account_id=account_id,
                    key_id=key.key_id.key_id,
                    key_data=key.key_data.key_data,
                    fingerprint=None,
                    timestamp=now
                )
                session.add(new_key)
            await session.commit()
        except Exception as e:
            logger.error(f"Error adding app state keys: {e}")
            await session.rollback()
            raise

    @classmethod
    async def get_one_app_state_key(cls, session: AsyncSession, account_id: int):

        try:
            query = select(cls).where(
                cls.account_id == account_id
            ).order_by(desc(cls.timestamp))
            result = await session.execute(query)
            row = result.first()
            if not row:
                return None
            
            key_obj = row[0]
            from zowpy.protocol.historysync.attributes import (
                AppStateSyncKeyAttribute,
                AppStateSyncKeyIdAttribute,
                AppStateSyncKeyDataAttribute,
            )
            return AppStateSyncKeyAttribute(
                key_id=AppStateSyncKeyIdAttribute(key_id=key_obj.key_id),
                key_data=AppStateSyncKeyDataAttribute(
                    key_data=key_obj.key_data,
                    fingerprint=key_obj.fingerprint,
                    timestamp=key_obj.timestamp
                )
            )
        except Exception as e:
            logger.error(f"Error getting one app state key: {e}")
            return None

    @classmethod
    async def get_app_state_key(cls, session: AsyncSession, account_id: int, key_id: bytes):

        try:
            query = select(cls).where(
                cls.account_id == account_id,
                cls.key_id == key_id
            )
            result = await session.execute(query)
            row = result.scalar_one_or_none()
            if not row:
                return None
            
            from zowpy.protocol.historysync.attributes import (
                AppStateSyncKeyAttribute,
                AppStateSyncKeyIdAttribute,
                AppStateSyncKeyDataAttribute,
            )
            return AppStateSyncKeyAttribute(
                key_id=AppStateSyncKeyIdAttribute(key_id=row.key_id),
                key_data=AppStateSyncKeyDataAttribute(
                    key_data=row.key_data,
                    fingerprint=row.fingerprint,
                    timestamp=row.timestamp
                )
            )
        except Exception as e:
            logger.error(f"Error getting app state key: {e}")
            return None

    @classmethod
    async def delete_app_state_key(cls, session: AsyncSession, account_id: int, key_id: bytes):

        try:
            query = delete(cls).where(
                cls.account_id == account_id,
                cls.key_id == key_id
            )
            await session.execute(query)
            await session.commit()
        except Exception as e:
            logger.error(f"Error deleting app state key: {e}")
            await session.rollback()
            raise
