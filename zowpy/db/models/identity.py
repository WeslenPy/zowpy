from __future__ import annotations

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
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
from zowpy.db.common.model import BaseModel
from zowpy.db.config.base import Model

class Identity(Model,BaseModel):
    """
    Port of the `identities` table from LiteIdentityKeyStore, with an
    additional foreign key to Account for multi‑account support.
    """

    __tablename__ = "identities"

    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    recipient_id = Column(BigInteger, nullable=False)
    recipient_type = Column(Integer, nullable=False, default=0)
    device_id = Column(Integer, nullable=False, default=0)
    registration_id = Column(Integer, nullable=True)
    public_key = Column(LargeBinary(length=4294967295), nullable=True)
    private_key = Column(LargeBinary(length=4294967295), nullable=True)
    next_prekey_id = Column(Integer, nullable=True)
    timestamp = Column(BigInteger, nullable=True)

    account = relationship("Account", back_populates="identities", lazy="raise")

    @classmethod
    async def get_identity_key_pair(cls, session: AsyncSession, account_id: int):

        try:
            query = select(cls.public_key, cls.private_key).where(
                cls.account_id == account_id,
                cls.recipient_id == -1
            )
            result = await session.execute(query)
            row = result.first()
            if row and row[0] and row[1]:
                public_key_bytes = row[0]
                private_key_bytes = row[1]
                from zowpy.axolotl.identitykey import IdentityKey
                from zowpy.axolotl.identitykeypair import IdentityKeyPair
                from zowpy.axolotl.ecc.djbec import DjbECPublicKey, DjbECPrivateKey
                # Original LiteIdentityKeyStore strips first byte (0x05) for public key
                return IdentityKeyPair(
                    IdentityKey(DjbECPublicKey(public_key_bytes[1:])),
                    DjbECPrivateKey(private_key_bytes)
                )
            return None
        except Exception as e:
            logger.error(f"Error getting identity key pair: {e}")
            return None

    @classmethod
    async def get_local_registration_id(cls, session: AsyncSession, account_id: int):

        try:
            query = select(cls.registration_id).where(
                cls.account_id == account_id,
                cls.recipient_id == -1
            )
            result = await session.execute(query)
            registration_id = result.scalar()
            return registration_id
        except Exception as e:
            logger.error(f"Error getting local registration id: {e}")
            return None

    @classmethod
    async def store_local_data(cls, session: AsyncSession, account_id: int, 
                                    registration_id: int, identity_key_pair, device_id: int = 0):

        try:
            # Check if exists
            query = select(cls).where(
                cls.account_id == account_id,
                cls.recipient_id == -1
            )
            result = await session.execute(query)
            row = result.scalar_one_or_none()
            
            pub_key = identity_key_pair.getPublicKey().getPublicKey().serialize()
            priv_key = identity_key_pair.getPrivateKey().serialize()
            
            if row:
                row.registration_id = registration_id
                row.public_key = pub_key
                row.private_key = priv_key
                row.device_id = device_id
            else:
                new_identity = cls(
                    account_id=account_id,
                    recipient_id=-1,
                    recipient_type=0,
                    device_id=device_id,
                    registration_id=registration_id,
                    public_key=pub_key,
                    private_key=priv_key
                )
                session.add(new_identity)
            
            await session.commit()
        except Exception as e:
            logger.error(f"Error storing local data: {e}")
            await session.rollback()
            raise

    @classmethod
    async def save_identity(cls, session: AsyncSession, account_id: int, recipient_id: int, device_id: int, identity_key):

        try:
            # Delete existing
            query = delete(cls).where(
                cls.account_id == account_id,
                cls.recipient_id == recipient_id,
                cls.device_id == device_id
            )
            await session.execute(query)
            await session.commit()
            
            # Insert new
            pub_key = identity_key.getPublicKey().serialize()
            new_identity = cls(
                account_id=account_id,
                recipient_id=recipient_id,
                recipient_type=0,
                device_id=device_id,
                public_key=pub_key
            )
            session.add(new_identity)
            await session.commit()
        except Exception as e:
            logger.error(f"Error saving identity: {e}")
            await session.rollback()
            raise

    @classmethod
    async def is_trusted_identity(cls, session: AsyncSession, account_id: int, recipient_id: int, device_id: int, identity_key):

        try:
            query = select(cls.public_key).where(
                cls.account_id == account_id,
                cls.recipient_id == recipient_id,
                cls.device_id == device_id
            )
            result = await session.execute(query)
            public_key = result.scalar()
            
            if not public_key:
                return True  # If no identity stored, trust by default
            
            pub_key = identity_key.getPublicKey().serialize()
            return public_key == pub_key
        except Exception as e:
            logger.error(f"Error checking trusted identity: {e}")
            return True  # Default to trusted on error