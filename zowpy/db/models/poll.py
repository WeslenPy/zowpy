from __future__ import annotations
import hashlib

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

class Poll(Model,BaseModel):
    """
    Port of the `poll` table from LitePollStore.
    """

    __tablename__ = "polls"

    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    poll_msg_id = Column(BigInteger, nullable=False)
    enc_key = Column(LargeBinary, nullable=False)
    name = Column(String(255), nullable=True)

    account = relationship("Account", back_populates="polls", lazy="raise")
    options = relationship(
        "PollOption",
        back_populates="poll",
        cascade="all, delete-orphan",
        lazy="raise_on_sql",
    )

    __table_args__ = (
        Index("ix_polls_account_poll_msg", "account_id", "poll_msg_id", unique=True),
    )

    @classmethod
    async def delete_poll(cls, session: AsyncSession, account_id: int, poll_msg_id: int):

        try:
            # Delete via cascade - deleting poll will delete options
            query = select(cls).where(
                cls.account_id == account_id,
                cls.poll_msg_id == poll_msg_id
            )
            result = await session.execute(query)
            poll = result.scalar_one_or_none()
            if poll:
                await session.delete(poll)
                await session.commit()
        except Exception as e:
            logger.error(f"Error deleting poll: {e}")
            await session.rollback()
            raise

    @classmethod
    async def store_poll(cls, session: AsyncSession, account_id: int, poll_msg_id: int, name: str, enc_key: bytes, options: list[str]):

        try:
            from zowpy.db.models.polloption import PollOption
            
            poll = cls(
                account_id=account_id,
                poll_msg_id=poll_msg_id,
                enc_key=enc_key,
                name=name
            )
            session.add(poll)
            await session.flush()  # so poll.id is available

            for item in options:
                opt_hash = hashlib.sha256(item.encode()).digest()
                opt = PollOption(
                    poll_id=poll.id,
                    option_name=item,
                    option_sha256=opt_hash
                )
                session.add(opt)

            await session.commit()
        except Exception as e:
            logger.error(f"Error storing poll: {e}")
            await session.rollback()
            raise

    @classmethod
    async def decrypt_options(cls, session: AsyncSession, account_id: int, poll_msg_id: int, option_sha256_list: list[bytes]):

        try:
            from zowpy.db.models.polloption import PollOption
            
            query = select(cls).where(
                cls.account_id == account_id,
                cls.poll_msg_id == poll_msg_id
            )
            result = await session.execute(query)
            poll = result.scalar_one_or_none()
            if not poll:
                return ["ITEM ERROR"] * len(option_sha256_list)

            options = []
            for sha256_item in option_sha256_list:
                opt_query = select(PollOption.option_name).where(
                    PollOption.poll_id == poll.id,
                    PollOption.option_sha256 == sha256_item
                )
                opt_result = await session.execute(opt_query)
                opt_name = opt_result.scalar()
                if opt_name:
                    options.append(opt_name)
                else:
                    options.append("ITEM ERROR")
            return options
        except Exception as e:
            logger.error(f"Error decrypting options: {e}")
            return ["ITEM ERROR"] * len(option_sha256_list)

    @classmethod
    async def get_poll_enc_key(cls, session: AsyncSession, account_id: int, poll_msg_id: int):

        try:
            query = select(cls.enc_key).where(
                cls.account_id == account_id,
                cls.poll_msg_id == poll_msg_id
            )
            result = await session.execute(query)
            enc_key = result.scalar()
            return enc_key
        except Exception as e:
            logger.error(f"Error getting poll enc key: {e}")
            return None