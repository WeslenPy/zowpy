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


class TaskMsg(Model,BaseModel):
    """
    Port of the `task_msg` table from LiteTaskMsgStore.
    Armazena mensagens de tarefa para rastreamento de respostas.
    """

    __tablename__ = "task_msgs"

    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    msg_id = Column(String(255), nullable=False, index=True)
    task_id = Column(String(255), nullable=False, index=True)
    src = Column(String(255), nullable=False)  # JID do remetente
    dst = Column(String(255), nullable=False)  # JID do destinatário

    created_at = Column(DateTime, nullable=False, default=dt.datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # Para limpeza automática

    account = relationship("Account", back_populates="task_msgs", lazy="raise")

    __table_args__ = (
        Index("ix_task_msgs_account_msg", "account_id", "msg_id", unique=True),
        Index("ix_task_msgs_account_task", "account_id", "task_id"),
        Index("ix_task_msgs_src_dst", "src", "dst"),
    )
