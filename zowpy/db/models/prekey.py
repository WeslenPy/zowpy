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
    insert,
    select,
    update,
    func,
    exists,
)
from sqlalchemy.orm import relationship
from zowpy.db.common.model import BaseModel
from zowpy.db.config.base import Model
from zowpy.db.exceptions.exceptions import InvalidKeyIdException



class PreKey(Model,BaseModel):
    """
    Port of the `prekeys` table from LitePreKeyStore.
    """

    __tablename__ = "prekeys"

    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    prekey_id = Column(Integer, nullable=False)
    sent_to_server = Column(Boolean, nullable=True)
    record = Column(LargeBinary, nullable=False)

    account = relationship("Account", back_populates="prekeys", lazy="raise")

    __table_args__ = (
        UniqueConstraint("account_id", "prekey_id", name="uq_prekeys_account_prekey"),
    )

    @classmethod
    async def load_prekey(cls, session: AsyncSession, account_id: int, prekey_id: int):

        try:
            query = select(cls.record).where(cls.account_id == account_id, cls.prekey_id == prekey_id)
            result = await session.execute(query)
            record = result.scalar()
            if not record:
                raise InvalidKeyIdException("No such prekeyrecord!")
            from zowpy.axolotl.state.prekeyrecord import PreKeyRecord
            return PreKeyRecord(serialized=record)
        except InvalidKeyIdException:
            raise
        except Exception as e:
            logger.error(f"Error loading prekey: {e}")
            raise InvalidKeyIdException("No such prekeyrecord!")

    @classmethod
    async def load_unsent_pending_prekeys(cls, session: AsyncSession, account_id: int):

        try:
            query = select(cls.record).where(
                cls.account_id == account_id,
                (cls.sent_to_server.is_(None)) | (cls.sent_to_server == False)
            )
            result = await session.execute(query)
            rows = result.all()
            from zowpy.axolotl.state.prekeyrecord import PreKeyRecord
            return [PreKeyRecord(serialized=row[0]) for row in rows]
        except Exception as e:
            logger.error(f"Error loading unsent pending prekeys: {e}")
            return []

    @classmethod
    async def set_as_sent(cls, session: AsyncSession, account_id: int, prekey_ids: list[int]):

        if not prekey_ids:
            return

        try:
            query = update(cls).where(
                cls.account_id == account_id,
                cls.prekey_id.in_(prekey_ids)
            ).values(sent_to_server=True)
            await session.execute(query)
            await session.commit()
        except Exception as e:
            logger.error(f"Error setting prekeys as sent: {e}")
            await session.rollback()
            raise


    @classmethod 
    async def store_prekeys_bulk(cls, session: AsyncSession, account_id: int, prekeys: list):
        """
        Armazena múltiplos prekeys em uma única transação (bulk insert).
        
        Args:
            prekeys: Lista de tuplas (preKeyId, preKeyRecord)
        """
        if not prekeys:
            return
        
        try:
            logger.debug(f"storePreKeys: storing {len(prekeys)} prekeys in bulk")
            rows = []

            for preKeyId, preKeyRecord in prekeys:
                record_data = preKeyRecord.serialize()
                rows.append({
                    'account_id': account_id,
                    'prekey_id': preKeyId,
                    'record': bytes(record_data),
                })
            
            # Bulk insert usando insert().values() (mais eficiente)
            await session.execute(
                insert(cls).values(rows)
            )

            await session.commit()
            
            logger.info(f"storePreKeys: successfully stored {len(prekeys)} prekeys in bulk")
        except Exception as e:
            await session.rollback()
            logger.error(f"storePreKeys: error storing {len(prekeys)} prekeys: {e}", exc_info=True)
            raise

    @classmethod
    async def load_pending_prekeys(cls, session: AsyncSession, account_id: int):

        try:
            query = select(cls.record).where(cls.account_id == account_id)
            result = await session.execute(query)
            rows = result.all()
            from zowpy.axolotl.state.prekeyrecord import PreKeyRecord
            return [PreKeyRecord(serialized=row[0]) for row in rows]
        except Exception as e:
            logger.error(f"Error loading pending prekeys: {e}")
            return []

    @classmethod
    async def store_prekey(cls, session: AsyncSession, account_id: int, prekey_id: int, record: bytes):

        try:
            new_prekey = cls(
                account_id=account_id,
                prekey_id=prekey_id,
                record=record
            )
            session.add(new_prekey)
            await session.commit()
        except Exception as e:
            logger.error(f"Error storing prekey: {e}")
            await session.rollback()
            raise

    @classmethod
    async def contains_prekey(cls, session: AsyncSession, account_id: int, prekey_id: int):

        try:
            query = select(exists().where(cls.account_id == account_id, cls.prekey_id == prekey_id))
            result = await session.execute(query)
            return result.scalar() or False
        except Exception as e:
            logger.error(f"Error checking prekey existence: {e}")
            return False

    @classmethod
    async def remove_prekey(cls, session: AsyncSession, account_id: int, prekey_id: int):

        try:
            query = delete(cls).where(cls.account_id == account_id, cls.prekey_id == prekey_id)
            await session.execute(query)
            await session.commit()
        except Exception as e:
            logger.error(f"Error removing prekey: {e}")
            await session.rollback()
            raise

    @classmethod
    async def load_max_prekey_id(cls, session: AsyncSession, account_id: int):

        try:
            query = select(func.max(cls.prekey_id)).where(cls.account_id == account_id)
            result = await session.execute(query)
            max_id = result.scalar()
            return 0 if max_id is None else int(max_id)
        except Exception as e:
            logger.error(f"Error loading max prekey id: {e}")
            return 0

    @classmethod
    async def clear_prekeys(cls, session: AsyncSession, account_id: int):

        try:
            query = delete(cls).where(cls.account_id == account_id)
            await session.execute(query)
            await session.commit()
        except Exception as e:
            logger.error(f"Error clearing prekeys: {e}")
            await session.rollback()
            raise
