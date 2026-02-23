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