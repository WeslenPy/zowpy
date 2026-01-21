from __future__ import annotations
from time import time
import hashlib
import base64

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
from zowpy.utils.tools import WATools
from zowpy.db.common.model import BaseModel
from zowpy.db.config.base import Model


class Broadcast(Model,BaseModel):
    """
    Port of the `broadcast` table from LiteBroadcastStore.
    """

    __tablename__ = "broadcasts"

    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    sender = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    jids = Column(Text, nullable=False)  # Comma‑separated list (kept as is for compatibility)
    phash = Column(String(64), nullable=False)
    bcid = Column(String(255), nullable=False)

    account = relationship("Account", back_populates="broadcasts", lazy="raise")

    __table_args__ = (
        Index("ix_broadcasts_account_bcid", "account_id", "bcid", unique=True),
        Index("ix_broadcasts_account_phash", "account_id", "phash", unique=True),
    )

    @staticmethod
    def phash_sha256(jids):
        jids = sorted(jids)
        h = hashlib.sha256()
        for jid in jids:
            h.update(jid.encode())
        return "2:" + base64.b64encode(h.digest()[:6]).decode()

    @classmethod
    async def add_broadcast(cls, session: AsyncSession, account_id: int, jids: str | list, sender_jid: str, name: str | None = None):

        # jids suporta string separada por vírgula ou array
        if isinstance(jids, str):
            jids = jids.split(",")

        new_jid = [WATools.fullJid(j) for j in jids]
        new_jid.append(WATools.fullJid(sender_jid))

        phash = cls.phash_sha256(new_jid)
        if name is None:
            name = ""

        # Tenta reutilizar broadcast existente por phash
        bcid, phash_result = await cls.find_broadcast_by_phash(session, account_id, phash)
        if bcid:
            return bcid, phash_result

        bcid = "%d@broadcast" % time()
        new_broadcast = cls(
            account_id=account_id,
            sender=WATools.fullJid(sender_jid),
            name=name,
            jids=",".join(new_jid),
            phash=phash,
            bcid=bcid,
        )
        session.add(new_broadcast)
        await session.commit()
        return bcid, phash

    @classmethod
    async def find_participants_by_bcid(cls, session: AsyncSession, account_id: int, bcid: str):

        try:
            query = select(cls.jids, cls.sender).where(cls.account_id == account_id, cls.bcid == bcid)
            result = await session.execute(query)
            row = result.first()
            if row:
                jids_str = row[0]
                sender = row[1]
                # Retorna array de jids excluindo o sender
                jids = [item for item in jids_str.split(",") if item != sender]
                return jids
            return None
        except Exception as e:
            logger.error(f"Error finding participants by bcid: {e}")
            return None

    @classmethod
    async def find_broadcast_by_phash(cls, session: AsyncSession, account_id: int, phash: str):

        try:
            query = select(cls.bcid).where(cls.account_id == account_id, cls.phash == phash)
            result = await session.execute(query)
            bcid = result.scalar()
            if bcid:
                return bcid, phash
            return None, None
        except Exception as e:
            logger.error(f"Error finding broadcast by phash: {e}")
            return None, None
