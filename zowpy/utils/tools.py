import os
from pathlib import Path
import struct
from typing import Optional, Tuple, Union
import zlib
from .constants import YowConstants
import codecs, sys
import tempfile
import base64
import hashlib
import os.path, mimetypes
import uuid
import random
from ..noise.structs import KeyPair
import re
from loguru import logger
import requests
from urllib.parse import urlparse
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import hmac
from math import ceil
from Crypto.Util.Padding import pad,unpad

from ..protocol.structs import ProtocolNode



# Optional modules - importação segura de módulos opcionais
class PILOptionalModule:
    """Context manager para importação opcional do PIL/Pillow"""
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def __call__(self, name):
        try:
            from PIL import Image
            return Image
        except ImportError:
            raise ImportError(f"PIL/Pillow não está instalado. Instale com: pip install Pillow")

class FFMpegOptionalModule:
    """Context manager para importação opcional do ffmpeg-python"""
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def __call__(self):
        try:
            import ffmpeg
            return ffmpeg
        except ImportError:
            raise ImportError(f"ffmpeg-python não está instalado. Instale com: pip install ffmpeg-python")

class Jid:
    @staticmethod
    def normalize(tos):
        numbers = tos.split(",")
        ret = []
        for number in numbers:
            number = number.strip()
            if f"@{YowConstants.LID_SUFFIX}" in number:
                ret.append(number)
                continue
            if '@' in number:
                ret.append(number)                
                continue
            elif "-" in number or ("." not in number and ":" not in number and len(number) >= 15):
                ret.append("%s@%s" % (number, YowConstants.WHATSAPP_GROUP_SERVER))            
                continue
                        
            ret.append("%s@%s" % (number, YowConstants.WHATSAPP_SERVER))

        return ','.join(ret)
        

class HexTools:
    decode_hex = codecs.getdecoder("hex_codec")
    @staticmethod
    def decodeHex(hexString):
        result = HexTools.decode_hex(hexString)[0]
        if sys.version_info >= (3,0):
            result = result.decode('latin-1')
        return result

class WATools:

    # Tipos de modificação para generate_msg_secret_key 
    MSG_SECRET_TYPE_POLL_VOTE = "Poll Vote"
    MSG_SECRET_TYPE_REACTION = "Enc Reaction"
    MSG_SECRET_TYPE_COMMENT = "Enc Comment"
    MSG_SECRET_TYPE_REPORT_TOKEN = "Report Token"
    MSG_SECRET_TYPE_EVENT_RESPONSE = "Event Response"
    MSG_SECRET_TYPE_EVENT_EDIT = "Event Edit"
    MSG_SECRET_TYPE_BOT_MSG = "Bot Message"


    @staticmethod
    def normalizeJid(tos):
        numbers = tos.split(",")
        ret = []
        for number in numbers:
            number = number.strip()
            # Preserve LID: do not force @s.whatsapp.net
            if f"@{YowConstants.LID_SUFFIX}" in number:
                ret.append(number)
                continue
            if '@' in number:
                ret.append(number)                
                continue
            elif "-" in number or ("." not in number and ":" not in number and len(number) >= 15):
                ret.append("%s@%s" % (number, YowConstants.WHATSAPP_GROUP_SERVER))            
                continue
                        
            ret.append("%s@%s" % (number, YowConstants.WHATSAPP_SERVER))

        return ','.join(ret)
        

    @staticmethod
    def fullJid(jid):
       jid = Jid.normalize(jid) 
       s = jid.split("@")[1]
       i,t,d = WATools.jidDecode(jid)
       return "%s.%d:%d@%s" % (i,t,d,s)
    
    @staticmethod
    def jidDecode(jid)->list[str,int,int]:
        """
        Decodifica um JID em um recipientId, recipientType e deviceId.
        Suporta JID (user@s.whatsapp.net), LID (user:device@lid) e formato completo (user.type:device).
        :param jid: JID ou LID a ser decodificado
        :type jid: str
        :return: Lista contendo recipientId, recipientType e deviceId
        :rtype: list[str,int,int]
        """
        username = jid.split("@")[0]
        nps = re.split(':|\\.', username)
        recipientId = nps[0]

        if len(recipientId) < 14:
            recipientType = int(nps[1]) if len(nps) >= 2 else 0
        else:
            recipientType = 1

        # LID user:device -> deviceId = second part; full form user.type:device -> deviceId = third part
        deviceId = int(nps[2]) if len(nps) >= 3 else (int(nps[1]) if len(nps) >= 2 else 0)
        return [recipientId, recipientType, deviceId]

    @staticmethod
    def jid_to_non_ad_string(jid: str) -> str:
        """
        Retorna o JID em forma string sem sufixo agent/device (equivalente a ToNonAD().String()).
        Ex.: "5511999.0:0@s.whatsapp.net" -> "5511999@s.whatsapp.net"
        """
        normalized = WATools.normalizeJid(jid).split(",")[0].strip()
        if "@" not in normalized:
            return normalized
        recipient_id, _, _ = WATools.jidDecode(normalized)
        server = normalized.split("@")[1]
        return f"{recipient_id}@{server}"

    @staticmethod
    def generateIdentity():
        return os.urandom(20)

    @classmethod
    def generatePhoneId(cls,deviceEnv):
        """
        :return:
        :rtype: str
        """                
        if deviceEnv.getOSName() in ["iOS","SMB iOS"]:
            return str(cls.generateUUID()).upper()
        else:
            return str(cls.generateUUID())
    
    @classmethod
    def generateDeviceId(cls):
        """
        :return:
        :rtype: bytes
        """        
        return cls.generateUUID().bytes

    @classmethod
    def generateUUID(cls):
        """
        :return:
        :rtype: uuid.UUID
        """
        return uuid.uuid4()

    @classmethod
    def generateKeyPair(cls):
        """
        :return:
        :rtype: KeyPair
        """
        return KeyPair.generate()

    @staticmethod
    def getFileHashForUpload(filePath):
        sha1 = hashlib.sha256()
        f = open(filePath, 'rb')
        try:
            sha1.update(f.read())
        finally:
            f.close()
        b64Hash = base64.b64encode(sha1.digest())
        return b64Hash if type(b64Hash) is str else b64Hash.decode()

    @staticmethod
    def getDataHashForUpload(data):
        sha1 = hashlib.sha256()
        sha1.update(data)
        b64Hash = base64.b64encode(sha1.digest())
        return b64Hash if type(b64Hash) is str else b64Hash.decode()
    
    @staticmethod
    def generate_media_key():
        """
        Gera media_key no formato correto para compatibilidade com zowsuplib.
        
        Baseado em zowsuplib/yowsup/layers/protocol_messages/protocolentities/attributes/attributes_downloadablemedia.py:
        - Gera string de 32 caracteres aleatórios usando alfabeto alfanumérico
        - Codifica em GBK (ou UTF-8 como fallback)
        
        Returns:
            bytes: media_key de 32 bytes
        """
        alp = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        media_key_str = ''.join(random.sample(alp, 32))
        try:
            # Tenta codificar em GBK (como zowsuplib faz)
            return media_key_str.encode("GBK")
        except (LookupError, UnicodeEncodeError):
            # Fallback para UTF-8 se GBK não disponível
            return media_key_str.encode("utf-8")      

    @staticmethod
    def compress(uncompressed: bytes) -> bytes:
        """
        Comprime dados usando zlib.
        :param uncompressed: Dados não comprimidos
        :return: Dados comprimidos
        :rtype: bytes
        """
        compressor = zlib.compressobj()
        compressed_data = compressor.compress(uncompressed)
        compressed_data += compressor.flush()
        return compressed_data

    @staticmethod
    def decompress(compressed: bytes) -> bytes:
        """
        Descomprime dados usando zlib.
        :param compressed: Dados comprimidos
        :return: Dados descomprimidos
        :rtype: bytes
        """
        decompressor = zlib.decompressobj()
        decompressed_data = decompressor.decompress(compressed)
        decompressed_data += decompressor.flush()
        return decompressed_data          
    
    @staticmethod
    def extract_and_expand(key: bytes, info: bytes = b"", output_length: int = 32,salt=None) -> bytes:
        return WATools.expand(hmac.new(salt if salt is not None else bytes(32) , key, hashlib.sha256).digest(), info, output_length)


    @staticmethod
    def generate_msg_secret_key(
        modification_type: Union[str, bytes],
        modification_sender: str,
        orig_msg_id: Union[str, bytes],
        orig_msg_sender: str,
        orig_msg_secret: bytes,
    ) -> Tuple[bytes, bytes]:
        """
        Gera chave secreta e additional_data para criptografia de modificações (ex.: voto em poll, reação, comentário).
        Equivalente a generateMsgSecretKey no Go (HKDF-SHA256 com orig_msg_secret e use_case_secret).
        Para modification_type em (Poll Vote, Event Response, vazio), retorna additional_data no formato
        orig_msg_id + '\\x00' + modification_sender_str; nos demais tipos retorna additional_data vazio.
        """
        orig_msg_sender_str = WATools.jid_to_non_ad_string(orig_msg_sender)
        modification_sender_str = WATools.jid_to_non_ad_string(modification_sender)
        orig_id_bytes = orig_msg_id if isinstance(orig_msg_id, bytes) else orig_msg_id.encode("utf-8")
        mod_type_bytes = modification_type if isinstance(modification_type, bytes) else (modification_type or "").encode("utf-8")
        use_case_secret = orig_id_bytes + orig_msg_sender_str.encode("utf-8") + modification_sender_str.encode("utf-8") + mod_type_bytes
        secret_key = WATools.extract_and_expand(orig_msg_secret, use_case_secret, 32, salt=None)
        mod_type_str = modification_type.decode("utf-8") if isinstance(modification_type, bytes) else (modification_type or "")
        if not mod_type_str or mod_type_str in (
            WATools.MSG_SECRET_TYPE_POLL_VOTE,
            WATools.MSG_SECRET_TYPE_EVENT_RESPONSE,
        ):
            additional_data = orig_id_bytes + b"\x00" + modification_sender_str.encode("utf-8")
        else:
            additional_data = b""
        return secret_key, additional_data

    @staticmethod
    def get_message_reporting_token(
        msg_protobuf: bytes,
        message_secret: bytes,
        sender_jid: str,
        remote_jid: str,
        message_id: Union[str, bytes],
    ) -> ProtocolNode:
        """
        Gera o node <reporting> com <reporting_token> para mensagem (token HMAC-SHA256).
        Equivalente a getMessageReportingToken no Go: reportingSecret via generateMsgSecretKey(Report Token),
        depois HMAC-SHA256(reportingSecret, getReportingToken(msgProtobuf))[:16].
        getReportingToken(msgProtobuf) é o input ao HMAC; aqui usa-se msg_protobuf como tal.
        """
        reporting_secret, _ = WATools.generate_msg_secret_key(
            WATools.MSG_SECRET_TYPE_REPORT_TOKEN,
            sender_jid,
            message_id,
            remote_jid,
            message_secret,
        )
        data_to_hash = msg_protobuf
        hasher = hmac.new(reporting_secret, data_to_hash, hashlib.sha256)
        token_reporting = hasher.digest()[:16]
      
        return token_reporting

    @staticmethod
    def expand(prk: bytes, info: bytes, output_size: int) -> bytes:
        """
        Expande uma chave usando hmac.
        :param prk: Chave primária
        :param info: Info
        :param output_size: Tamanho da saída
        :return: Chave expandida
        :rtype: bytes
        """
        HASH_OUTPUT_SIZE = 32  # SHA-256 produces a 32-byte output                
        iterations = ceil(output_size / HASH_OUTPUT_SIZE)
        mixin = b""
        results = bytearray()
        
        for index in range(1, iterations + 1):
            mac = hmac.new(prk, mixin, hashlib.sha256)
            if info:
                mac.update(info)
            mac.update(bytes([index]))
            step_result = mac.digest()
            step_size = min(output_size, len(step_result))
            results.extend(step_result[:step_size])
            mixin = step_result
            output_size -= step_size
        
        return bytes(results)
    
    
    @staticmethod
    def encryptAndPrefix(buffer,key):                
        iv = get_random_bytes(AES.block_size)              
        cipher = AES.new(key, AES.MODE_CBC,iv= iv)           
        buffer_padded = pad(buffer, AES.block_size)
        ciphered = cipher.encrypt(buffer_padded)    
        return iv+ciphered    
    
    @staticmethod
    def generateMac(opbyte,data,keyId,key):        
        keyData = opbyte+keyId
        last = struct.pack(">Q",len(keyData))                
        total = keyData+data+last        
        mac = hmac.new(key, total, hashlib.sha512).digest()                
        return mac[0:32]
    
    @staticmethod
    def generateSnapshotMac(ltHash,version,patchType,key):
        total = ltHash+struct.pack(">Q", version)+patchType.encode()
        mac = hmac.new(key, total, hashlib.sha256).digest()
        return mac
    

    @staticmethod
    def generatePatchMac(snapShotMac,valueMacs,version,patchType,key):
        total = snapShotMac
        for item in valueMacs:
            total+=item
        total+=struct.pack(">Q", version)+patchType.encode()
        mac = hmac.new(key, total, hashlib.sha256).digest()
        return mac        

  

class StorageTools:
    NAME_CONFIG = "config.json"

    @staticmethod
    def _extract_phone_from_profile_name(profile_name):
        """
        Attempts to extract the phone / account identifier from a profile_name.

        Common patterns in this project:
          - ACCOUNT_PATH + phone
          - ACCOUNT_PATH + phone + "_" + deviceid
        We normalize to the last path component and take the leading digits.
        """
        base = os.path.basename(str(profile_name))
        # Strip optional "_deviceId" suffix
        if "_" in base:
            base = base.split("_", 1)[0]
        # Match a leading sequence of at least 5 digits (the phone number)
        m = re.match(r"(\d{5,})", base)
        return m.group(1) if m else None

    @staticmethod
    def constructPath(*path):
        """
        DEPRECATED: O zowpy não usa armazenamento baseado em arquivos.
        Use o banco de dados unificado através de AsyncDatabasePool.
        """
        logger.warning("StorageTools.constructPath está deprecado. Use o banco de dados unificado.")
        path = os.path.join(*path)
        # Usa diretório temporário como fallback
        temp_dir = tempfile.gettempdir()
        fullPath = os.path.join(temp_dir, "zowpy", path)
        if not os.path.exists(os.path.dirname(fullPath)):
            os.makedirs(os.path.dirname(fullPath), exist_ok=True)
        return fullPath

    @staticmethod
    def getStorageForProfile(profile_name):
        if type(profile_name) is not str:
            profile_name = str(profile_name)
        return StorageTools.constructPath(profile_name)

    @staticmethod
    def writeProfileData(profile_name, name, val):
        logger.debug(f"writeProfileData(profile_name={profile_name}, name={name}, val=[omitted])")
        path = os.path.join(StorageTools.getStorageForProfile(profile_name), name)
        logger.debug(f"Writing {path}")

        with open(path, 'w' if type(val) is str else 'wb') as attrFile:
            attrFile.write(val)

    @staticmethod
    def readProfileData(profile_name, name, default=None):
        logger.debug(f"readProfileData(profile_name={profile_name}, name={name})")
        path = StorageTools.getStorageForProfile(profile_name)
        dataFilePath = os.path.join(path, name)
        if os.path.isfile(dataFilePath):
            logger.debug(f"Reading {dataFilePath}")
            with open(dataFilePath, 'rb') as attrFile:
                return attrFile.read()
        else:
            logger.debug(f"{dataFilePath} does not exist")

        return default

    @classmethod
    async def writeProfileConfig(cls, profile_name, config, session_maker):
        """
        Writes profile config exclusively to the unified database (ProfileConfig).

        No config.json or per-account directories are used anymore. The
        profile_name is expected to start with the phone number (or
        phone_deviceid), so we can link it to an Account row.
        
        :param profile_name: Nome do perfil (deve conter o número de telefone)
        :param config: Configuração (str ou bytes)
        :param session_maker: AsyncSessionMaker instance
        """
        if session_maker is None:
            logger.error("session_maker é obrigatório para writeProfileConfig")
            return
        
        phone = cls._extract_phone_from_profile_name(profile_name)

        if not phone:
            logger.error(f"Cannot infer phone from profile_name={profile_name}; config will not be persisted")
            return

        # Lazy import to avoid circular dependencies at module import time
        from ..db.models import Account, ProfileConfig
        from sqlalchemy import select

        async with session_maker() as session:
            # Busca ou cria Account
            result = await session.execute(select(Account).filter_by(phone=phone))
            account = result.scalar_one_or_none()
            
            if account is None:
                account = Account(phone=phone)
                session.add(account)
                await session.flush()

            # Busca ou cria ProfileConfig
            result = await session.execute(
                select(ProfileConfig).filter_by(
                    account_id=account.id,
                    name=cls.NAME_CONFIG
                )
            )
            profile_config = result.scalar_one_or_none()

            data = config.encode() if isinstance(config, str) else config

            if profile_config is None:
                profile_config = ProfileConfig(
                    account_id=account.id,
                    name=cls.NAME_CONFIG,
                    data=data,
                )
                session.add(profile_config)
            else:
                profile_config.data = data

            await session.commit()
            logger.debug(f"ProfileConfig stored in DB for phone={phone}")

    @classmethod
    async def readProfileConfig(cls, profile_name, session_maker):
        """
        Reads profile config exclusively from the unified database (ProfileConfig).

        If no matching Account/ProfileConfig is found, returns None. No
        file-based config.json lookup is performed.
        
        :param profile_name: Nome do perfil (deve conter o número de telefone)
        :param session_maker: AsyncSessionMaker instance
        :return: bytes ou None
        """
        if session_maker is None:
            logger.error("session_maker é obrigatório para readProfileConfig")
            return None
        
        phone = cls._extract_phone_from_profile_name(profile_name)

        if not phone:
            logger.error(f"Cannot infer phone from profile_name={profile_name}; no config available")
            return None

        from ..db.models import Account, ProfileConfig
        from sqlalchemy import select

        async with session_maker() as session:
            result = await session.execute(select(Account).filter_by(phone=phone))
            account = result.scalar_one_or_none()
            
            if not account:
                return None

            result = await session.execute(
                select(ProfileConfig).filter_by(
                    account_id=account.id,
                    name=cls.NAME_CONFIG
                )
            )
            profile_config = result.scalar_one_or_none()

            logger.debug(f"profile_config: {profile_config}")
            
            if profile_config is None:
                return None

            return profile_config.data


class ImageTools:
    @staticmethod
    def scaleImage(infile, outfile, imageFormat, width, height):
        with PILOptionalModule() as imp:
            Image = imp("Image")
            im = Image.open(infile)
            #Convert P mode images
            if im.mode != "RGB":
                im = im.convert("RGB")
            im.thumbnail((width, height))
            im.save(outfile, imageFormat)
            return True
        return False

    @staticmethod
    def getImageDimensions(imageFile):
        with PILOptionalModule() as imp:
            Image = imp("Image")
            im = Image.open(imageFile)
            return im.size

    @staticmethod
    def generatePreviewFromImage(image):
        fd, path = tempfile.mkstemp()
        preview = None
        if ImageTools.scaleImage(image, path, "JPEG", YowConstants.PREVIEW_WIDTH, YowConstants.PREVIEW_HEIGHT):
            fileObj = os.fdopen(fd, "rb+")
            fileObj.seek(0)
            preview = fileObj.read()
            fileObj.close()
        os.remove(path)
        return preview

class MimeTools:
    MIME_FILE = os.path.join(os.path.dirname(__file__), 'mime.types')
    mimetypes.init() # Load default mime.types
    try:
        mimetypes.init([MIME_FILE]) # Append whatsapp mime.types
    except Exception as e:
        logger.warning("Mime types supported can't be read. System mimes will be used. Cause: " +str(e))

    # Mapeamento manual para tipos MIME não reconhecidos automaticamente
    _MANUAL_MIME_TYPES = {
        '.webp': 'image/webp',
        '.webm': 'video/webm',
        '.was': 'application/was',  # WhatsApp Audio Sticker
    }

    @staticmethod
    def getMIME(filepath):
        # Tenta primeiro com mimetypes padrão
        mimeType = mimetypes.guess_type(filepath)[0]
        
        # Se não encontrou, tenta mapeamento manual por extensão
        if mimeType is None:
            filepath_lower = filepath.lower()
            for ext, mime in MimeTools._MANUAL_MIME_TYPES.items():
                if filepath_lower.endswith(ext):
                    mimeType = mime
                    break
        
        # Se ainda não encontrou, tenta adicionar ao mimetypes dinamicamente
        if mimeType is None:
            # Extrai extensão do arquivo
            ext = os.path.splitext(filepath)[1].lower()
            if ext:
                # Adiciona tipos comuns de stickers/imagens
                if ext == '.webp':
                    mimetypes.add_type('image/webp', ext)
                    mimeType = 'image/webp'
                elif ext == '.webm':
                    mimetypes.add_type('video/webm', ext)
                    mimeType = 'video/webm'
        
        if mimeType is None:
            raise Exception("Unsupported/unrecognized file type for: "+filepath);
        return mimeType


class AudioTools:
    @staticmethod
    def getAudioProperties(audioFile):
        """
        Obtém propriedades do áudio (duração em segundos).
        Em caso de erro, retorna valor aleatório genérico entre 1-60 segundos.
        """
        try:
            with FFMpegOptionalModule() as imp:
                ffmpeg = imp()
                probe = ffmpeg.probe(audioFile)
                audio_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'audio'), None)
                if audio_stream and 'duration' in audio_stream:
                    duration = int(float(audio_stream['duration']))
                    return duration
        except Exception as e:
            logger.warning(f"Erro ao obter propriedades do áudio {audioFile}: {e}. Usando valor fallback.")
        
        # Fallback: duração aleatória entre 1-60 segundos (típico para mensagens de áudio)
        fallback_duration = random.randint(1, 60)
        logger.debug(f"Usando duração fallback: {fallback_duration}s")
        return fallback_duration

class VideoTools:
    @staticmethod
    def getVideoProperties(videoFile):
        """
        Obtém propriedades do vídeo (width, height, bitrate, duration, codec_name).
        Em caso de erro, retorna valores genéricos/aleatórios.
        """
        try:
            with FFMpegOptionalModule() as imp:
                ffmpeg = imp()            
                probe = ffmpeg.probe(videoFile)
                video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
                if video_stream:
                    width = int(video_stream.get('width', 640))
                    height = int(video_stream.get('height', 480))
                    bitrate = int(video_stream.get('bit_rate', 1000000))
                    duration = int(float(video_stream.get('duration', 10)))
                    codec_name = video_stream.get('codec_name', 'h264')
                    return width, height, bitrate, duration, codec_name
        except Exception as e:
            logger.warning(f"Erro ao obter propriedades do vídeo {videoFile}: {e}. Usando valores fallback.")
        
        # Fallback: valores genéricos/aleatórios
        # Resoluções comuns: 640x480, 1280x720, 1920x1080
        resolutions = [(640, 480), (1280, 720), (1920, 1080), (854, 480), (1280, 960)]
        width, height = random.choice(resolutions)
        # Bitrate típico: 500k-5M
        bitrate = random.randint(500000, 5000000)
        # Duração típica: 5-120 segundos
        duration = random.randint(5, 120)
        # Codec comum
        codec_name = random.choice(['h264', 'h265', 'vp8', 'vp9', 'mpeg4'])
        
        logger.debug(f"Usando valores fallback: {width}x{height}, bitrate={bitrate}, duration={duration}s, codec={codec_name}")
        return width, height, bitrate, duration, codec_name

    @staticmethod
    def generatePreviewFromVideo(videoFile):
        """
        Gera preview (thumbnail) do vídeo.
        Em caso de erro, retorna None ou preview genérico.
        """
        try:
            with FFMpegOptionalModule() as imp:
                ffmpeg = imp()
                # Usa tempfile para compatibilidade multiplataforma
                temp_dir = tempfile.gettempdir()
                path = os.path.join(temp_dir, str(uuid.uuid4()) + ".jpg")
                
                try:
                    ffmpeg.input(videoFile, ss=0).filter("scale", 100, -1).output(path, vframes=1).run(quiet=True, overwrite_output=True)
                    preview = ImageTools.generatePreviewFromImage(path)
                    if os.path.exists(path):
                        os.remove(path)
                    return preview
                except Exception as e:
                    logger.warning(f"Erro ao gerar preview do vídeo {videoFile}: {e}")
                    if os.path.exists(path):
                        os.remove(path)
        except Exception as e:
            logger.warning(f"Erro ao inicializar FFMpeg para preview do vídeo {videoFile}: {e}. Usando fallback.")
        
        # Fallback: retorna None (sem preview) ou pode tentar gerar preview genérico
        # Por enquanto, retorna None para indicar que não foi possível gerar preview
        logger.debug("Usando fallback: preview não disponível")
        return None


class DownloadTools:
    """
    Ferramentas auxiliares para download seguro de arquivos de URLs.
    """
    
    @staticmethod
    def download_file_from_url(url: str, default_extension: str = None, prefix: str = "download") -> str:
        """
        Faz download de um arquivo de uma URL e salva em um diretório seguro.
        
        Args:
            url: URL do arquivo a ser baixado
            default_extension: Extensão padrão se não conseguir detectar da URL (ex: ".ogg", ".mp4")
            prefix: Prefixo para o nome do arquivo se não conseguir extrair da URL
        
        Returns:
            Caminho completo do arquivo baixado
        
        Raises:
            Exception: Se houver erro ao baixar ou salvar o arquivo
        """
        try:
            # Faz o download do arquivo
            down_res = requests.get(url, timeout=30)
            down_res.raise_for_status()
            
            # Extrai o filename da URL de forma segura
            parsed_url = urlparse(url)
            url_path = parsed_url.path
            
            # Tenta extrair o filename do path da URL
            if url_path:
                # Remove a barra inicial se existir
                url_path = url_path.lstrip('/')
                # Pega a última parte do path (filename)
                filename = os.path.basename(url_path) if url_path else None
            else:
                filename = None
            
            # Se não conseguiu extrair um filename válido da URL, gera um baseado no hash
            if not filename or len(filename) == 0 or len(filename) > 200:
                # Gera um hash da URL para criar um filename único
                url_hash = hashlib.sha256(url.encode('utf-8')).hexdigest()[:32]
                ext = default_extension or ".tmp"
                filename = f"{prefix}_{url_hash}{ext}"
            else:
                # Sanitiza o filename: remove caracteres inválidos e limita tamanho
                # Remove caracteres inválidos para Windows/Linux
                invalid_chars = '<>:"|?*\\'
                for char in invalid_chars:
                    filename = filename.replace(char, '_')
                
                # Limita o tamanho do filename (Windows tem limite de 255 caracteres)
                if len(filename) > 200:
                    name, ext = os.path.splitext(filename)
                    filename = name[:190] + (ext or default_extension or "")
                
                # Se não tiver extensão e foi fornecida uma padrão, adiciona
                if default_extension and not os.path.splitext(filename)[1]:
                    filename += default_extension
            
            # Determina o diretório de download
            # Usa diretório temporário padrão (zowpy não usa settings.download_path)
            download_dir = Path(tempfile.gettempdir()) / "zowpy_downloads"
            download_dir.mkdir(parents=True, exist_ok=True)
            
            # Monta o caminho completo do arquivo
            filepath = download_dir / filename
            
            # Se o arquivo já existir, adiciona um sufixo numérico
            counter = 1
            original_filepath = filepath
            while filepath.exists():
                name, ext = os.path.splitext(original_filepath)
                filepath = Path(f"{name}_{counter}{ext}")
                counter += 1
                if counter > 1000:  # Limite de segurança
                    raise Exception("Muitos arquivos com o mesmo nome no diretório")
            
            # Salva o arquivo
            filepath_str = str(filepath)
            with open(filepath_str, "wb") as file:
                file.write(down_res.content)
            
            logger.debug(f"Arquivo baixado de URL e salvo em: {filepath_str}")
            return filepath_str
            
        except requests.RequestException as e:
            logger.error(f"Erro ao baixar arquivo da URL {url}: {e}")
            raise Exception(f"Erro ao baixar arquivo: {str(e)}")
        except (PermissionError, OSError) as e:
            logger.error(f"Erro de permissão ao salvar arquivo: {e}")
            raise Exception(f"Erro de permissão ao salvar arquivo: {str(e)}")
        except Exception as e:
            logger.error(f"Erro inesperado ao processar arquivo da URL {url}: {e}", exc_info=True)
            raise



