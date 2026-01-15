"""
Consonance Config - Portado e adaptado para zowpy.

Porta ClientConfig, AppVersionConfig e UserAgentConfig do consonance.
"""


class AppVersionConfig:
    """Configuração de versão da aplicação."""

    STR_TEMPLATE = """AppVersionConfig(
            primary={primary},
            secondary={secondary},
            tertiary={tertiary},
            quaternary={quaternary}
        )"""

    def __init__(self, version: str):
        """
        :param version: Versão no formato "X.Y.Z.W" ou similar
        :type version: str
        """
        self._version = version
        dissected = version.split(".")
        padded = dissected + ["0"] * (4 - len(dissected))
        assert len(padded) == 4, f"{version} is not a valid version"

        self._primary, self._secondary, self._tertiary, self._quaternary = map(
            lambda v: int(v), padded
        )

    def __str__(self) -> str:
        return self.STR_TEMPLATE.format(
            primary=self.primary,
            secondary=self.secondary,
            tertiary=self.tertiary,
            quaternary=self.quaternary,
        )

    def get_version(self) -> str:
        """Retorna a versão como string."""
        return self._version

    @property
    def primary(self) -> int:
        return self._primary

    @property
    def secondary(self) -> int:
        return self._secondary

    @property
    def tertiary(self) -> int:
        return self._tertiary

    @property
    def quaternary(self) -> int:
        return self._quaternary


class UserAgentConfig:
    """Configuração de User Agent."""

    PLATFORM_ANDROID = 0
    PLATFORM_IOS = 1
    PLATFORM_WINDOWS_PHONE = 2
    PLATFORM_PYTHON_CLIENT = 7
    SMB_ANDROID = 10
    SMB_IOS = 12

    STR_TEMPLATE = """UserAgentConfig(
        platform={platform},
        app_version={app_version},
        mcc={mcc},
        mnc={mnc},
        os_version={os_version},
        manufacturer={manufacturer},
        device={device},
        os_build_number={os_build_number},
        phone_id={phone_id},
        locale_lang={locale_lang},
        locale_country={locale_country},
        device_exp_id={device_exp_id},
        device_type={device_type},
        device_model_type={device_model_type}
    )"""

    def __init__(
        self,
        platform: int,
        app_version: "AppVersionConfig | str",
        mcc: str,
        mnc: str,
        os_version: str,
        manufacturer: str,
        device: str,
        os_build_number: str,
        phone_id: str,
        locale_lang: str,
        locale_country: str,
        device_exp_id: str,
        device_type: str,
        device_model_type: str,
    ):
        """
        :param platform: Plataforma (PLATFORM_ANDROID, PLATFORM_IOS, etc.)
        :param app_version: Versão da app (AppVersionConfig ou string)
        :param mcc: Mobile Country Code
        :param mnc: Mobile Network Code
        :param os_version: Versão do OS
        :param manufacturer: Fabricante
        :param device: Dispositivo
        :param os_build_number: Número de build do OS
        :param phone_id: ID do telefone
        :param locale_lang: Idioma do locale
        :param locale_country: País do locale
        :param device_exp_id: ID experimental do dispositivo
        :param device_type: Tipo do dispositivo
        :param device_model_type: Tipo do modelo do dispositivo
        """
        if isinstance(app_version, str):
            app_version = AppVersionConfig(app_version)
        self._platform = platform
        self._app_version = app_version
        self._mcc = mcc
        self._mnc = mnc
        self._os_version = os_version
        self._manufacturer = manufacturer
        self._device = device
        self._os_build_number = os_build_number
        self._phone_id = phone_id
        self._locale_lang = locale_lang
        self._locale_country = locale_country
        self._device_exp_id = device_exp_id
        self._device_type = device_type
        self._device_model_type = device_model_type

    def __str__(self) -> str:
        return self.STR_TEMPLATE.format(
            platform=self.platform,
            app_version=self.app_version,
            mcc=self.mcc,
            mnc=self.mnc,
            os_version=self.os_version,
            manufacturer=self.manufacturer,
            device=self.device,
            os_build_number=self.os_build_number,
            phone_id=self.phone_id,
            locale_lang=self.locale_lang,
            locale_country=self.locale_country,
            device_exp_id=self.device_exp_id,
            device_type=self.device_type,
            device_model_type=self.device_model_type,
        )

    @property
    def platform(self) -> int:
        return self._platform

    @property
    def app_version(self) -> AppVersionConfig:
        return self._app_version

    @property
    def mcc(self) -> str:
        return self._mcc

    @property
    def mnc(self) -> str:
        return self._mnc

    @property
    def os_version(self) -> str:
        return self._os_version

    @property
    def manufacturer(self) -> str:
        return self._manufacturer

    @property
    def device(self) -> str:
        return self._device

    @property
    def os_build_number(self) -> str:
        return self._os_build_number

    @property
    def phone_id(self) -> str:
        return self._phone_id

    @property
    def locale_lang(self) -> str:
        return self._locale_lang

    @property
    def locale_country(self) -> str:
        return self._locale_country

    @property
    def device_exp_id(self) -> str:
        return self._device_exp_id

    @property
    def device_type(self) -> str:
        return self._device_type

    @property
    def device_model_type(self) -> str:
        return self._device_model_type


class ClientConfig:
    """Configuração do cliente WhatsApp."""

    STR_TEMPLATE = """ClientConfig(
    username={username},
    passive={passive},
    useragent={useragent},
    pushname={pushname},
    short_connect={short_connect}
)"""

    def __init__(
        self,
        username: int,
        passive: bool,
        useragent: UserAgentConfig,
        pushname: str,
        short_connect: bool = True,
        connect_reason: str | None = None,
    ):
        """
        :param username: Número de telefone (username)
        :param passive: Modo passivo
        :param useragent: Configuração do user agent
        :param pushname: Nome de exibição
        :param short_connect: Conexão curta
        :param connect_reason: Razão da conexão
        """
        self._username = username
        self._passive = passive
        self._useragent = useragent
        self._pushname = pushname
        self._short_connect = short_connect
        self._connect_reason = connect_reason

    def __str__(self) -> str:
        return self.STR_TEMPLATE.format(
            username=self.username,
            passive=self.passive,
            useragent=self.useragent,
            pushname=self.pushname,
            short_connect=self.short_connect,
        )

    @property
    def username(self) -> int:
        return self._username

    @property
    def passive(self) -> bool:
        return self._passive

    @property
    def useragent(self) -> UserAgentConfig:
        return self._useragent

    @property
    def pushname(self) -> str:
        return self._pushname

    @property
    def short_connect(self) -> bool:
        return self._short_connect

    @property
    def connect_reason(self) -> str | None:
        return self._connect_reason

