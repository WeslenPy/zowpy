from ..config.manager import ConfigManager
from ..config.v1.config import Config
from loguru import logger
from ..db.factory import AxolotlManagerFactory
from ..db.manager import AxolotlManager

class AsyncProfile(object):
    def __init__(self, profile_name, config=None, db_pool=None):
        # type: (str, Config) -> None
        """
        :param profile_name:  profile name
        :param config: A supplied config will disable loading configs using the Config manager and provide that config
        instead
        """
        logger.debug(f"Constructed Profile(profile_name={profile_name})")
        self._profile_name = profile_name
        self._config = config
        self._config_manager = ConfigManager()
        self._db_pool = db_pool
        self._axolotl_manager = None

    def __str__(self):
        return "AsyncProfile(profile_name=%s)" % self._profile_name

    async def _load_config(self, db_pool=None):
        # type: () -> Config
        logger.debug(f"load_config for {self._profile_name}")
        return await self._config_manager.load(self._profile_name, db_pool=db_pool or self._db_pool)

    async def _load_axolotl_manager(self, db_pool=None):
        # type: () -> AxolotlManager
        return await AxolotlManagerFactory().get_manager(self._profile_name, self.username, db_pool=db_pool or self._db_pool)

    async def write_config(self, config, db_pool=None):
        # type: (Config) -> None
        logger.debug(f"write_config for {self._profile_name}")
        await self._config_manager.save(self._profile_name, config, db_pool=db_pool or self._db_pool)

    @property
    async def config(self):
        if self._config is None:
            self._config = await self._load_config()
        return self._config

    @property
    async def axolotl_manager(self):
        if self._axolotl_manager is None:
            self._axolotl_manager = await self._load_axolotl_manager()
        return self._axolotl_manager

    @property
    async def username(self):
        config = await self.config
        return config.login or config.phone or self._profile_name


