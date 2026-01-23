"""
Exemplo avançado de uso do ZowPy.

Demonstra uso de múltiplas contas e eventos.
"""

import asyncio
from zowpy import AccountManager
from zowpy.core.import_account import import_account_from_six_parts
from loguru import logger
logger.add("logs/advanced.log", level="DEBUG")

async def main():
    """Exemplo avançado com múltiplas contas"""


    six_parts= "pk1,sk1,pk2,sk2,sixth"
    await import_account_from_six_parts(six_parts, env="smb_android")
    # Cria manager
    manager = AccountManager()
    
    # Adiciona contas
    account1 = await manager.add_account("555555555555")
    account2 = await manager.add_account("555555555552")
    
    # Eventos para account1
    @account1.on_message
    async def handle_message1(message):
        print(f"[Account1] Received: {message.get('text', '')}")
    
    # Eventos para account2
    @account2.on_message
    async def handle_message2(message):
        print(f"[Account2] Received: {message.get('text', '')}")
    
    try:
        # Conecta todas contas
        await manager.connect_all()
        
        to = "555555555555"

        await account1.join_group_with_link("IkUXAl5oMK5I0ZXp9dauhy")
        await account2.join_group_with_link("IkUXAl5oMK5I0ZXp9dauhy")
        # await account3.join_group_with_link("IkUXAl5oMK5I0ZXp9dauhy")


        # Envia mensagens
        msg_id1 = await account1.send_text(to, "Hello from account1!")
        msg_id2 = await account2.send_text(to, "Hello from account2!")
        # msg_id3 = await account3.send_text(to, "Hello from account3!")

        print(f"Messages sent: {msg_id1}, {msg_id2}")
        
        # Aguarda um pouco
        await asyncio.sleep(10)
        



    finally:
        # Desconecta todas
        await manager.shutdown()


if __name__ == "__main__":
    asyncio.run(main())












