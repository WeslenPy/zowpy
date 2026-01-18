"""
Exemplo básico de uso do ZowPy - Mantendo conta online indefinidamente.

Demonstra como usar a API pública de forma assíncrona e manter a conta online.
Usa o novo cliente linear (client_v2) que implementa fluxo baseado no zowsuplib.
"""

import asyncio
import signal
from zowpy import ZowPyClient
from zowpy.core.import_account import import_account_from_six_parts
from loguru import logger

# Configura logging
logger.add("logs/basic.log", level="DEBUG")

# Flag global para controle de desconexão
running = True

def signal_handler(sig, frame):
    """Handler para SIGINT (Ctrl+C)"""
    global running
    print("\n🛑 Recebido sinal de interrupção, desconectando...")
    running = False

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
    global running
    
    # Configura handler para Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Importa conta (se necessário)
    six_parts = "201288305948,gehExdJAhPTAkqd5LDQ0zsBmUuuvP837jAQHNgndgnk=,+I0r7c+ZSZl6HmmY9uUI8E3ki4+ZRQ3trbYGISvLem0=,HiqT5eRDdur33fCRLW/UmUi8Sm/c+mEL+ajC/pIE/nk=,AAOlZ9VKgYuEvIetCouS+BS2DXCLd5XS2PispXKClkw=,MjAxMjg4MzA1OTQ4I6EaQHqQklbEQ2Klo9w0kEh1yPOB"
    await import_account_from_six_parts(six_parts, env="smb_android")
    
    # Cria cliente
    account_id = six_parts.split(",")[0]
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
        print(f"✅ Conectado ao WhatsApp! Account: {account_id}")
        print("🟢 Cliente online - Mantendo conexão ativa...")
    
    @client.on_disconnected
    async def handle_disconnected(data=None):
        """Handler de desconexão - Reconecta automaticamente"""
        account_id = data.get('account_id', 'unknown') if data else 'unknown'
        print(f"❌ Desconectado do WhatsApp. Account: {account_id}")
        
        # Reconecta automaticamente se ainda estiver rodando
        if running:
            print("🔄 Tentando reconectar automaticamente...")
            try:
                # Aguarda um pouco antes de reconectar
                await asyncio.sleep(2)
                await client.reconnect()
                print("✅ Reconectado com sucesso!")
            except Exception as e:
                logger.error(f"Erro ao reconectar: {e}", exc_info=True)
                print(f"❌ Erro ao reconectar: {e}")
                # Tenta novamente após 5 segundos
                await asyncio.sleep(5)
                if running:
                    try:
                        await client.reconnect()
                    except Exception as reconnect_error:
                        logger.error(f"Erro na segunda tentativa de reconexão: {reconnect_error}", exc_info=True)
    
    try:
        # Conecta (fluxo linear: conexão → handshake → autenticação)
        print("🔄 Conectando ao WhatsApp...")
        await client.connect()
        print("✅ Cliente conectado e autenticado!")
        print("🟢 Cliente online - Mantendo conexão ativa indefinidamente...")
        print("💡 Pressione Ctrl+C para desconectar")
        
        # Envia mensagem inicial (opcional)
        to = "559885700260"
        text = "Hello! Esta é uma mensagem de teste do ZowPy."
        # print(f"📤 Enviando mensagem para {to}...")
        msg_id = await client.send_text(to, text)
        # print(f"✅ Mensagem enviada! ID: {msg_id}")
        
        # Mantém o cliente online indefinidamente
        # O keepalive é enviado automaticamente a cada 20 segundos
        # A reconexão automática é tratada no handler on_disconnected
        while running:
            # Verifica se ainda está conectado
            if not client._connected or not client._authenticated:
                if running:
                    print("⚠️ Cliente desconectado, aguardando reconexão automática...")
                    await asyncio.sleep(5)
                    continue
            
            # Aguarda 1 segundo e verifica novamente
            await asyncio.sleep(1)
        
        print("\n🔄 Desconectando...")
    
    except KeyboardInterrupt:
        print("\n🛑 Interrupção recebida, desconectando...")
        running = False
    
    except Exception as e:
        print(f"❌ Erro: {e}")
        logger.exception("Erro no exemplo básico")
        running = False
    
    finally:
        # Desconecta apenas se running foi desativado
        if not running:
            print("🔄 Desconectando...")
            try:
                await client.disconnect()
                print("✅ Desconectado com sucesso!")
            except Exception as e:
                logger.error(f"Erro ao desconectar: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
