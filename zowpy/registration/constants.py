import json
import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, FrozenSet, Optional


# Nomes de OS do DeviceEnv / Config alinhados a SMB (companion / business).
_SMB_OS_NAMES: FrozenSet[str] = frozenset({"SMBA", "SMBI", "SMB iOS"})

# Lista típica de permissões ausentes no telemetria Android (debug_info).
_DEFAULT_MISSING_PERMISSIONS = (
    "android.permission.FOREGROUND_SERVICE_DATA_SYNC, "
    "android.permission.FOREGROUND_SERVICE_MICROPHONE, "
    "android.permission.FOREGROUND_SERVICE_CAMERA, "
    "android.permission.FOREGROUND_SERVICE_MEDIA_PROJECTION, "
    "android.permission.SCHEDULE_EXACT_ALARM, "
    "android.permission.NEARBY_WIFI_DEVICES, "
    "android.permission.ACCESS_MEDIA_LOCATION, "
    "android.permission.FOREGROUND_SERVICE_LOCATION, "
    "android.permission.INSTALL_SHORTCUT, "
    "android.permission.READ_MEDIA_AUDIO, "
    "android.permission.READ_MEDIA_IMAGES, "
    "android.permission.READ_MEDIA_VIDEO, "
    "android.permission.READ_MEDIA_VISUAL_USER_SELECTED, "
    "android.permission.POST_NOTIFICATIONS, "
    "android.permission.USE_FULL_SCREEN_INTENT, "
    "com.sec.android.provider.badge.permission.READ, "
    "com.sec.android.provider.badge.permission.WRITE, "
    "com.htc.launcher.permission.READ_SETTINGS, "
    "com.htc.launcher.permission.UPDATE_SHORTCUT, "
    "com.sonyericsson.home.permission.BROADCAST_BADGE, "
    "com.sonymobile.home.permission.PROVIDER_INSERT_BADGE, "
    "com.huawei.android.launcher.permission.READ_SETTINGS, "
    "com.huawei.android.launcher.permission.WRITE_SETTINGS, "
    "com.huawei.android.launcher.permission.CHANGE_BADGE, "
    "com.facebook.services.identity.FEO2"
)


class PayloadManager:
    @staticmethod
    def _random_choice(options: list[str]) -> str:
        return random.choice(options)

    @staticmethod
    def is_smb_os_name(os_name: Optional[str]) -> bool:
        """True se o ambiente for SMB (SMBA / SMBI / SMB iOS, etc.)."""
        if not os_name:
            return False
        name = str(os_name).strip()
        if name in _SMB_OS_NAMES:
            return True
        upper = name.upper()
        return "SMB" in upper

    @classmethod
    def _build_debug_info(
        cls,
        *,
        version: str,
        lg: str,
        lc: str,
        context: str,
        os_name: Optional[str] = None,
        device: Optional[str] = None,
        manufacturer: Optional[str] = None,
        model: Optional[str] = None,
        carrier: Optional[str] = None,
        mcc_mnc: Optional[str] = None,
        sim_mcc_mnc: Optional[str] = None,
    ) -> Dict[str, Any]:
        
        chosen_device = device or cls._random_choice(["ASUS_I005DA", "SM-S901E", "Pixel 7", "M2101K9G"])
        chosen_manufacturer = manufacturer or cls._random_choice(["Asus", "Samsung", "Google", "Xiaomi"])
        chosen_model = model or chosen_device
        chosen_carrier = carrier or cls._random_choice(["TIM", "VIVO", "Claro", "Oi"])
        chosen_mcc_mnc = mcc_mnc or cls._random_choice(["724-02", "724-05", "724-06", "724-10"])
        chosen_sim_mcc_mnc = sim_mcc_mnc or chosen_mcc_mnc
        chosen_connection = cls._random_choice(["W.I.F.I."])
        chosen_network = cls._random_choice(["U.N.K.N.O.W.N."])
        local_now = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S.%f%z")
        pretty_free_space = f"{random.randint(12, 128)} GB"
        # is_companion = cls.is_smb_os_name(os_name)

        return {
            "App": "com.whatsapp",
            "Architecture": cls._random_choice(["x86_64", "arm64-v8a"]),
            "Board": cls._random_choice(["SM8350", "GS201"]),
            "Build": f"{chosen_manufacturer}/{chosen_manufacturer}/{chosen_device}:9/release:user/release-keys",
            "CCode": " ",
            "CPU ABI": cls._random_choice(["arm64-v8a", "x86_64"]),
            "Carrier": chosen_carrier,
            "Description": version,
            "Device": chosen_device,
            "Device ID": 0,
            "Device ISO8601": local_now,
            "Is Foldable": False,
            "Is Tablet": False,
            "Kernel": cls._random_choice(
                [
                    "4.19.71+ #949 SMP PREEMPT Mon Sep 11 17:07:27 CST 2023",
                ]
            ),
            "LC": lc.upper(),
            "LG": lg,
            "Manufacturer": chosen_manufacturer,
            "Missing Permissions": _DEFAULT_MISSING_PERMISSIONS,
            "Model": chosen_model,
            "Network Type": chosen_network,
            "OS": cls._random_choice(["9", "10", "11", "12", "13", "14"]),
            "Phone Type": "G.S.M.",
            "Product": chosen_device,
            "Radio MCC-MNC": chosen_mcc_mnc,
            "SIM MCC-MNC": chosen_sim_mcc_mnc,
            "Target": "release",
            "Version": version,
            "Debug info": "unregistered",
            "MDEnabled": True,
            "HasMdCompanion": False,
            "Context": context,
            "useragent": f"WhatsApp/{version} Android/9 Device/{chosen_manufacturer}-{chosen_device}",
            "Socket Conn": "DN",
            "Free Space Built-In": pretty_free_space,
            "Free Space Removable": pretty_free_space,
            "Smb count":0,
            "Ent count":0,
            "Connection": chosen_connection,
            "Diagnostic Codes": cls._random_choice(
                ["DC-RTED FE-GDE FE-GDC FE-VIDC FE-SMSRTV"]
            ),
            "Sim": f"{random.randint(10000000000, 99999999999)} {random.randint(1, 9)}",
            "L Distance": 11,
            "Network metered": "100:false",
            "Network restricted": "100:false",
            "Data roaming": "false",
            "Tel roaming": "false",
            "ABprops hash state": "unregistered",
            "Serverprops hash state": "unregistered",
            "Video transcode": "no encoders",
            "XPMigrated": "no",
            "Screen reader": False,
            "Fingerprint eligible": False,
            "Last local backup time": "never",
            "Google account added": True,
            "Groups media visibility": "default",
            "Individual media visibility": "default",
            "In scoped mode": False,
            "Has unexpected .nomedia": False,
            "waffle enabled": False,
            "Is Companion": False,
            "Has Wear OS Companion": False,
            "saga_copy": False,
        }

    @classmethod
    def variables(
        cls,
        *,
        description: str ,
        request_token: str,
        version: str,
        app_id: str = "dev.app.id",
        lg: str = "pt",
        lc: str = "BR",
        context: str = "blocked_ban_appeals",
        os_name: Optional[str] = None,
        debug_overrides: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Retorna payload GraphQL em JSON string.

        ``os_name`` (ex.: ``DeviceEnv.getOSName()``) define ``Is Companion``: só SMB
        marca companion; caso contrário é ``False``.
        """
        debug_info = cls._build_debug_info(
            version=version, lg=lg, lc=lc, context=context, os_name=os_name
        )
        if debug_overrides:
            debug_info.update(debug_overrides)

        payload = {
            "app_id": app_id,
            "request_token": request_token,
            "user_request": {
                "description": description,
                "debug_info": json.dumps(debug_info, ensure_ascii=False),
            },
        }
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

    @classmethod
    def access_token(cls) -> str:
        return "WA|1015890928915437|3201f239340c1c8ec6262a6dad04200e"

    @classmethod
    def doc_id(cls) -> int:
        return 6960707423955525


class URLManager:
    @classmethod
    def domain(cls) -> str:
        return "whatsapp"

    @classmethod
    def protocol(cls) -> str:
        return "https"

    @classmethod
    def wa_graphql_host(cls) -> str:
        return f"graph.{cls.domain()}.com"

    @classmethod
    def wa_graphql(cls) -> str:
        return f"{cls.protocol()}://{cls.wa_graphql_host()}"

    @classmethod
    def wa_net(cls) -> str:
        return f"{cls.protocol()}://v.{cls.domain()}.net"