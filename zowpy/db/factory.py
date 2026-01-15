from .manager import AxolotlManager
from .store.sqlaxolotlstore import SqlAxolotlStore
from .pool import AsyncDatabasePool
from typing import Optional
from loguru import logger


class AxolotlManagerFactory(object):
    """
    Factory that always uses the unified SQLAlchemy-backed Axolotl store.

    All accounts share a single database (see app/db.py), and data is
    linked via foreign keys to the Account table.
    """

    def __init__(self, db_pool: Optional[AsyncDatabasePool] = None):
        """
        :param db_pool: AsyncDatabasePool instance (optional, will use from_settings if None)
        """
        if db_pool is None:
            db_pool = AsyncDatabasePool.from_settings()
        self.db_pool = db_pool

    async def get_manager(self, profile_name, username, db_pool=None):
        logger.debug(f"get_manager(profile_name={profile_name}, username={username})")

        # Unified backend: single DB, multi-account schema
        store = SqlAxolotlStore(username, db_pool or self.db_pool)

        manager = AxolotlManager(store, username)
        await manager.initialize()
        return manager


