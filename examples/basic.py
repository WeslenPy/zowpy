"""
Exemplo básico de uso do ZowPy.

Demonstra como usar a API pública de forma assíncrona.
Usa o novo cliente linear (client_v2) que implementa fluxo baseado no zowsuplib.
"""

import asyncio
from zowpy import ZowPyClient
from zowpy.core.import_account import import_account_from_six_parts
from loguru import logger

# Configura logging
logger.add("logs/basic.log",  level="DEBUG")

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
    # Importa conta (se necessário)
    six_parts = "201288480973,AlRIiQrA/5lc+fKvMbL1oCsLU1NzuRXzZGQlnY6VvBo=,sDuD+i4yroP8UvXssgPKLea7B9GV3X9C9SZ4XkzGQUI=,WqvR/LO+GfvDtASa0XVuGlmRJlhwZ1SKbow3aMjmeAc=,2F/XuRqbi/vps/4XIP8Y1YLJlhCW7D9B5/Dew7KN23Y=,MjAxMjg4NDgwOTczI7fskl6SZSyH5qJtFVZkFKg2mU7d"
    await import_account_from_six_parts(six_parts, env="smb_android")
    
    # Cria cliente (substitua pelo seu número)
    account_id = "201288480973"  # Substitua pelo seu número
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
        to = "559885700260"  # Substitua pelo número de destino
        await client.sync_devices(jids=[to])

        text = "Hello! Esta é uma mensagem de teste do ZowPy."
        print(f"📤 Enviando mensagem para {to}...")
        msg_id = await client.send_text(to, text)
        print(f"✅ Mensagem enviada! ID: {msg_id}")
        
        # # Aguarda resposta (timeout de 30s)
        # # Estilo whatsmeow: pode filtrar por remetente, tipo, etc.
        # print("⏳ Aguardando resposta...")
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
        await asyncio.sleep(120)
        
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



