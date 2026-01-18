"""
Async Media Uploader - Upload HTTP assíncrono de mídia criptografada.

Baseado em MediaUploader do zowsuplib, mas totalmente assíncrono usando aiohttp.
"""

import hashlib
import os
import random
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
    
    Baseado em MediaUploader do zowsuplib:
    - Upload via POST multipart/form-data
    - Campos: "to", "from", "file"
    - Progress callback opcional
    - Retorna URL e direct_path da resposta JSON
    
    Compatível com formato antigo (URL direta) e novo formato (media_conn).
    """
    
    def __init__(self):
        """Inicializa AsyncMediaUploader."""
        if not HAS_AIOHTTP:
            raise RuntimeError("aiohttp é necessário para upload de mídia")
    
    async def upload(
        self,
        filepath: str,
        upload_url: str,
        to_jid: str,
        from_jid: str,
        progress_callback: Optional[Callable[[str, str, str, int], None]] = None,
        chunk_size: int = 8192
    ) -> Dict[str, str]:
        """
        Faz upload de arquivo via HTTP POST multipart/form-data.
        
        Baseado em MediaUploader.run() do zowsuplib:
        1. Lê arquivo do filesystem
        2. Constrói multipart/form-data com "to", "from", "file"
        3. Faz POST HTTP/HTTPS
        4. Parseia resposta JSON e retorna url/direct_path
        
        Args:
            filepath: Caminho do arquivo a fazer upload
            upload_url: URL completa de upload (inclui auth e token)
            to_jid: JID do destinatário
            from_jid: JID do remetente (account JID)
            progress_callback: Callback(opcional): (filepath, to_jid, upload_url, percentage) -> None
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
        
        # Gera nome criptográfico para o arquivo (baseado em MediaUploader)
        m = hashlib.md5()
        m.update(filename.encode())
        crypto = m.hexdigest() + os.path.splitext(filename)[1]
        
        # Prepara from_jid (remove @whatsapp.net)
        from_jid_clean = from_jid.replace("@whatsapp.net", "")
        
        logger.debug(
            f"Iniciando upload: file={filename} ({filesize} bytes), "
            f"to={to_jid}, url={upload_url[:50]}..."
        )
        
        # Abre arquivo e prepara multipart/form-data
        try:
            with open(filepath, 'rb') as f:
                file_data = f.read()
        except Exception as e:
            raise RuntimeError(f"Erro ao ler arquivo {filepath}: {e}")
        
        # Prepara dados do formulário
        data = aiohttp.FormData()
        data.add_field('to', to_jid)
        data.add_field('from', from_jid_clean)
        data.add_field(
            'file',
            file_data,
            filename=crypto,
            content_type='application/octet-stream'  # Tipo genérico, servidor detecta
        )
        
        # Faz upload usando aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                # Calcula progresso durante upload (aproximado via Content-Length)
                total_sent = 0
                last_progress = 0
                
                async def track_progress(chunk):
                    nonlocal total_sent, last_progress
                    total_sent += len(chunk)
                    if filesize > 0:
                        progress_pct = min(int((total_sent / filesize) * 100), 99)
                        # Emite progresso apenas se mudou significativamente
                        if progress_pct != last_progress and progress_pct % 5 == 0:
                            if progress_callback:
                                progress_callback(filepath, to_jid, upload_url, progress_pct)
                            last_progress = progress_pct
                    return chunk
                
                # Faz POST (aiohttp gerencia multipart/form-data automaticamente)
                async with session.post(
                    upload_url,
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=300)  # 5 minutos timeout
                ) as response:
                    response.raise_for_status()
                    
                    # Lê resposta JSON
                    result = await response.json()
                    
                    # Emite progresso 100%
                    if progress_callback:
                        progress_callback(filepath, to_jid, upload_url, 100)
                    
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
        to_jid: str,
        from_jid: str,
        filename: str = "file",
        progress_callback: Optional[Callable[[str, str, str, int], None]] = None
    ) -> Dict[str, str]:
        """
        Faz upload de bytes diretamente (sem arquivo no filesystem).
        
        Útil para upload de dados gerados em memória.
        
        Args:
            data: Bytes a fazer upload
            upload_url: URL completa de upload
            to_jid: JID do destinatário
            from_jid: JID do remetente
            filename: Nome do arquivo (padrão: "file")
            progress_callback: Callback opcional para progresso
        
        Returns:
            dict: {"url": "...", "direct_path": "..."}
        """
        if not HAS_AIOHTTP:
            raise RuntimeError("aiohttp é necessário para upload de mídia")
        
        filesize = len(data)
        
        # Gera nome criptográfico
        m = hashlib.md5()
        m.update(filename.encode())
        crypto = m.hexdigest() + os.path.splitext(filename)[1]
        
        # Prepara from_jid
        from_jid_clean = from_jid.replace("@whatsapp.net", "")
        
        logger.debug(
            f"Iniciando upload de bytes: filename={filename} ({filesize} bytes), "
            f"to={to_jid}, url={upload_url[:50]}..."
        )
        
        # Prepara dados do formulário
        form_data = aiohttp.FormData()
        form_data.add_field('to', to_jid)
        form_data.add_field('from', from_jid_clean)
        form_data.add_field(
            'file',
            data,
            filename=crypto,
            content_type='application/octet-stream'
        )
        
        # Faz upload
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    upload_url,
                    data=form_data,
                    timeout=aiohttp.ClientTimeout(total=300)
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    
                    if progress_callback:
                        progress_callback(filename, to_jid, upload_url, 100)
                    
                    url = result.get("url")
                    direct_path = result.get("direct_path")
                    
                    if not url:
                        raise RuntimeError(
                            f"Upload falhou: resposta não contém 'url'. "
                            f"Resultado: {result}"
                        )
                    
                    logger.info(
                        f"Upload de bytes concluído: filename={filename}, "
                        f"url={url[:50]}..."
                    )
                    
                    return {
                        "url": url,
                        "direct_path": direct_path or "",
                    }
                    
        except Exception as e:
            logger.error(f"Erro ao fazer upload de bytes {filename}: {e}", exc_info=True)
            raise

