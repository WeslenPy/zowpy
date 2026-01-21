from .base import Model
from .engine import engine, get_async_session_with_context



async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)
