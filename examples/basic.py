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
    # six_parts = "201288305948,gehExdJAhPTAkqd5LDQ0zsBmUuuvP837jAQHNgndgnk=,+I0r7c+ZSZl6HmmY9uUI8E3ki4+ZRQ3trbYGISvLem0=,HiqT5eRDdur33fCRLW/UmUi8Sm/c+mEL+ajC/pIE/nk=,AAOlZ9VKgYuEvIetCouS+BS2DXCLd5XS2PispXKClkw=,MjAxMjg4MzA1OTQ4I6EaQHqQklbEQ2Klo9w0kEh1yPOB"
    # six_parts= "201208868278,+PfRJy8TA13JI8rZiQYLnWZ+X0sEYDmB08ZzxiSsWxo=,aL74nYQzRkb3OGioDiAbeCMBadegkXBPO3TE5xf3nFM=,MbuNxcpVZuFg6C4IC2+knQeyvdd+R2icsOSh1vD57Xk=,qCPWUX3807N+/KU4hkogYh9REvvGOxpugFj2CQWIynM=,MjAxMjA4ODY4Mjc4I2nimRzHQYZasFIhLa1u1gEQrfAm"
    
    # six_parts = "201223930365,yn393U8sbIKti1Efdnbk0e2Q6m5yUwYOtLlnYVfPP0Q=,MLamPzWnhfKj5JPcnBPEEp6YIcomYbYrUPXdlrf/qEQ=,GSsGb7EHKfeAHBQRnXFRjlUeo7jS7Zh0LdoyUPCraiQ=,0G7eIsr2cQTY0e5bj/+ax5COdC3tP59B3lz8mlqvD0U=,MjAxMjIzOTMwMzY1IwN6OSuFVT02qBFhrRnOYQFckUMB"
    
    # six_parts = "201221738157,Z2If9htLbmWogKiefrdlAzHwQHjkwfPAvkTmucpoQBE=,kGNH79dHSLZ7xIJZapNvT17jaWC79hgfxx074nVSt0A=,POI3x69j0om0xaNPOYG+kqKfW0HpTq9lpfgBTBo5xnw=,yJuW4Ikd0eB0001p0ss9f2EiA6GitdVGTUYdooQr6FA=,MjAxMjIxNzM4MTU3I6WKbYijHPwkd9k4qepyoM2bPTlR"
    
    six_parts = "201228276695,Apxk7RvapZh/uBUcLbaYvguEgd0mHyP3jSN6wfy3cTk=,UDBcdUHsAYTr9i+X4/ehoAAvlZr6WGBy5lAPst2Yz0w=,4B+wLEZzb+PWkRI2l8C8Kr7togg86hdmsiq46pdl4TU=,8LL3kDyHnPlArTFz5hztHugaGAXRbAnWplLZAes7Hno=,MjAxMjI4Mjc2Njk1I5ck5MpKH/TfJeN6V/6YUhg0w5s+"
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
        # to = "559885700260"
        to = "120363404389347069@g.us"
        text = "Hello! Esta é uma mensagem de teste do ZowPy."
        print(f"📤 Enviando mensagem para {to}...")
        # msg_id = await client.send_text(to, text)

        # Exemplo de uso do send_media_direct
        # Baseado nos logs do zowsuplib (multi.log linhas 24222-24229)
        # Valores extraídos do log de envio de imagem PNG
        print(f"\n📤 Exemplo: Enviando mídia usando send_media_direct...")
        

        # result = await client.list_groups()
        # print(result)

        # await client.send_image(to, "https://www.google.com/images/branding/googlelogo/1x/googlelogo_color_272x92dp.png")

        # await client.send_sticker(to, "https://s3-bucket-waconnect.s3.us-west-2.amazonaws.com/static/api/5981fc257c8d45b8dd74eeccc674637baff025d19de3eeec877e571e8015732a7777214b675efc19f8d319f6daebb011f5b0d3ea0f52f721dbe015345c37a805.webp")
        
        
        # await client.send_audio(to, "https://s3-bucket-waconnect.s3.us-west-2.amazonaws.com/static/api/f5ba3d484c1f8a182648272831cdcbe6155f686c8600edc703c3a75965b2a7da924d69c8d9591e32c28a1b21ab2b9820f7ca06578420839f68996c76cd6090b1.ogg",ptt=True)
        
        # await client.send_document(to, "https://s3-bucket-waconnect.s3.us-west-2.amazonaws.com/static/api/f5ba3d484c1f8a182648272831cdcbe6155f686c8600edc703c3a75965b2a7da924d69c8d9591e32c28a1b21ab2b9820f7ca06578420839f68996c76cd6090b1.ogg")
        
        # print(f"✅ Mensagem enviada! ID: {msg_id}")
        
        # Mantém o cliente online indefinidamente
        # O keepalive é enviado automaticamente a cada 20 segundos
        # A reconexão automática é tratada no handler on_disconnected
        while running:
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


