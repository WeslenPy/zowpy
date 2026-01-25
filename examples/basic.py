"""
Exemplo básico de uso do ZowPy - Mantendo conta online indefinidamente.

Demonstra como usar a API pública de forma assíncrona e manter a conta online.
Usa o novo cliente linear (client_v2) que implementa fluxo baseado no zowsuplib.
"""

import asyncio
import signal
import base64
from zowpy import ZowPyClient
from zowpy.core.import_account import import_account_from_six_parts
from loguru import logger

# Configura logging
logger.add("logs/basic.log", level="DEBUG")


async def main():
    """
    Exemplo básico usando o ZowPy Client - Mantendo online indefinidamente.
    
    O cliente implementa um fluxo completo baseado no zowsuplib:
    1. Conecta TCP
    2. Envia header WA\x06\x03
    3. Carrega prekeys
    4. Inicia bridge TCP ↔ Stream
    5. Executa handshake (Noise Protocol)
    6. Autentica (WAUTH-2)
    7. Envia prekeys
    8. Envia presence "available"
    9. Cliente pronto!
    
    Mantém a conta online indefinidamente:
    - Keepalive automático a cada 20 segundos
    - Reconexão automática em caso de desconexão
    - Tratamento de sinais para desconexão limpa (Ctrl+C)
    """
    
    # Cria cliente
    account_id = "201208868278"
    client = ZowPyClient(account_id)
    
    # Eventos
    @client.on_message
    async def handle_message(message):
        """Handler de mensagens recebidas"""
        await client.mark_as_read(message.get('id'), message.get('from'), message.get('participant'))
        logger.info(f"Mensagem recebida: {message}")
        print(f"📨 Mensagem recebida de {message.get('from', 'unknown')}: {message.get('text', '')}")
    
    @client.on_connected
    async def handle_connected(data=None):
        """Handler de conexão estabelecida"""
        account_id = data.get('account_id', 'unknown') if data else 'unknown'
        print(f"Conectado ao WhatsApp! Account: {account_id}")
        print("Cliente online - Mantendo conexão ativa...")
    
    @client.on_disconnected
    async def handle_disconnected(data=None):
        """Handler de desconexão - Reconecta automaticamente"""
        account_id = data.get('account_id', 'unknown') if data else 'unknown'
        print(f"Desconectado do WhatsApp. Account: {account_id}")
        
    try:
        # Conecta (fluxo linear: conexão → handshake → autenticação)
        # await client.remove_proxy()
        
        await client.connect()
        print("Cliente conectado e autenticado!")
        print("Cliente online - Mantendo conexão ativa indefinidamente...")
        
        # Envia mensagem inicial (opcional)
        to = "120363425739599511@g.us"
        text = "Hello! Esta é uma mensagem de teste do ZowPy."
        print(f" Enviando mensagem para {to}...")

        print(f"\n📤 Exemplo: Enviando mídia usando send_media_direct...")


        while True:
            await client.send_text(to, text)
            await asyncio.sleep(300)
            print(f"Enviando mensagem para {to}...")
        

        print("\n🔄 Desconectando...")
    
    except KeyboardInterrupt:
        await client.disconnect()
        print("\n🛑 Interrupção recebida, desconectando...")
    
    except Exception as e:
        print(f"❌ Erro: {e}")
        logger.exception("Erro no exemplo básico")
    
 
if __name__ == "__main__":
    asyncio.run(main())
    logger.info("Fim do exemplo básico")




