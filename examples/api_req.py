"""
Exemplo de uso dos métodos de registration na API de alto nível.

Métodos demonstrados:
- registration_exists
- registration_request_code
- registration_register
"""

import asyncio
import os

from zowpy.api.client import ZowPyClient


async def main() -> None:
    # Defina o número da conta (com DDI), por exemplo: 5511999999999
    account_id = "201203250554"

    # Código de verificação (use o recebido por SMS/voz).
    # Se vazio, o exemplo pula o passo de register.

    client = ZowPyClient(account_id=account_id, env="android")

    # Opcional: configure proxy (formato exemplo: user:pass@host:port)
    # await client.set_proxy("127.0.0.1:8080", proxy_type="http")

    exists_result = await client.registration_request_exists(
        phone_number=account_id,
        encrypt=False,
    )
    print("exists_result:", exists_result.status)
    
    
    # unban = await client.registration_unban(
    #     token="Ae2KoNdHvKGdnFrGNyL17ngXwfqom3L0bncWavP-9RIehyYdU5FELuFR3H4gCRlakU-AEagVG96wWMZFjwr9HjYypykAxDi1ax28hJPb5km12F335fcDRhcNaZfrEijtKT7uxkXpV3w63fJmcjIRCCmA7huwPC3kgNtTyPdtcygQjWQiHnkzwdhPfrXN6mE8n7BhE00iNAySmtQ_16yTONPVBg",
    #     phone_number=account_id,
    # )
    
    



if __name__ == "__main__":
    asyncio.run(main())
