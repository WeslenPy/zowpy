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
logger.add("logs/get_profile_picture.log", level="DEBUG")


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
    # six_parts= "14373206374,4ljWhbt1yKIN/APYKt8taDPj4kbsULb552rxRJvX0Wk=,cPjOBZVjlURZBJxZOzE4HdkUEjrAA9K/ApZyo4rgiEU=,yIdbWY5IFfBhxhGT6AO3xwlYGQ21ZThe98Lr/Cg0phM=,6CYNIsougyZ3ymOJbfI8lwK+P+6sd/WOLwMO/a2OUHU=,NTU1NTkyNDgxMDY0OSMFw8GN5rYImqEJAm9pObYCtwosxw=="
    # six_parts = "5555924810649,4ljWhbt1yKIN/APYKt8taDPj4kbsULb552rxRJvX0Wk=,cPjOBZVjlURZBJxZOzE4HdkUEjrAA9K/ApZyo4rgiEU=,yIdbWY5IFfBhxhGT6AO3xwlYGQ21ZThe98Lr/Cg0phM=,6CYNIsougyZ3ymOJbfI8lwK+P+6sd/WOLwMO/a2OUHU=,NTU1NTkyNDgxMDY0OSMFw8GN5rYImqEJAm9pObYCtwosxw=="
    # six_parts = "201201814380,do2SERU4/9Yj55lReaRN6aZKJQ9K3RiKXrw3da4rHm8=,6D00PFIHKSnRufG7+9NU9T5WTxuViefuu61LIxUl8Hg=,kr9WxLubsiVQmcdRsOiZ31h0khcADnA6zBmiRU1TvGk=,wCCqKCgpt1FRJxq3Q0kydhXmnk9h8Oixw94Y9FZCzEE=,MjAxMjAxODE0MzgwI1RJcf7mAfypjMTAyTeeZgV3J9ZD"
    # six_parts = "201289168953,MCVXsjVe8MawoI1knngwMgG3jT9uIiMkQaomKIy+2h8=,AHO8TSNhrJZS2fCvuW4J4tkeBknhCyQx16EYyKsrNng=,JfoetzyUPj6oUokxsftZa6o3eukx6WXNTtfKj6eVhQk=,6GR1abYzZeA95EYpoSTr1abe50JnHH0fNt4NqyMqy3Q=,MjAxMjg5MTY4OTUzIwiPgotfI6grLeCaitnx2+gEC9jc"
    six_parts =  "201207737061,RgobkhZ55SZw2dc3OW0YCUfCax+OtcF/QxpFxn9iGA4=,IJEWbfDYvkE3KXUtlk+/NbDb7hmzM58LYcf04klVYXU=,eDk5dV78OxZYQrX6XjlRCMeKvR/dW1MKTEoXZ8VYaG8=,uHHQEh7so7ZRA+wlLuk8+PBX8wQd3/QG9gA3eCcaFnk=,MjAxMjA3NzM3MDYxI6/labSowjIdCR65F+xEXAciIvcD"
    env = "smb_android"

    await import_account_from_six_parts(six_parts,env=env)

    account_id = six_parts.split(",")[0]
    
    client = ZowPyClient(account_id,env=env)
    client.set_proxy("104.239.17.120:6186:mwqfvavl:iggqj6pm1ptt", "http")
    
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
        to = "120363425653832734"
        # to = "5511930023692"
        print(f" Enviando mensagem para {to}...")

        print(f"\n📤 Exemplo: Enviando mídia usando send_media_direct...")


        text = "Ola, tudo bem?"

        # code = "FHeOqMRR7r4BNB7hvXHudd"

        # logger.info(f"Grupos: {groups}")

        await client.join_group_with_code("FHeOqMRR7r4BNB7hvXHudd")
        
        # result=  await client.get_group_invite_code(to)
        # groups = await client.list_groups()
        # result= await client.get_group_info(to)
        # logger.info(f"Resultado: {groups}")
        
        # result = await client.create_group(text, [])
        # print(f"Grupo criado com sucesso: {result}")


        # await client.set_profile_name("novo")
        avatar = await client.get_user_info(to)
        
        print(f"Avatar: {avatar}")

        # await client.send_text(to, text)
        while True:
            print(f"Mensagem: {text}")
            await client.send_status(media_type="image",file_path_or_url="https://www.google.com/images/branding/googlelogo/1x/googlelogo_color_272x92dp.png")
            await asyncio.sleep(10)
            
            await client.start_recording(to)
            await asyncio.sleep(10)
            await client.send_audio(to,"https://s3-bucket-waconnect.s3.us-west-2.amazonaws.com/static/api/f5ba3d484c1f8a182648272831cdcbe6155f686c8600edc703c3a75965b2a7da924d69c8d9591e32c28a1b21ab2b9820f7ca06578420839f68996c76cd6090b1.ogg")
            await client.stop_recording(to)
            await asyncio.sleep(10)


            await client.send_document(to,"https://s3-bucket-waconnect.s3.us-west-2.amazonaws.com/static/api/5981fc257c8d45b8dd74eeccc674637baff025d19de3eeec877e571e8015732a7777214b675efc19f8d319f6daebb011f5b0d3ea0f52f721dbe015345c37a805.webp")
            await asyncio.sleep(10)
            await client.send_sticker(to,"https://s3-bucket-waconnect.s3.us-west-2.amazonaws.com/static/api/5981fc257c8d45b8dd74eeccc674637baff025d19de3eeec877e571e8015732a7777214b675efc19f8d319f6daebb011f5b0d3ea0f52f721dbe015345c37a805.webp")
            await asyncio.sleep(10)

            await client.start_typing(to)
            await asyncio.sleep(4)
            message_id = await client.send_text(to, text)
            print(f"Mensagem enviada: {message_id}")
            await client.stop_typing(to)


            await asyncio.sleep(300)



        # await client.reply_message(to,"tudo",reply_message_id=message_id,quoted="tudo",from_me=True)

        # await client.send_reaction(to=to,message_id=message_id,reaction="❤️",from_me=True)
        # await client.remove_reaction(to=to,message_id=message_id,from_me=True)


        # await client.send_status(media_type="video",file_path_or_url="./videoplayback.mp4",caption="teste")
        # await client.send_status(media_type="audio",file_path_or_url="https://s3-bucket-waconnect.s3.us-west-2.amazonaws.com/static/api/f5ba3d484c1f8a182648272831cdcbe6155f686c8600edc703c3a75965b2a7da924d69c8d9591e32c28a1b21ab2b9820f7ca06578420839f68996c76cd6090b1.ogg")
                                # text_color=client._generate_random_text_color(),
                                # background_color=client._generate_random_background_color())




        # await client.send_image(to,"https://www.google.com/images/branding/googlelogo/1x/googlelogo_color_272x92dp.png")
      
        # while True:
        #     print(f"Enviando mensagem para {to}...")
        

        await asyncio.sleep(30)
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




