"""
Exemplo avançado de uso do ZowPy.

Demonstra uso de múltiplas contas e eventos.
"""

import asyncio
from zowpy import AccountManager
from zowpy.core.import_account import import_account_from_six_parts


async def main():
    """Exemplo avançado com múltiplas contas"""
    # six_parts= "201212270497,G4xt4XNboT4nt209OJ4nxB1e5BMoZ647c/Sd6asBEzs=,UBYb9eQ2qu82oKj1VSb8q0NctcO2GhKWDJ1oEHQZqmI=,njGwWRJkx9IN/gkEMlt6X68XgdC6+5ovCF5O+2CYFCo=,UIDdJGFNlxvI0LW5tMDruLAGKtNZCTUQMvu/djhJD0E=,MjAxMjEyMjcwNDk3I33kteKf/8uRCS4S9r//9yvhXRYU"
    six_parts = "201228276695,Apxk7RvapZh/uBUcLbaYvguEgd0mHyP3jSN6wfy3cTk=,UDBcdUHsAYTr9i+X4/ehoAAvlZr6WGBy5lAPst2Yz0w=,4B+wLEZzb+PWkRI2l8C8Kr7togg86hdmsiq46pdl4TU=,8LL3kDyHnPlArTFz5hztHugaGAXRbAnWplLZAes7Hno=,MjAxMjI4Mjc2Njk1I5ck5MpKH/TfJeN6V/6YUhg0w5s+"
    await import_account_from_six_parts(six_parts, env="smb_android")
    # Cria manager
    manager = AccountManager()
    
    # Adiciona contas
    account1 = await manager.add_account("201208868278")
    account2 = await manager.add_account("201212270497")
    account3 = await manager.add_account("201228276695")
    
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
        

        to = "120363423929565689@g.us"

        await account1.join_group_with_link("IkUXAl5oMK5I0ZXp9dauhy")
        await account2.join_group_with_link("IkUXAl5oMK5I0ZXp9dauhy")
        await account3.join_group_with_link("IkUXAl5oMK5I0ZXp9dauhy")


        # Envia mensagens
        msg_id1 = await account1.send_text(to, "Hello from account1!")
        msg_id2 = await account2.send_text(to, "Hello from account2!")
        msg_id3 = await account3.send_text(to, "Hello from account3!")
        
        await account1.send_image(to, "https://www.google.com/images/branding/googlelogo/1x/googlelogo_color_272x92dp.png")

        await account2.send_sticker(to, "https://s3-bucket-waconnect.s3.us-west-2.amazonaws.com/static/api/5981fc257c8d45b8dd74eeccc674637baff025d19de3eeec877e571e8015732a7777214b675efc19f8d319f6daebb011f5b0d3ea0f52f721dbe015345c37a805.webp")

        await account1.send_audio(to, "https://s3-bucket-waconnect.s3.us-west-2.amazonaws.com/static/api/f5ba3d484c1f8a182648272831cdcbe6155f686c8600edc703c3a75965b2a7da924d69c8d9591e32c28a1b21ab2b9820f7ca06578420839f68996c76cd6090b1.ogg",ptt=True)
        
        await account2.send_document(to, "https://s3-bucket-waconnect.s3.us-west-2.amazonaws.com/static/api/f5ba3d484c1f8a182648272831cdcbe6155f686c8600edc703c3a75965b2a7da924d69c8d9591e32c28a1b21ab2b9820f7ca06578420839f68996c76cd6090b1.ogg")
        
        
        print(f"Messages sent: {msg_id1}, {msg_id2}")
        
        # Aguarda um pouco
        await asyncio.sleep(10)
        
    finally:
        # Desconecta todas
        await manager.shutdown()


if __name__ == "__main__":
    asyncio.run(main())












