"""
Exemplo de uso de wait_for_message estilo whatsmeow.

Demonstra como usar filtros e condições para aguardar mensagens específicas.
"""

import asyncio
from zowpy import ZowPyClient


async def main():
    """Exemplo de wait_for_message com filtros"""
    client = ZowPyClient("5511999999999")
    
    try:
        await client.connect()
        
        # Exemplo 1: Aguarda qualquer mensagem
        print("Aguardando qualquer mensagem...")
        msg1 = await client.wait_for_message(timeout=30.0)
        print(f"Recebido: {msg1}")
        
        # Exemplo 2: Aguarda mensagem de um remetente específico
        print("\nAguardando mensagem de 5511888888888...")
        msg2 = await client.wait_for_message(
            timeout=30.0,
            from_jid="5511888888888@s.whatsapp.net"
        )
        print(f"Recebido de {msg2.get('from')}: {msg2.get('text')}")
        
        # Exemplo 3: Aguarda mensagem de texto
        print("\nAguardando mensagem de texto...")
        msg3 = await client.wait_for_message(
            timeout=30.0,
            message_type="text"
        )
        print(f"Texto recebido: {msg3.get('text')}")
        
        # Exemplo 4: Aguarda mensagem com condição customizada
        print("\nAguardando mensagem contendo 'hello'...")
        msg4 = await client.wait_for_message(
            timeout=30.0,
            condition=lambda m: "hello" in m.get("text", "").lower()
        )
        print(f"Mensagem com 'hello': {msg4.get('text')}")
        
        # Exemplo 5: Aguarda mensagem de um remetente E com texto específico
        print("\nAguardando mensagem de remetente específico com 'ok'...")
        msg5 = await client.wait_for_message(
            timeout=30.0,
            from_jid="5511888888888@s.whatsapp.net",
            condition=lambda m: "ok" in m.get("text", "").lower()
        )
        print(f"Resposta OK recebida: {msg5.get('text')}")
        
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

