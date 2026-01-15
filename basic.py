"""
Exemplo básico de uso do ZowPy.

Demonstra como usar a API pública de forma assíncrona.
Usa o novo cliente linear (client_v2) que implementa fluxo baseado no zowsuplib.
"""

import asyncio
from zowpy import ZowPyClient
from loguru import logger

# Configura logging
logger.add("logs/basic.log", rotation="10 MB", retention="7 days", level="INFO")


async def main():
    """
    Exemplo básico usando o novo cliente linear.
    
    O novo cliente (client_v2) implementa um fluxo totalmente linear:
    1. Conecta TCP
    2. Envia header WA\x06\x03
    3. Carrega prekeys
    4. Inicia bridge TCP ↔ Stream
    5. Executa handshake (linear, sem eventos)
    6. Aguarda <success> do servidor
    7. Cliente pronto!
    """
    # Cria cliente (substitua pelo seu número)
    account_id = "5511999999999"  # Substitua pelo seu número
    client = ZowPyClient(account_id)
    
    # Eventos
    @client.on_message
    async def handle_message(message):
        """Handler de mensagens recebidas"""
        print(f"📨 Mensagem recebida de {message.get('from', 'unknown')}: {message.get('text', '')}")
    
    @client.on_connected
    async def handle_connected():
        """Handler de conexão estabelecida"""
        print("✅ Conectado ao WhatsApp!")
    
    @client.on_disconnected
    async def handle_disconnected():
        """Handler de desconexão"""
        print("❌ Desconectado do WhatsApp")
    
    try:
        # Conecta (fluxo linear: conexão → handshake → autenticação)
        print("🔄 Conectando ao WhatsApp...")
        await client.connect()
        print("✅ Cliente conectado e autenticado!")
        
        # Envia mensagem
        to = "5511888888888"  # Substitua pelo número de destino
        text = "Hello! Esta é uma mensagem de teste do ZowPy."
        print(f"📤 Enviando mensagem para {to}...")
        msg_id = await client.send_text(to, text)
        print(f"✅ Mensagem enviada! ID: {msg_id}")
        
        # Aguarda resposta (timeout de 30s)
        # Estilo whatsmeow: pode filtrar por remetente, tipo, etc.
        print("⏳ Aguardando resposta...")
        try:
            response = await client.wait_for_message(
                timeout=30.0,
                from_jid=f"{to}@s.whatsapp.net"  # Filtra por remetente
            )
            print(f"📨 Resposta recebida de {response.get('from')}: {response.get('text')}")
        except Exception as e:
            print(f"⏱️  Nenhuma resposta recebida: {e}")
        
        # Aguarda um pouco antes de desconectar
        print("⏳ Aguardando 5 segundos antes de desconectar...")
        await asyncio.sleep(5)
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        logger.exception("Erro no exemplo básico")
    finally:
        # Desconecta
        print("🔄 Desconectando...")
        await client.disconnect()
        print("✅ Desconectado com sucesso!")


if __name__ == "__main__":
    asyncio.run(main())

