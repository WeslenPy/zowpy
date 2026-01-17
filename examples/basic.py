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
    Exemplo básico usando o ZowPy Client.
    
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
    
    Envio de mensagens:
    - send_text() agora segue o fluxo completo do zowsuplib
    - Sincroniza contatos automaticamente se necessário
    - Aplica validações de segurança (rate limiting, limites diários)
    - Sincroniza dispositivos e obtém chaves automaticamente
    - Criptografa e envia mensagem
    """
    # Importa conta (se necessário)
    six_parts= "201208868278,+PfRJy8TA13JI8rZiQYLnWZ+X0sEYDmB08ZzxiSsWxo=,aL74nYQzRkb3OGioDiAbeCMBadegkXBPO3TE5xf3nFM=,MbuNxcpVZuFg6C4IC2+knQeyvdd+R2icsOSh1vD57Xk=,qCPWUX3807N+/KU4hkogYh9REvvGOxpugFj2CQWIynM=,MjAxMjA4ODY4Mjc4I2nimRzHQYZasFIhLa1u1gEQrfAm"
    await import_account_from_six_parts(six_parts, env="smb_android")
    
    # Cria cliente (substitua pelo seu número)
    account_id = six_parts.split(",")[0]  # Substitua pelo seu número
    client = ZowPyClient(account_id)
    
    # Eventos
    @client.on_message
    async def handle_message(message):
        """Handler de mensagens recebidas"""
        logger.info(f"Mensagem recebida: {message}")
        print(f"📨 Mensagem recebida de {message.get('from', 'unknown')}: {message.get('text', '')}")
    
    @client.on_connected
    async def handle_connected(data=None):
        """Handler de conexão estabelecida"""
        # data contém informações como {'account_id': '...'}
        account_id = data.get('account_id', 'unknown') if data else 'unknown'
        print(f"✅ Conectado ao WhatsApp! Account: {account_id}")
    
    @client.on_disconnected
    async def handle_disconnected(data=None):
        """Handler de desconexão"""
        # data contém informações como {'account_id': '...'}
        account_id = data.get('account_id', 'unknown') if data else 'unknown'
        print(f"❌ Desconectado do WhatsApp. Account: {account_id}")
    
    try:
        # Conecta (fluxo linear: conexão → handshake → autenticação)
        print("🔄 Conectando ao WhatsApp...")
        await client.connect()
        print("✅ Cliente conectado e autenticado!")
        
        # Envia mensagem
        # Nota: send_text() agora sincroniza contatos automaticamente se necessário
        # seguindo o fluxo completo do zowsuplib (assure_contacts_and_send)
        # to = "559885700260"  # Substitua pelo número de destino
        to = "559885700260"
        text = "Hello! Esta é uma mensagem de teste do ZowPy."
        print(f"📤 Enviando mensagem para {to}...")
        # send_text() agora:
        # 1. Valida conta (restrição, limite diário)
        # 2. Sincroniza contato automaticamente se for novo
        # 3. Aplica rate limiting
        # 4. Sincroniza dispositivos se necessário
        # 5. Obtém chaves e cria sessões se necessário
        # 6. Criptografa e envia mensagem
        msg_id = await client.send_text(to, text)

        # await client.sync_contacts([to], mode="delta", context="interactive")
        # print(f"✅ Mensagem enviada! ID: {msg_id}")
        
        # Exemplo: enviar para múltiplos destinos (separados por vírgula)
        # to_multiple = "559885700260,559885700261"
        # msg_id = await client.send_text(to_multiple, "Mensagem para múltiplos contatos")
        
        
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





