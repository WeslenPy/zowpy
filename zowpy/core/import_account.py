"""
Importação de contas a partir do formato 6-parts.

Formato: phone,pk1,sk1,pk2,sk2,sixth

Baseado na implementação do zowsuplib.
"""

import base64
import json
from dataclasses import dataclass, asdict
from typing import Optional
from loguru import logger

from zowpy.utils.tools import WATools, StorageTools

from ..consonance.structs.keypair import KeyPair
from ..db.manager import AxolotlManager
from ..db.models import Account
from ..db.pool import AsyncDatabasePool
from ..config.bot_env import BotEnv
from ..config.device_env import DeviceEnv
from ..config.network import NetworkEnv
from ..utils.phone import PhoneUtils
from ..config.manager import Config
from ..profile.profile import AsyncProfile
import names



async def import_account_from_six_parts(
    six_parts_data: str,
    *,
    env: str = "android",
    db_pool: Optional[AsyncDatabasePool] = None,
) -> str:
    """
    Importa uma conta nova a partir de uma string no formato 6-parts.
    
    A string deve ter 6 campos separados por vírgula, no formato gerado
    pelo script export6.py:
    
        phone,pk1,sk1,pk2,sk2,sixth
    
    Onde:
        - phone: número de telefone da conta
        - pk1: chave pública 1 (do client_static_keypair) em base64
        - sk1: chave privada 1 (do client_static_keypair) em base64
        - pk2: chave pública 2 (da identidade Axolotl) em base64 (sem o primeiro byte)
        - sk2: chave privada 2 (da identidade Axolotl) em base64
        - sixth: base64(phone.encode() + "#".encode() + config.id)
    
    A importação realiza, em alto nível:
    - verifica se a conta já existe no banco de dados (se sim, retorna sem importar)
    - cria/atualiza o registro da conta no DB unificado (`Account`)
    - persiste a configuração de perfil (Config) em `AccountState`
    - grava as chaves de identidade locais na store Axolotl (AsyncAxolotlStore)
    
    Args:
        six_parts_data: String com 6 campos separados por vírgula
        env: Ambiente do dispositivo (default: "android")
        db_pool: Pool de banco de dados (opcional, cria padrão se não fornecido)
    
    Returns:
        str: Número de telefone (account_id) da conta importada
    
    Raises:
        ValueError: Se o formato dos dados for inválido
    """
    # Cria db_pool padrão se não fornecido
    if db_pool is None:
        from ..config.settings import settings
        db_pool = AsyncDatabasePool(settings.zowpy_db_url)
        await db_pool.initialize()
        
        # Inicializa banco de dados (cria tabelas se não existirem)
        from ..db import init_db
        await init_db(db_pool=db_pool)
    
    parts = [p.strip() for p in six_parts_data.split(",")]
    if len(parts) != 6:
        raise ValueError("6-parts-account-data inválido: esperado 6 campos separados por vírgula")
    
    phone, pk1, sk1, pk2, sk2, sixth = parts
    
    # Verifica se a conta já existe no banco de dados
    async with db_pool.get_session() as session:
        from sqlalchemy import select
        result = await session.execute(select(Account).filter_by(phone=phone))
        existing_account = result.scalar_one_or_none()
        if existing_account:
            logger.info(f"Conta {phone} já existe no banco de dados, pulando importação")
            return phone
    
    logger.info(f"Importando conta {phone}...")
    
    # Reconstrói o client_static_keypair a partir de pk1/sk1 (mesma lógica de import6.py)
    client_static_keypair_str = base64.b64encode(
        base64.b64decode(sk1) + base64.b64decode(pk1)
    ).decode()
    kp = KeyPair.from_bytes(base64.b64decode(client_static_keypair_str))
    
    # Decodifica o sexto campo e extrai o id (últimos 20 bytes)
    if len(sixth) % 4 != 0:
        sixth = sixth + "=" * (4 - len(sixth) % 4)
    sixth_bytes = base64.b64decode(sixth)
    account_id_bytes = sixth_bytes[-20:]
    
    # Cria um ambiente mínimo apenas para gerar fdid de forma consistente
    device_env = DeviceEnv(env, random=True)
    network_env = NetworkEnv(NetworkEnv.TYPE_DIRECT)
    bot_env = BotEnv(device_env, network_env)
    
    # Deriva país (código de chamada) e escolhe um par mcc/mnc plausível
    cc = PhoneUtils.getMobileCC(phone)
    mcc, mnc = PhoneUtils.get_mcc_mnc(phone)
    if not mcc:
        mcc = "000"
    if not mnc:
        mnc = "000"
    
    
    # Cria objeto Config (igual ao zowsuplib)
    config = Config(
        pushname=names.get_full_name() + "X",
        cc=cc,
        mcc=mcc,
        mnc=mnc,
        sim_mcc=mcc,
        sim_mnc=mnc,
        phone=phone,
        client_static_keypair=kp,
        fdid=WATools.generatePhoneId(device_env),
        expid=WATools.generateDeviceId(),
        id=account_id_bytes,
        os_name=device_env.getOSName(),
        os_version=device_env.getOSVersion(),
        manufacturer=device_env.getManufacturer(),
        device_name=device_env.getDeviceName2(),
        device_model_type=device_env.getDeviceModelType(),
    )
    
    # Garante que a conta exista e atualiza alguns metadados básicos
    async with db_pool.get_session() as session:
        from sqlalchemy import select
        result = await session.execute(select(Account).filter_by(phone=phone))
        account = result.scalar_one_or_none()
        
        if account is None:
            account = Account(phone=phone)
            session.add(account)
            await session.flush()
        
        account.pushname = config.pushname
        account.env = env
        # Inicializa os campos de status com valores padrão
        account.is_logged_in = False
        account.has_restriction = False
        account.is_initialized = False
        
        await session.commit()
    
    profile = AsyncProfile(phone, db_pool=db_pool)
    await profile.write_config(config,db_pool=db_pool)
    
    from ..db.store.sqlaxolotlstore import SqlAxolotlStore
    store = SqlAxolotlStore(phone, db_pool)
    axolotl_manager = AxolotlManager(store, phone)
    
    pub_raw = base64.b64decode(pk2)
    if len(pub_raw) == 32:
        pub_key = b"\x05" + pub_raw
    else:
        logger.info("6-parts account pode estar em formato não padrão; usando chave pública como recebido")
        pub_key = pub_raw
    
    priv_key = base64.b64decode(sk2)
    
    await axolotl_manager._store.updateLocalIdentityKeys(
        axolotl_manager.registration_id,
        pub_key,
        priv_key,
        deviceid=0
    )
    
    logger.info(f"Conta {phone} importada com sucesso no DB unificado")
    return phone
