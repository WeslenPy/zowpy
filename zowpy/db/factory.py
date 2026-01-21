from sqlalchemy.ext.asyncio import AsyncSession
from .manager import AxolotlManager
from .store import SqlAxolotlStore
from typing import Optional
from loguru import logger
from .config.engine import AsyncSessionMaker


class AxolotlManagerFactory(object):
    """
    Factory that always uses the unified SQLAlchemy-backed Axolotl store.

    All accounts share a single database (see app/db.py), and data is
    linked via foreign keys to the Account table.
    """

    def __init__(self, session_maker: Optional[AsyncSessionMaker] = None):
        """
        :param session_maker: AsyncSessionMaker instance (optional, will use default if None)
        """
        if session_maker is None:
            session_maker = AsyncSessionMaker
        self.session_maker = session_maker

    async def get_manager(self, profile_name, username, session_maker: Optional[AsyncSessionMaker] = None):
        logger.debug(f"get_manager(profile_name={profile_name}, username={username})")

        # Unified backend: single DB, multi-account schema
        session_maker_to_use = session_maker or self.session_maker
        
        # Obter account_id primeiro
        from .models import Account
        async with session_maker_to_use() as temp_session:
            account = await Account.get_or_create_account(temp_session, username)
            account_id = account.id
        
        store = SqlAxolotlStore(username, account_id, session_maker_to_use)
        await store.setup()

        manager = AxolotlManager(store, username)
        await manager.initialize()
        return manager


