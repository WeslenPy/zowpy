from __future__ import annotations

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
)
from sqlalchemy.orm import relationship
from zowpy.db.common.model import BaseModel
from zowpy.db.config.base import Model


class ProfileConfig(Model,BaseModel):
    """
    Generic per‑account configuration blob.

    This replaces the previous \"config.json\" / \"config\" profile files and
    allows storing arbitrary named blobs (json or key‑val format) per account.
    """
    __tablename__ = "profile_configs"

    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(128), nullable=False)  # e.g. \"config.json\"
    data = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, nullable=False, default=dt.datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=dt.datetime.utcnow,
        onupdate=dt.datetime.utcnow,
    )

    account = relationship("Account", lazy="raise")

    __table_args__ = (
        UniqueConstraint("account_id", "name", name="uq_profile_configs_account_name"),
    )