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


class PollOption(Model,BaseModel):
    """
    Port of the `poll_option` table from LitePollStore.
    """

    __tablename__ = "poll_options"

    poll_id = Column(Integer, ForeignKey("polls.id", ondelete="CASCADE"), nullable=False, index=True)

    option_name = Column(String(255), nullable=False)
    option_sha256 = Column(LargeBinary, nullable=False)

    poll = relationship("Poll", back_populates="options", lazy="raise")

    __table_args__ = (
        Index("ix_poll_options_poll_sha", "poll_id", "option_sha256", unique=True),
    )
