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

class LidMap(Model,BaseModel):
    """
    Map of phone numbers to LID.
    """

    __tablename__ = "lid_map"

    pn = Column(String(255), nullable=False, unique=True, index=True)
    lid = Column(String(255), nullable=False)



    @classmethod
    async def add_lid_mapping(cls, session: AsyncSession, jid: str, lid: str):

        if not await cls.get_lid_mapping_by_jid(session, jid):
            new_lid_mapping = cls(
                pn=jid,
                lid=lid
            )
            session.add(new_lid_mapping)
            await session.commit()
            return jid


    @classmethod
    async def get_lid_mapping_by_jid(cls, session: AsyncSession, jid: str):
        """Return the LID string for the given JID, or None if not in map."""
        query = select(cls.lid).where(cls.pn == jid)
        result = await session.execute(query)
        return result.scalar_one_or_none()


    @classmethod
    async def delete_lid_mapping(cls, session: AsyncSession, jid: str):
        query = delete(cls).where(cls.pn == jid)
        await session.execute(query)
        await session.commit()
        return jid

    @classmethod
    async def get_lid_mapping_by_lid(cls, session: AsyncSession, lid: str):
        query = select(cls.pn,cls.lid).where(cls.lid == lid)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def get_all_lid_mapping(cls, session: AsyncSession):
        query = select(cls.pn,cls.lid)
        result = await session.execute(query)
        return result.scalars().all()