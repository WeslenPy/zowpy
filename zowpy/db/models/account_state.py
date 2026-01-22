

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
from sqlalchemy.dialects.mysql import LONGTEXT,LONGBLOB

from sqlalchemy.orm import relationship
from zowpy.db.common.model import BaseModel
from zowpy.db.config.base import Model



class AccountState(Model,BaseModel):
    """
    Armazena estado genérico da conta (key-value pairs).
    Usado para armazenar dados temporários como credenciais, tokens, etc.
    """
    __tablename__ = "account_state"
    
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    
    key = Column(String(255), nullable=False, index=True)
    value = Column(Text, nullable=True)  # JSON serializado
    
    account = relationship("Account", back_populates="account_state", lazy="raise")
    
    __table_args__ = (
        UniqueConstraint("account_id", "key", name="uq_account_state_account_key"),
        Index("ix_account_state_account_key", "account_id", "key"),
    )

