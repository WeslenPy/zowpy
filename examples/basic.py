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
    six_parts= "14373206374,4ljWhbt1yKIN/APYKt8taDPj4kbsULb552rxRJvX0Wk=,cPjOBZVjlURZBJxZOzE4HdkUEjrAA9K/ApZyo4rgiEU=,yIdbWY5IFfBhxhGT6AO3xwlYGQ21ZThe98Lr/Cg0phM=,6CYNIsougyZ3ymOJbfI8lwK+P+6sd/WOLwMO/a2OUHU=,NTU1NTkyNDgxMDY0OSMFw8GN5rYImqEJAm9pObYCtwosxw=="
    # six_parts = "5555924810649,4ljWhbt1yKIN/APYKt8taDPj4kbsULb552rxRJvX0Wk=,cPjOBZVjlURZBJxZOzE4HdkUEjrAA9K/ApZyo4rgiEU=,yIdbWY5IFfBhxhGT6AO3xwlYGQ21ZThe98Lr/Cg0phM=,6CYNIsougyZ3ymOJbfI8lwK+P+6sd/WOLwMO/a2OUHU=,NTU1NTkyNDgxMDY0OSMFw8GN5rYImqEJAm9pObYCtwosxw=="
    
    # await import_account_from_six_parts(six_parts, env="android")

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
        to = "120363423929565689"
        # to = "559885700260"
        print(f" Enviando mensagem para {to}...")

        print(f"\n📤 Exemplo: Enviando mídia usando send_media_direct...")


        text = "Ola, tudo bem?"

        code = "IkUXAl5oMK5I0ZXp9dauhy"

        # groups = await client.list_groups()
        # logger.info(f"Grupos: {groups}")

        # await client.join_group_with_code("IkUXAl5oMK5I0ZXp9dauhy")
        
        # result=  await client.get_group_invite_code(to)
        # result= await client.get_group_info(to)
        # logger.info(f"Resultado: {groups}")
        
        # result = await client.create_group(text, [])
        # print(f"Grupo criado com sucesso: {result}")


        await client.start_typing(to)
        await asyncio.sleep(4)
        await client.send_text(to, text)
        await client.stop_typing(to)
        await client.send_image(to,"https://www.google.com/images/branding/googlelogo/1x/googlelogo_color_272x92dp.png")
        await client.send_audio(to,"https://s3-bucket-waconnect.s3.us-west-2.amazonaws.com/static/api/f5ba3d484c1f8a182648272831cdcbe6155f686c8600edc703c3a75965b2a7da924d69c8d9591e32c28a1b21ab2b9820f7ca06578420839f68996c76cd6090b1.ogg")
        await client.send_document(to,"https://s3-bucket-waconnect.s3.us-west-2.amazonaws.com/static/api/5981fc257c8d45b8dd74eeccc674637baff025d19de3eeec877e571e8015732a7777214b675efc19f8d319f6daebb011f5b0d3ea0f52f721dbe015345c37a805.webp")
        await client.send_sticker(to,"https://s3-bucket-waconnect.s3.us-west-2.amazonaws.com/static/api/5981fc257c8d45b8dd74eeccc674637baff025d19de3eeec877e571e8015732a7777214b675efc19f8d319f6daebb011f5b0d3ea0f52f721dbe015345c37a805.webp")
        # while True:
        #     print(f"Enviando mensagem para {to}...")
        

        await asyncio.sleep(10)
        print("\n🔄 Desconectando...")
        await client.disconnect()
    
    except KeyboardInterrupt:
        await client.disconnect()
        print("\n🛑 Interrupção recebida, desconectando...")
    
    except Exception as e:
        print(f"❌ Erro: {e}")
        logger.exception("Erro no exemplo básico")
    
 
if __name__ == "__main__":
    asyncio.run(main())
    logger.info("Fim do exemplo básico")




