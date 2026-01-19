"""
Async Media Uploader - Upload HTTP assíncrono de mídia criptografada.

Baseado em MediaUploader do zowsuplib, mas totalmente assíncrono usando aiohttp.
"""

import hashlib
import os
from typing import Optional, Callable, Dict, Any
from loguru import logger

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    logger.warning("aiohttp não instalado. Upload de mídia requer aiohttp.")


class AsyncMediaUploader:
    """
    Upload HTTP assíncrono de mídia criptografada.
    
    Baseado em DownloadableMediaMessageAttributes.from_buffer() do zowsuplib:
    - Upload via POST direto com dados criptografados no body
    - Content-Type: application/octet-stream no header HTTP
    - Não usa multipart/form-data
    - Retorna URL e direct_path da resposta JSON
    """
    
    def __init__(self):
        """Inicializa AsyncMediaUploader."""
        if not HAS_AIOHTTP:
            raise RuntimeError("aiohttp é necessário para upload de mídia")
    
    async def upload(
        self,
        filepath: str,
        upload_url: str,
        progress_callback: Optional[Callable[[str, str, str, int], None]] = None,
        chunk_size: int = 8192
    ) -> Dict[str, str]:
        """
        Faz upload de arquivo via HTTP POST direto (dados criptografados no body).
        
        Baseado em DownloadableMediaMessageAttributes.from_buffer() do zowsuplib:
        1. Lê arquivo do filesystem (dados já criptografados)
        2. Faz POST direto com dados no body
        3. Content-Type: application/octet-stream no header
        4. Parseia resposta JSON e retorna url/direct_path
        
        Args:
            filepath: Caminho do arquivo criptografado a fazer upload
            upload_url: URL completa de upload (inclui auth e token)
            progress_callback: Callback(opcional): (filepath, url, upload_url, percentage) -> None
            chunk_size: Tamanho do chunk para leitura/envio (padrão: 8192)
        
        Returns:
            dict: {"url": "...", "direct_path": "..."} da resposta JSON
        
        Raises:
            RuntimeError: Se aiohttp não estiver instalado
            FileNotFoundError: Se arquivo não existir
            aiohttp.ClientError: Se upload falhar
        """
        if not HAS_AIOHTTP:
            raise RuntimeError("aiohttp é necessário para upload de mídia")
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")
        
        # Prepara informações do arquivo
        filename = os.path.basename(filepath)
        filesize = os.path.getsize(filepath)
        
        logger.debug(
            f"Iniciando upload: file={filename} ({filesize} bytes), "
            f"url={upload_url[:50]}..."
        )
        
        # Abre arquivo e lê dados criptografados
        try:
            with open(filepath, 'rb') as f:
                file_data = f.read()
        except Exception as e:
            raise RuntimeError(f"Erro ao ler arquivo {filepath}: {e}")
        
        # Faz upload usando aiohttp com POST direto
        try:
            # Headers conforme zowsup: Content-Type: application/octet-stream
            headers = {"Content-Type": "application/octet-stream"}
            
            async with aiohttp.ClientSession() as session:
                # Faz POST direto com dados criptografados no body
                async with session.post(
                    upload_url,
                    data=file_data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=300)  # 5 minutos timeout
                ) as response:
                    response.raise_for_status()
                    
                    # Lê resposta JSON
                    result = await response.json()
                    
                    # Emite progresso 100%
                    if progress_callback:
                        # Assinatura: (filepath, to_jid, upload_url, percentage)
                        # Como não temos mais to_jid no POST direto, passamos string vazia
                        progress_callback(filepath, "", upload_url, 100)
                    
                    # Parseia resposta (baseado em JSONResponseParser)
                    # Formato esperado: {"url": "...", "direct_path": "..."}
                    url = result.get("url")
                    direct_path = result.get("direct_path")
                    
                    if not url:
                        raise RuntimeError(
                            f"Upload falhou: resposta não contém 'url'. "
                            f"Resultado: {result}"
                        )
                    
                    logger.info(
                        f"Upload concluído: file={filename}, "
                        f"url={url[:50]}..., direct_path={direct_path or 'N/A'}"
                    )
                    
                    return {
                        "url": url,
                        "direct_path": direct_path or "",
                    }
                    
        except aiohttp.ClientError as e:
            logger.error(f"Erro HTTP ao fazer upload de {filepath}: {e}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao fazer upload de {filepath}: {e}", exc_info=True)
            raise
    
    async def upload_from_bytes(
        self,
        data: bytes,
        upload_url: str,
        progress_callback: Optional[Callable[[str, str, str, int], None]] = None
    ) -> Dict[str, str]:
        """
        Faz upload de bytes diretamente (sem arquivo no filesystem).
        
        Útil para upload de dados gerados em memória.
        
        Args:
            data: Bytes criptografados a fazer upload
            upload_url: URL completa de upload
            progress_callback: Callback opcional para progresso
        
        Returns:
            dict: {"url": "...", "direct_path": "..."}
        """
        if not HAS_AIOHTTP:
            raise RuntimeError("aiohttp é necessário para upload de mídia")
        
        filesize = len(data)
        
        logger.debug(
            f"Iniciando upload de bytes: ({filesize} bytes), "
            f"url={upload_url[:50]}..."
        )
        
        # Faz upload usando POST direto (como zowsup)
        try:
            # Headers conforme zowsup: Content-Type: application/octet-stream
            headers = {"Content-Type": "application/octet-stream"}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    upload_url,
                    data=data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=300)
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    
                    if progress_callback:
                        progress_callback("", upload_url, upload_url, 100)
                    
                    url = result.get("url")
                    direct_path = result.get("direct_path")
                    
                    if not url:
                        raise RuntimeError(
                            f"Upload falhou: resposta não contém 'url'. "
                            f"Resultado: {result}"
                        )
                    
                    logger.info(
                        f"Upload de bytes concluído: "
                        f"url={url[:50]}..."
                    )
                    
                    return {
                        "url": url,
                        "direct_path": direct_path or "",
                    }
                    
        except Exception as e:
            logger.error(f"Erro ao fazer upload de bytes: {e}", exc_info=True)
            raise

