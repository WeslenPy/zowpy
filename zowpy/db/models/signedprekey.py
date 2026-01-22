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
    desc,
)
from sqlalchemy.orm import relationship
from zowpy.db.exceptions.exceptions import InvalidKeyIdException
from zowpy.db.common.model import BaseModel
from zowpy.db.config.base import Model



class SignedPreKey(Model,BaseModel):
    """
    Port of the `signed_prekeys` table from LiteSignedPreKeyStore.
    """

    __tablename__ = "signed_prekeys"

    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    prekey_id = Column(Integer, nullable=False)
    timestamp = Column(BigInteger, nullable=True)
    record = Column(LargeBinary(length=4294967295), nullable=False)

    account = relationship("Account", back_populates="signed_prekeys", lazy="raise")

    __table_args__ = (
        UniqueConstraint("account_id", "prekey_id", name="uq_signed_prekeys_account_prekey"),
    )



    @classmethod
    async def load_signed_prekey(cls, session: AsyncSession, account_id: int, prekey_id: int):

        try:
            query = select(cls.record).where(cls.account_id == account_id, cls.prekey_id == prekey_id)
            result = await session.execute(query)
            record = result.scalar()
            if not record:
                raise InvalidKeyIdException(f"No such signedprekeyrecord! {prekey_id}")
            from zowpy.axolotl.state.signedprekeyrecord import SignedPreKeyRecord
            return SignedPreKeyRecord(serialized=record)
        except InvalidKeyIdException:
            raise
        except Exception as e:
            logger.error(f"Error loading signed prekey: {e}")
            raise InvalidKeyIdException(f"No such signedprekeyrecord! {prekey_id}")

    @classmethod
    async def load_signed_prekeys(cls, session: AsyncSession, account_id: int):

        try:
            query = select(cls.record).where(cls.account_id == account_id).order_by(cls.prekey_id.asc())
            result = await session.execute(query)
            rows = result.all()
            from zowpy.axolotl.state.signedprekeyrecord import SignedPreKeyRecord
            return [SignedPreKeyRecord(serialized=row[0]) for row in rows]
        except Exception as e:
            logger.error(f"Error loading signed prekeys: {e}")
            return []

    @classmethod
    async def store_signed_prekey(cls, session: AsyncSession, account_id: int, prekey_id: int, timestamp: int, record: bytes):
        try:
            # Delete existing first
            await cls.remove_signed_prekey(session, account_id, prekey_id)
            
            new_signed_prekey = cls(
                account_id=account_id,
                prekey_id=prekey_id,
                timestamp=timestamp,
                record=record
            )
            session.add(new_signed_prekey)
            await session.commit()
        except Exception as e:
            logger.error(f"Error storing signed prekey: {e}")
            await session.rollback()
            raise

    @classmethod
    async def contains_signed_prekey(cls, session: AsyncSession, account_id: int, prekey_id: int):

        try:
            query = select(exists().where(cls.account_id == account_id, cls.prekey_id == prekey_id))
            result = await session.execute(query)
            return result.scalar() or False
        except Exception as e:
            logger.error(f"Error checking signed prekey existence: {e}")
            return False

    @classmethod
    async def remove_signed_prekey(cls, session: AsyncSession, account_id: int, prekey_id: int):
        
        try:
            query = delete(cls).where(cls.account_id == account_id, cls.prekey_id == prekey_id)
            await session.execute(query)
            await session.commit()
            return True
        except Exception as e:
            logger.error(f"Error removing signed prekey: {e}")
            await session.rollback()
            return False