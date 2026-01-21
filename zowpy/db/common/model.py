from datetime import datetime

from loguru import logger
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    delete,
    desc,
    func,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only
from pydantic import BaseModel as PydanticBaseModel



class BaseModel:
    __table_args__: dict[str, str] = {'mysql_engine': 'InnoDB'}
    __mapper_args__: dict[str, bool] = {'always_refresh': True}
    __abstract__ = True

    id = Column(Integer, primary_key=True, name='id')


    created_at = Column(
        DateTime,
        name='created_at',
        nullable=False,
        default=datetime.now,
    )

    updated_at = Column(
        DateTime,
        name='update_at',
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
    )


    
    async def update_from_schema(self,session:AsyncSession,data:PydanticBaseModel):
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(self, key, value)

        await session.commit()
        await session.refresh(self)
        
        
    async def change_status_id(self, new_status_id: int,
                            session: AsyncSession) -> None:

        stmt = (
            update(self.__class__)
            .where(self.__class__.id == self.id)
            .values({"status_id": new_status_id})
        )

        await session.execute(stmt)
        await session.commit()

    @classmethod
    async def update_status_id(cls, new_status_id: int, current_id: int,
                            session: AsyncSession) -> None:

        stmt = (
            update(cls)
            .where(cls.id == current_id)
            .values({"status_id": new_status_id})
        )

        await session.execute(stmt)
        await session.commit()

    @classmethod
    async def get_full(cls, session: AsyncSession):

        logger.debug(session)

        stmt = select(cls)

        result = await session.execute(stmt)

        logger.info(f"Buscando todos os {cls.__tablename__}")

        row = result.scalars().all()

        logger.info(f" {cls.__tablename__} encontrados: {row}")

        return row

    @classmethod
    async def get_random(cls, session: AsyncSession):

        logger.debug(session)

        stmt = select(cls).order_by(func.random())

        result = await session.execute(stmt)

        logger.info(f"Buscando de forma randomica {cls.__tablename__}")

        row = result.scalars().first()

        logger.info(f" {cls.__tablename__} encontrada: {row}")

        return row

    @classmethod
    async def drop_all(cls, session: AsyncSession):
        await session.execute(delete(cls))
        await session.commit()

    @classmethod
    async def get_first_row(cls, session: AsyncSession):
        result = await session.execute(select(cls).order_by(desc(cls.id)))
        return result.scalars().first()

    async def save(self, session: AsyncSession):
        session.add(self)
        await session.commit()
        await session.refresh(self)

        return self

    async def save_with_flush(self, session: AsyncSession):
        session.add(self)
        await session.flush()
        await session.refresh(self)

        return self

    @classmethod
    async def delete_row(cls, _id: int, session: AsyncSession) -> bool:

        await session.execute(
        delete(cls).where(cls.id == _id))
        
        await session.commit()

    @classmethod
    async def exists(cls, _id: int, session: AsyncSession):

        row = await session.scalar(
            select(cls).options(load_only(cls.id)).where(
                cls.id == _id
            )
        )

        return row

    @classmethod
    async def update_obj(cls, _id: int, data: dict, session: AsyncSession):
        await session.execute(
            update(cls).where(cls.id == _id).values(**data)
        )
        await session.commit()

    async def update(self, data: dict, session: AsyncSession):
        for key, value in data.items():
            if key == 'id':
                continue

            if getattr(self, key, 'not_found') != 'not_found':
                setattr(self, key, value)
        await session.commit()
        return self
