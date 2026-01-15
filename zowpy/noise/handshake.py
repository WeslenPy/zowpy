"""
Async WA Handshake - Handshake totalmente assíncrono.

Refatora WAHandshake para async, mantendo lógica IK/XX.
"""

import asyncio
from typing import Optional, Tuple
from loguru import logger
from ..noise.dissononce_extras.processing.symmetricstate_wa import WASymmetricState
from dissononce.processing.impl.handshakestate import HandshakeState
from dissononce.extras.processing.handshakestate_guarded import GuardedHandshakeState
from dissononce.extras.processing.handshakestate_switchable import SwitchableHandshakeState
from dissononce.processing.handshakepatterns.interactive.IK import IKHandshakePattern
from dissononce.processing.handshakepatterns.interactive.XX import XXHandshakePattern
from dissononce.processing.modifiers.fallback import FallbackPatternModifier
from dissononce.processing.impl.cipherstate import CipherState
from dissononce.cipher.aesgcm import AESGCMCipher
from dissononce.hash.sha256 import SHA256Hash
from dissononce.dh.keypair import KeyPair
from dissononce.dh.x25519.public import PublicKey as DissononcePublicKey
from dissononce.dh.private import PrivateKey
from dissononce.dh.x25519.x25519 import X25519DH
from dissononce.extras.dh.dangerous.dh_nogen import NoGenDH
from dissononce.exceptions.decrypt import DecryptFailedException
from google.protobuf.message import DecodeError

from .stream import AsyncSegmentedStream
from .structs import PublicKey

# Imports condicionais para compatibilidade
from .proto import wa5_pb2
from .certman.certman import AsyncCertMan
from .util import ByteUtil


class HandshakeFailedException(Exception):
    """Handshake falhou"""
    pass


class NewRemoteStaticException(Exception):
    """Nova chave estática remota detectada"""
    def __init__(self, server_hello):
        self.server_hello = server_hello
        super().__init__("New remote static detected")


class AsyncWAHandshake:
    """
    Handshake totalmente assíncrono para WhatsApp Noise Protocol.
    
    Implementação moderna e assíncrona baseada no zowsuplib, mantendo
    compatibilidade com o protocolo Noise do WhatsApp.
    
    Fluxo:
    1. Se rs (remote static) estiver presente → Handshake IK
       - Se servidor retornar nova chave estática → Fallback para XX
    2. Se rs não estiver presente → Handshake XX
    
    Todas as operações são assíncronas (await) para não bloquear o event loop.
    """
    
    def __init__(self, version_major: int = 6, version_minor: int = 3):
        self._prologue = b"WA" + bytearray([version_major, version_minor])
        self._handshakestate: Optional[SwitchableHandshakeState] = None
        self.mode = None
        self.identity = None
        self.regid = None
        self.signedprekey = None
        self.deviceid = None
    
    def setmode(self, mode):
        """Define modo de handshake"""
        self.mode = mode
    
    def setIdentity(self, value):
        """Define identidade"""
        self.identity = value
    
    def setSignedPreKey(self, value):
        """Define signed prekey"""
        self.signedprekey = value
    
    def setRegistrationId(self, value):
        """Define registration ID"""
        self.regid = value
    
    def setDeviceId(self, value):
        """Define device ID"""
        self.deviceid = value
    
    async def perform(
        self,
        client_config,
        stream: AsyncSegmentedStream,
        s: KeyPair,
        rs: Optional[PublicKey] = None,
        e: Optional[KeyPair] = None
    ) -> Tuple[CipherState, CipherState]:
        """
        Executa handshake de forma totalmente assíncrona.
        Aguarda dados, não bloqueia.
        
        Args:
            client_config: Configuração do cliente
            stream: Stream assíncrono
            s: Chave estática local
            rs: Chave estática remota (opcional)
            e: Chave efêmera (opcional)
        
        Returns:
            Tuple[CipherState, CipherState]: Par de cipher states (send, recv)
        
        Raises:
            HandshakeFailedException: Se handshake falhar
        """
        logger.info("Iniciando handshake assíncrono")
        
        # Configura DH
        dh = X25519DH()
        if e is not None:
            dh = NoGenDH(dh, PrivateKey(e.private.data))
        
        # Inicializa handshake state
  
        self._handshakestate = SwitchableHandshakeState(
            GuardedHandshakeState(
                HandshakeState(
                    WASymmetricState(
                        CipherState(
                            AESGCMCipher()
                        ),
                        SHA256Hash()
                    ),
                    dh
                )
            )
        ) 


        logger.debug(f"KeyPair s: {s}")
        # Cria dissononce keypair
        dissononce_s = KeyPair(
            DissononcePublicKey(s.public.data),
            PrivateKey(s.private.data)
        )
        dissononce_rs = DissononcePublicKey(rs.data) if rs else None

        
        # Cria client payload
        client_payload = self._create_full_payload(client_config, s)
        
        try:
            if rs is not None:
                logger.info("Usando handshake IK (rs presente)")
                try:
                    cipherstatepair = await self._perform_ik_handshake(
                        stream, client_payload, dissononce_s, dissononce_rs
                    )
                    logger.info("Handshake IK concluído")
                except NewRemoteStaticException as ex:
                    logger.warning("Nova chave estática remota detectada, fazendo fallback para XX")
                    cipherstatepair = await self._switch_handshake_xx_fallback(
                        stream, dissononce_s, client_payload, ex.server_hello
                    )
                    logger.info("Handshake XX fallback concluído")
            else:
                logger.info("Usando handshake XX (rs ausente)")
                cipherstatepair = await self._perform_xx_handshake(
                    stream, client_payload, dissononce_s
                )
                logger.info("Handshake XX concluído")
            
            return cipherstatepair
            
        except DecryptFailedException as e:
            logger.error(f"Erro de descriptografia: {e}")
            raise HandshakeFailedException(e) from e
        except DecodeError as e:
            logger.error(f"Erro de decodificação: {e}")
            raise HandshakeFailedException(e) from e
    
    async def _perform_ik_handshake(
        self,
        stream: AsyncSegmentedStream,
        client_payload,
        s: KeyPair,
        rs: PublicKey
    ) -> Tuple[CipherState, CipherState]:
        """
        Executa handshake IK de forma totalmente assíncrona.
        """
        # Inicializa handshake IK
        self._handshakestate.initialize(
            handshake_pattern=IKHandshakePattern(),
            initiator=True,
            prologue=self._prologue,
            s=s,
            rs=rs
        )
        
        # Cria mensagem
        message_buffer = bytearray()
        self._handshakestate.write_message(
            client_payload.SerializeToString(),
            message_buffer
        )
        
        
        logger.debug(f"[HANDSHAKE-IK] Mensagem preparada: {len(message_buffer)} bytes")
        # Split: ephemeral (32 bytes) + static (48 bytes) + payload (restante)
        # Nota: O terceiro parâmetro len(message_buffer) é usado para pegar o restante
        # A implementação do ByteUtil.split trata isso corretamente
        ephemeral_public, static_public, payload = ByteUtil.split(
            bytes(message_buffer), 32, 48, len(message_buffer)
        )

        
        handshakemessage = wa5_pb2.HandshakeMessage()
        client_hello = wa5_pb2.HandshakeMessage.ClientHello()
        client_hello.ephemeral = ephemeral_public
        client_hello.static = static_public
        client_hello.payload = payload
        handshakemessage.client_hello.MergeFrom(client_hello)
        
        # Serializa mensagem
        serialized = handshakemessage.SerializeToString()
        logger.info(f"[HANDSHAKE-IK] Enviando client_hello: {len(serialized)} bytes")
        logger.debug(f"[HANDSHAKE-IK] ClientHello: ephemeral={len(ephemeral_public)}, static={len(static_public)}, payload={len(payload)}")
        
        # Envia - await, não bloqueia
        await stream.write_segment(serialized)
        logger.info("[HANDSHAKE-IK] Client hello enviado via stream.write_segment(), aguardando server hello")
        
        # Aguarda resposta - await, não bloqueia
        logger.debug("[HANDSHAKE-IK] Aguardando server_hello via stream.read_segment()...")
        segment_data = await stream.read_segment()
        logger.info(f"[HANDSHAKE-IK] Dados recebidos: {len(segment_data)} bytes")
        logger.debug(f"[HANDSHAKE-IK] Primeiros 64 bytes (hex): {segment_data[:64].hex() if len(segment_data) >= 64 else segment_data.hex()}")
        
        incoming_handshakemessage = wa5_pb2.HandshakeMessage()
        try:
            incoming_handshakemessage.ParseFromString(segment_data)
            logger.debug("[HANDSHAKE-IK] Mensagem protobuf parseada com sucesso")
        except Exception as e:
            logger.error(f"[HANDSHAKE-IK] Erro ao fazer parse da mensagem: {e}")
            logger.debug(f"[HANDSHAKE-IK] Dados recebidos (hex completo): {segment_data.hex()}")
            raise
        
        # Verifica campos presentes
        has_client_hello = incoming_handshakemessage.HasField("client_hello")
        has_server_hello = incoming_handshakemessage.HasField("server_hello")
        has_client_finish = incoming_handshakemessage.HasField("client_finish")
        
        logger.debug(f"[HANDSHAKE-IK] Campos presentes: client_hello={has_client_hello}, server_hello={has_server_hello}, client_finish={has_client_finish}")
        
        if not has_server_hello:
            error_msg = "Handshake message does not contain server hello!"
            logger.error(f"[HANDSHAKE-IK] {error_msg}")
            logger.error(f"[HANDSHAKE-IK] Mensagem recebida tem client_hello={has_client_hello}, server_hello={has_server_hello}")
            if has_client_hello:
                logger.error("[HANDSHAKE-IK] ERRO: Recebido client_hello ao invés de server_hello! Possível eco da própria mensagem.")
            raise HandshakeFailedException(error_msg)
        
        server_hello = incoming_handshakemessage.server_hello
        
        # Verifica se há nova chave estática
        if server_hello.HasField("static"):
            raise NewRemoteStaticException(server_hello)
        
        # Processa mensagem
        payload_buffer = bytearray()
        return self._handshakestate.read_message(
            server_hello.ephemeral + server_hello.static + server_hello.payload,
            payload_buffer
        )
    
    async def _perform_xx_handshake(
        self,
        stream: AsyncSegmentedStream,
        client_payload,
        s: KeyPair
    ) -> Tuple[CipherState, CipherState]:
        """
        Executa handshake XX de forma totalmente assíncrona.
        """
        logger.info("[HANDSHAKE-XX] ========== INÍCIO DO HANDSHAKE XX ==========")
        
        # Inicializa handshake XX
        logger.debug(f"[HANDSHAKE-XX] Inicializando handshake state com prologue: {self._prologue.hex()}")
        logger.debug(f"[HANDSHAKE-XX] Chave estática local (s): public={s.public.data.hex()[:32]}..., private={s.private.data.hex()[:32]}...")
        
        self._handshakestate.initialize(
            handshake_pattern=XXHandshakePattern(),
            initiator=True,
            prologue=self._prologue,
            s=s
        )
        logger.debug("[HANDSHAKE-XX] Handshake state inicializado")
        
        
        logger.debug("[HANDSHAKE-XX] Gerando ephemeral do cliente (write_message com payload vazio)")
        ephemeral_public = bytearray()
        self._handshakestate.write_message(b'', ephemeral_public)
        logger.debug(f"[HANDSHAKE-XX] Ephemeral gerado: {len(ephemeral_public)} bytes, hex: {bytes(ephemeral_public).hex()[:64]}...")
        
        handshakemessage = wa5_pb2.HandshakeMessage()
        client_hello = wa5_pb2.HandshakeMessage.ClientHello()
        client_hello.ephemeral = bytes(ephemeral_public)
        handshakemessage.client_hello.MergeFrom(client_hello)
        
        # Serializa mensagem
        serialized = handshakemessage.SerializeToString()
        logger.info(f"[HANDSHAKE-XX] ClientHello preparado: {len(serialized)} bytes")
        logger.debug(f"[HANDSHAKE-XX] ClientHello serializado (hex): {serialized.hex()[:100]}...")
        logger.debug(f"[HANDSHAKE-XX] ClientHello ephemeral: {len(client_hello.ephemeral)} bytes")
        
        # Envia - await, não bloqueia
        logger.debug("[HANDSHAKE-XX] Enviando client_hello via stream.write_segment()...")
        await stream.write_segment(serialized)
        logger.info("[HANDSHAKE-XX] ✓ Client hello enviado, aguardando server hello")
        
        # Aguarda server hello - await, não bloqueia
        logger.debug("[HANDSHAKE-XX] Aguardando server_hello via stream.read_segment()...")
        segment_data = await stream.read_segment()
        logger.info(f"[HANDSHAKE-XX] ✓ Dados recebidos: {len(segment_data)} bytes")
        logger.debug(f"[HANDSHAKE-XX] Dados recebidos (hex completo): {segment_data.hex()}")
        logger.debug(f"[HANDSHAKE-XX] Primeiros 100 bytes (hex): {segment_data[:100].hex() if len(segment_data) >= 100 else segment_data.hex()}")
        
        # Parse do protobuf
        logger.debug("[HANDSHAKE-XX] Fazendo parse do HandshakeMessage protobuf...")
        incoming_handshakemessage = wa5_pb2.HandshakeMessage()
        try:
            incoming_handshakemessage.ParseFromString(segment_data)
            logger.debug("[HANDSHAKE-XX] ✓ Mensagem protobuf parseada com sucesso")
        except Exception as e:
            logger.error(f"[HANDSHAKE-XX] ✗ Erro ao fazer parse da mensagem: {e}")
            logger.error(f"[HANDSHAKE-XX] Tipo do erro: {type(e).__name__}")
            logger.debug(f"[HANDSHAKE-XX] Dados recebidos (hex completo): {segment_data.hex()}")
            logger.debug(f"[HANDSHAKE-XX] Tamanho dos dados: {len(segment_data)} bytes")
            raise HandshakeFailedException(f"Erro ao fazer parse do server hello: {e}") from e

        logger.debug(f"[HANDSHAKE-XX] HandshakeMessage parseado: {incoming_handshakemessage}")
        
        # Verifica campos presentes
        has_client_hello = incoming_handshakemessage.HasField("client_hello")
        has_server_hello = incoming_handshakemessage.HasField("server_hello")
        has_client_finish = incoming_handshakemessage.HasField("client_finish")
        
        logger.info(f"[HANDSHAKE-XX] Campos presentes: client_hello={has_client_hello}, server_hello={has_server_hello}, client_finish={has_client_finish}")
        
        if not has_server_hello:
            error_msg = "Handshake message does not contain server hello!"
            logger.error(f"[HANDSHAKE-XX] ✗ {error_msg}")
            logger.error(f"[HANDSHAKE-XX] Mensagem recebida tem client_hello={has_client_hello}, server_hello={has_server_hello}")
            if has_client_hello:
                logger.error("[HANDSHAKE-XX] ERRO: Recebido client_hello ao invés de server_hello! Possível eco da própria mensagem.")
            raise HandshakeFailedException(error_msg)
        
        server_hello = incoming_handshakemessage.server_hello
        logger.debug(f"[HANDSHAKE-XX] ServerHello extraído")
        
        # Extrai campos do server_hello
        has_ephemeral = server_hello.HasField("ephemeral")
        has_static = server_hello.HasField("static")
        has_payload = server_hello.HasField("payload")
        
        logger.info(f"[HANDSHAKE-XX] ServerHello campos: ephemeral={has_ephemeral} ({len(server_hello.ephemeral) if has_ephemeral else 0} bytes), "
                   f"static={has_static} ({len(server_hello.static) if has_static else 0} bytes), "
                   f"payload={has_payload} ({len(server_hello.payload) if has_payload else 0} bytes)")
        
        if has_ephemeral:
            logger.debug(f"[HANDSHAKE-XX] ServerHello.ephemeral (hex): {server_hello.ephemeral.hex()[:64]}...")
        if has_static:
            logger.debug(f"[HANDSHAKE-XX] ServerHello.static (hex): {server_hello.static.hex()[:64]}...")
        if has_payload:
            logger.debug(f"[HANDSHAKE-XX] ServerHello.payload (hex, primeiros 64): {server_hello.payload.hex()[:64]}...")
        
        payload_buffer = bytearray()
        self._handshakestate.read_message(
            server_hello.ephemeral + server_hello.static + server_hello.payload, payload_buffer
        )
        
        # Valida certificado - CORRIGIDO: adicionado await
        certman = AsyncCertMan()
        if await certman.is_valid(self._handshakestate.rs, bytes(payload_buffer)):
            logger.debug("[HANDSHAKE-XX] Certificado válido")
        else:
            logger.error("[HANDSHAKE-XX] Certificado inválido")
            # Não falha o handshake, mas registra o erro
        
        # A chave estática remota já está disponível em self._handshakestate.rs após read_message
        # Não precisa extrair do server_hello.static diretamente
        if self._handshakestate.rs:
            logger.debug(f"[HANDSHAKE-XX] Chave estática remota obtida do handshake state: {self._handshakestate.rs.data.hex()[:32]}...")
        
        # Cria client finish
        logger.debug("[HANDSHAKE-XX] Criando client_finish...")
        logger.debug(f"[HANDSHAKE-XX] ClientPayload tamanho: {len(client_payload.SerializeToString())} bytes")
        
        message_buffer = bytearray()
        try:
            cipherpair = self._handshakestate.write_message(
                client_payload.SerializeToString(),
                message_buffer
            )
            logger.debug(f"[HANDSHAKE-XX] Client finish criptografado: {len(message_buffer)} bytes")
            logger.debug(f"[HANDSHAKE-XX] Cipherpair obtido: send={cipherpair}, recv={cipherpair}")
        except Exception as e:
            logger.error(f"[HANDSHAKE-XX] ✗ Erro ao criar client_finish: {e}")
            raise HandshakeFailedException(f"Erro ao criar client_finish: {e}") from e
        
        logger.debug("[HANDSHAKE-XX] Separando static e payload do client_finish...")

        static, payload = ByteUtil.split(bytes(message_buffer), 48, len(message_buffer) - 48)

        logger.debug(f"[HANDSHAKE-XX] Static: {len(static)} bytes, Payload: {len(payload)} bytes")
        logger.debug(f"[HANDSHAKE-XX] Static (hex): {static.hex()[:64]}...")
        
        client_finish = wa5_pb2.HandshakeMessage.ClientFinish()
        client_finish.static = static
        client_finish.payload = payload
        outgoing_handshakemessage = wa5_pb2.HandshakeMessage()
        outgoing_handshakemessage.client_finish.MergeFrom(client_finish)
        
        serialized_finish = outgoing_handshakemessage.SerializeToString()
        logger.info(f"[HANDSHAKE-XX] ClientFinish preparado: {len(serialized_finish)} bytes")
        logger.debug(f"[HANDSHAKE-XX] ClientFinish serializado (hex, primeiros 100): {serialized_finish.hex()[:100]}...")
        
        # Envia client finish - await, não bloqueia
        logger.debug("[HANDSHAKE-XX] Enviando client_finish via stream.write_segment()...")
        await stream.write_segment(serialized_finish)
        logger.info("[HANDSHAKE-XX] ✓ Client finish enviado")
        logger.info("[HANDSHAKE-XX] ========== HANDSHAKE XX CONCLUÍDO ==========")
        
        return cipherpair
    
    async def _switch_handshake_xx_fallback(
        self,
        stream: AsyncSegmentedStream,
        s: KeyPair,
        client_payload,
        server_hello
    ) -> Tuple[CipherState, CipherState]:
        """
        Faz fallback IK→XX quando detecta nova chave estática remota.
        """
        # Troca para handshake XX
        self._handshakestate.switch(
            handshake_pattern=FallbackPatternModifier().modify(XXHandshakePattern()),
            initiator=True,
            prologue=self._prologue,
            s=s
        )
        
        # Processa server hello
        payload_buffer = bytearray()
        self._handshakestate.read_message(
            server_hello.ephemeral + server_hello.static + server_hello.payload,
            payload_buffer
        )
        
        # Valida certificado
        certman = AsyncCertMan()
        if await certman.is_valid(self._handshakestate.rs, bytes(payload_buffer)):
            logger.debug("Certificado válido")
        else:
            logger.error("Certificado inválido")
        
        # Cria client finish
        message_buffer = bytearray()
        cipherpair = self._handshakestate.write_message(
            client_payload.SerializeToString(),
            message_buffer
        )
        
        # CORRIGIDO: No fallback XX, o split deve ser igual ao handshake XX normal (48, len - 48)
        static, payload = ByteUtil.split(
            bytes(message_buffer), 48, len(message_buffer) - 48
        )
        
        if wa5_pb2 is None:
            raise ImportError("wa5_pb2 not available")
        client_finish = wa5_pb2.HandshakeMessage.ClientFinish()
        client_finish.static = static
        client_finish.payload = payload
        outgoing_handshakemessage = wa5_pb2.HandshakeMessage()
        outgoing_handshakemessage.client_finish.MergeFrom(client_finish)
        
        # Envia client finish - await, não bloqueia
        await stream.write_segment(outgoing_handshakemessage.SerializeToString())
        
        return cipherpair
    
    def _create_full_payload(self, client_config, s):
        """
        Cria payload completo do cliente.
        Baseado na implementação do zowsuplib.
        
        :param client_config: Configuração do cliente
        :type client_config: ClientConfig
        :param s: KeyPair estático local
        :return: wa5_pb2.ClientPayload
        """
        if wa5_pb2 is None:
            raise ImportError("wa5_pb2 not available")
        
        import hashlib
        import base64
        
        client_payload = wa5_pb2.ClientPayload()
        user_agent = wa5_pb2.ClientPayload.UserAgent()
        user_agent_app_version = wa5_pb2.ClientPayload.UserAgent.AppVersion()

        user_agent.platform = client_config.useragent.platform
        user_agent.mcc = client_config.useragent.mcc
        user_agent.mnc = client_config.useragent.mnc
        user_agent.os_version = client_config.useragent.os_version
        user_agent.manufacturer = client_config.useragent.manufacturer
        user_agent.device = client_config.useragent.device
        user_agent.os_build_number = client_config.useragent.os_build_number
        user_agent.phone_id = client_config.useragent.phone_id

        user_agent.locale_language_iso_639_1 = client_config.useragent.locale_lang
        user_agent.locale_country_iso_3166_1_alpha_2 = client_config.useragent.locale_country

        user_agent.release_channel = 0  # RELEASE
        user_agent.device_type = 0  # PHONE

        if client_config.useragent.device_model_type is not None:
            user_agent.device_model_type = client_config.useragent.device_model_type

        user_agent_app_version.primary = client_config.useragent.app_version.primary
        user_agent_app_version.secondary = client_config.useragent.app_version.secondary
        user_agent_app_version.tertiary = client_config.useragent.app_version.tertiary
        user_agent_app_version.quaternary = client_config.useragent.app_version.quaternary

        user_agent.app_version.MergeFrom(user_agent_app_version)

        client_payload.passive = client_config.passive
        client_payload.short_connect = True
        client_payload.connect_type = 1
        client_payload.connect_reason = 1
        client_payload.dns_source.dns_method = 0
        client_payload.connect_attempt_count = 0
        client_payload.user_agent.MergeFrom(user_agent)

        if self.mode is None:
            # Modo normal (login)
            client_payload.username = client_config.username
            client_payload.push_name = client_config.pushname

            if self.deviceid is not None:
                client_payload.device = self.deviceid
            else:
                client_payload.device = 0
        else:
            # Modo registro (device pairing)
            if self.regid is None or self.identity is None or self.signedprekey is None:
                raise ValueError("regid, identity e signedprekey são necessários para modo registro")
            
            client_payload.device_pairing_data.e_regid = self.regid.to_bytes(4, "big")
            client_payload.device_pairing_data.e_keytype = b"\x05"
            client_payload.device_pairing_data.e_ident = self.identity.publicKey.serialize()[1:]
            client_payload.device_pairing_data.e_skey_id = self.signedprekey.getId().to_bytes(4, "big")
            client_payload.device_pairing_data.e_skey_val = self.signedprekey.getKeyPair().publicKey.serialize()[1:]

            sign = self.signedprekey.getSignature()
            client_payload.device_pairing_data.e_skey_sig = sign

            m = hashlib.md5()
            m.update(client_config.useragent.app_version.getVersion().encode())
            client_payload.device_pairing_data.build_hash = base64.b64decode(m.hexdigest())
            client_payload.device_pairing_data.device_props.os = client_config.useragent.os_version
            client_payload.device_pairing_data.device_props.version.primary = client_config.useragent.app_version.primary
            client_payload.device_pairing_data.device_props.version.secondary = client_config.useragent.app_version.secondary
            client_payload.device_pairing_data.device_props.version.tertiary = client_config.useragent.app_version.tertiary
            client_payload.device_pairing_data.device_props.version.quaternary = client_config.useragent.app_version.quaternary
            client_payload.device_pairing_data.device_props.platform_type = 9
            client_payload.device_pairing_data.device_props.require_full_sync = 1
            client_payload.oc = True
            client_payload.lc = 1

        return client_payload
    
    @property
    def rs(self) -> Optional[PublicKey]:
        """Retorna chave estática remota"""
        return PublicKey(self._handshakestate.rs.data) if self._handshakestate.rs else None

