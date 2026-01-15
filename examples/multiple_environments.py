"""
Exemplo de uso de múltiplas environments (Android, iOS, SMB Android, SMB iOS).

Demonstra como usar diferentes ambientes de dispositivo igual ao zowsuplib.
"""

import asyncio
from zowpy import ZowPyClient
from zowpy.config.environments import DeviceEnvironment


async def example_android():
    """Exemplo usando Android"""
    print("=== Android Environment ===")
    
    # Cria cliente com ambiente Android (padrão)
    client = ZowPyClient("5511999999999", device_env="android")
    print(f"Device env: {client.device_env}")
    
    # Ou usando DeviceEnvironment diretamente
    env = DeviceEnvironment("android")
    print(f"Platform: {env.getPlatform()}")
    print(f"OS: {env.getOSName()}")
    print(f"Device: {env.getDeviceName()}")
    print(f"Manufacturer: {env.getManufacturer()}")
    print()


async def example_ios():
    """Exemplo usando iOS"""
    print("=== iOS Environment ===")
    
    # Cria cliente com ambiente iOS
    client = ZowPyClient("5511999999999", device_env="ios")
    print(f"Device env: {client.device_env}")
    
    env = DeviceEnvironment("ios")
    print(f"Platform: {env.getPlatform()}")
    print(f"OS: {env.getOSName()}")
    print(f"Device: {env.getDeviceName()}")
    print(f"Manufacturer: {env.getManufacturer()}")
    print()


async def example_smb_android():
    """Exemplo usando SMB Android (WhatsApp Business)"""
    print("=== SMB Android Environment ===")
    
    # Cria cliente com ambiente SMB Android
    client = ZowPyClient("5511999999999", device_env="smb_android")
    print(f"Device env: {client.device_env}")
    
    env = DeviceEnvironment("smb_android")
    print(f"Platform: {env.getPlatform()}")
    print(f"OS: {env.getOSName()}")
    print(f"Device: {env.getDeviceName()}")
    print()


async def example_smb_ios():
    """Exemplo usando SMB iOS (WhatsApp Business)"""
    print("=== SMB iOS Environment ===")
    
    # Cria cliente com ambiente SMB iOS
    client = ZowPyClient("5511999999999", device_env="smb_ios")
    print(f"Device env: {client.device_env}")
    
    env = DeviceEnvironment("smb_ios")
    print(f"Platform: {env.getPlatform()}")
    print(f"OS: {env.getOSName()}")
    print(f"Device: {env.getDeviceName()}")
    print()


async def example_custom_config():
    """Exemplo usando configuração customizada"""
    print("=== Custom Configuration ===")
    
    # Cria ambiente com configuração customizada
    custom_config = {
        "device_name": "Custom Device",
        "os_version": "13.0.0",
        "manufacturer": "Samsung",
    }
    
    env = DeviceEnvironment("android", custom_config=custom_config)
    print(f"Device: {env.getDeviceName()}")
    print(f"OS Version: {env.getOSVersion()}")
    print(f"Manufacturer: {env.getManufacturer()}")
    print()


async def example_list_environments():
    """Lista todos os ambientes disponíveis"""
    print("=== Available Environments ===")
    
    envs = DeviceEnvironment.list_environments()
    for env_name in envs:
        env = DeviceEnvironment(env_name)
        platform_id = DeviceEnvironment.get_platform_id(env_name)
        print(f"{env_name}: platform={platform_id}, os={env.getOSName()}")
    print()


async def main():
    """Executa todos os exemplos"""
    await example_list_environments()
    await example_android()
    await example_ios()
    await example_smb_android()
    await example_smb_ios()
    await example_custom_config()


if __name__ == "__main__":
    asyncio.run(main())

