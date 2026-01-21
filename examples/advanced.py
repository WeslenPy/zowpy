"""
Exemplo avançado de uso do ZowPy.

Demonstra uso de múltiplas contas e eventos.
"""

import asyncio
from zowpy import ZowPyClient, AccountManager


async def main():
    """Exemplo avançado com múltiplas contas"""
    # Cria manager
    manager = AccountManager()
    
    # Adiciona contas
    account1 = await manager.add_account("5511999999999")
    account2 = await manager.add_account("5511888888888")
    
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
        
        # Envia mensagens
        msg_id1 = await account1.send_text("5511888888888", "Hello from account1!")
        msg_id2 = await account2.send_text("5511999999999", "Hello from account2!")
        
        print(f"Messages sent: {msg_id1}, {msg_id2}")
        
        # Aguarda um pouco
        await asyncio.sleep(10)
        
    finally:
        # Desconecta todas
        await manager.shutdown()


if __name__ == "__main__":
    asyncio.run(main())










