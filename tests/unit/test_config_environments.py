"""
Testes unitários para config/environments.py
"""

import pytest
from zowpy.config.environments import (
    DeviceEnvironment,
    AndroidConfig,
    iOSConfig,
    SMBAndroidConfig,
    SMBiOSConfig,
)


def test_device_environment_android():
    """Testa ambiente Android"""
    env = DeviceEnvironment("android")
    
    assert env.getPlatform() == 0
    assert env.getOSName() == "Android"
    assert env.getVersion() == "2.25.29.75"
    assert env.isAxolotlEnable() is True


def test_device_environment_ios():
    """Testa ambiente iOS"""
    env = DeviceEnvironment("ios")
    
    assert env.getPlatform() == 1
    assert env.getOSName() == "iOS"
    assert env.getVersion() == "2.25.29.75"
    assert env.isAxolotlEnable() is True


def test_device_environment_smb_android():
    """Testa ambiente SMB Android"""
    env = DeviceEnvironment("smb_android")
    
    assert env.getPlatform() == 10
    assert env.getOSName() == "Android"
    assert env.getVersion() == "2.25.29.75"
    assert env.isAxolotlEnable() is True


def test_device_environment_smb_ios():
    """Testa ambiente SMB iOS"""
    env = DeviceEnvironment("smb_ios")
    
    assert env.getPlatform() == 12
    assert env.getOSName() == "iOS"
    assert env.getVersion() == "2.25.29.75"
    assert env.isAxolotlEnable() is True


def test_device_environment_invalid():
    """Testa ambiente inválido"""
    with pytest.raises(ValueError, match="Unknown device environment"):
        DeviceEnvironment("invalid")


def test_device_environment_custom_config():
    """Testa ambiente com configuração customizada"""
    custom = {
        "device_name": "Custom Device",
        "os_version": "12.0.0",
    }
    env = DeviceEnvironment("android", custom_config=custom)
    
    assert env.getDeviceName() == "Custom Device"
    assert env.getOSVersion() == "12.0.0"


def test_device_environment_get_platform_id():
    """Testa obtenção de platform ID"""
    assert DeviceEnvironment.get_platform_id("android") == 0
    assert DeviceEnvironment.get_platform_id("ios") == 1
    assert DeviceEnvironment.get_platform_id("smb_android") == 10
    assert DeviceEnvironment.get_platform_id("smb_ios") == 12


def test_device_environment_list_environments():
    """Testa listagem de ambientes"""
    envs = DeviceEnvironment.list_environments()
    
    assert "android" in envs
    assert "ios" in envs
    assert "smb_android" in envs
    assert "smb_ios" in envs


def test_device_environment_is_valid():
    """Testa validação de ambiente"""
    assert DeviceEnvironment.is_valid("android") is True
    assert DeviceEnvironment.is_valid("ios") is True
    assert DeviceEnvironment.is_valid("smb_android") is True
    assert DeviceEnvironment.is_valid("smb_ios") is True
    assert DeviceEnvironment.is_valid("invalid") is False


def test_device_environment_setters():
    """Testa métodos setters"""
    env = DeviceEnvironment("android")
    
    env.setDeviceName("New Device")
    assert env.getDeviceName() == "New Device"
    
    env.setOSVersion("13.0.0")
    assert env.getOSVersion() == "13.0.0"
    
    env.setManufacturer("Samsung")
    assert env.getManufacturer() == "Samsung"

