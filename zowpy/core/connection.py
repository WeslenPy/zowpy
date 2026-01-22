"""
Async Connection V2 - Conexão TCP simplificada com métodos diretos.

Baseado no zowsuplib, mas totalmente assíncrono e sem callbacks complexos.
Métodos diretos: connect(), send_header(), read_chunk(), write()
"""

import asyncio
import socket
import struct
from typing import Optional, Tuple, Dict, Any
from loguru import logger

# Header do protocolo WhatsApp
WA_HEADER = b'WA\x06\x03'


class ConnectionError(Exception):
    """Erro de conexão"""
    pass


class AsyncConnection:
    """
    Conexão TCP simplificada com métodos diretos.
    
    Baseado no zowsuplib SocketConnectionDispatcher, mas totalmente assíncrono.
    Sem callbacks complexos, apenas métodos diretos.
    """
    
    def __init__(
        self,
        endpoint: Tuple[str, int],
        proxy: Optional[Dict[str, any]] = None
    ):
        """
        Inicializa conexão TCP assíncrona.
        
        Args:
            endpoint: Tupla (host, port) - ex: ("e15.whatsapp.net", 5222)
            proxy: Dicionário com configuração de proxy {"host": "...", "port": ..., "type": "socks5", "username": "...", "password": "..."}
        """
        self.host, self.port = endpoint
        self.proxy = proxy
        
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self._connected = False
        self._header_sent = False
    
    async def connect(self, timeout: float = 30.0) -> None:
        """
        Conecta TCP socket de forma totalmente assíncrona.
        
        Args:
            timeout: Timeout de conexão em segundos
        
        Raises:
            ConnectionError: Se conexão falhar
        """
        try:
            logger.info(f"Conectando TCP socket a {self.host}:{self.port}")
            
            # Conecta TCP socket - await, não bloqueia
            if self.proxy:
                # Conecta via proxy SOCKS5
                self.reader, self.writer = await self._connect_via_proxy(timeout)
            else:
                # Conexão direta
                self.reader, self.writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port),
                    timeout=timeout
                )
            
            logger.info(f"TCP socket conectado a {self.host}:{self.port}")
            self._connected = True
            
        except asyncio.TimeoutError:
            raise ConnectionError(f"Timeout conectando em {timeout}s")
        except Exception as e:
            raise ConnectionError(f"Erro ao conectar: {e}") from e
    
    async def _connect_via_proxy(self, timeout: float) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """
        Conecta via proxy SOCKS5 ou HTTP CONNECT de forma assíncrona.
        
        Args:
            timeout: Timeout de conexão
        
        Returns:
            Tuple[StreamReader, StreamWriter]: Reader e writer da conexão
        """
        proxy_type = self.proxy.get("type", "socks5")
        
        if proxy_type == "socks5":
            return await self._connect_via_socks5(timeout)
        elif proxy_type == "http":
            return await self._connect_via_http_proxy(timeout)
        else:
            raise ConnectionError(f"Tipo de proxy não suportado: {proxy_type}")
    
    async def _connect_via_socks5(self, timeout: float) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """
        Conecta via proxy SOCKS5 de forma assíncrona.
        
        Args:
            timeout: Timeout de conexão
        
        Returns:
            Tuple[StreamReader, StreamWriter]: Reader e writer da conexão
        """
        try:
            # Tenta usar socksio (assíncrono) se disponível
            try:
                import socksio
                
                proxy_host = self.proxy.get("host")
                proxy_port = self.proxy.get("port")
                proxy_username = self.proxy.get("username")
                proxy_password = self.proxy.get("password")
                
                # Cria cliente SOCKS5 assíncrono
                socks_client = socksio.SOCKS5(
                    proxy_host,
                    proxy_port,
                    username=proxy_username if proxy_username else None,
                    password=proxy_password if proxy_password else None,
                )
                
                # Conecta via proxy de forma assíncrona
                sock = await asyncio.wait_for(
                    socks_client.connect((self.host, self.port)),
                    timeout=timeout
                )
                
                # Cria StreamReader/Writer a partir do socket
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(sock=sock),
                    timeout=timeout
                )
                
                logger.info(f"Conectado via proxy SOCKS5 (socksio) {proxy_host}:{proxy_port}")
                return reader, writer
                
            except ImportError:
                # Fallback para PySocks síncrono em thread pool
                logger.debug("socksio não disponível, usando PySocks síncrono")
                return await self._connect_via_proxy_pysocks(timeout)
                
        except ImportError:
            raise ConnectionError(
                "Proxy SOCKS5 requer 'socksio' ou 'PySocks'. "
                "Instale com: pip install socksio ou pip install PySocks"
            )
        except Exception as e:
            raise ConnectionError(f"Erro ao conectar via proxy SOCKS5: {e}") from e
    
    async def _connect_via_http_proxy(self, timeout: float) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """
        Conecta via HTTP proxy CONNECT de forma assíncrona.
        
        Implementa HTTP CONNECT method para tunneling TCP através de proxy HTTP.
        
        Args:
            timeout: Timeout de conexão
        
        Returns:
            Tuple[StreamReader, StreamWriter]: Reader e writer da conexão
            
        Raises:
            ConnectionError: Se conexão ou CONNECT falhar
        """
        import base64
        
        proxy_host = self.proxy.get("host")
        proxy_port = self.proxy.get("port")
        proxy_username = self.proxy.get("username")
        proxy_password = self.proxy.get("password")
        
        try:
            # Conecta ao proxy HTTP
            logger.debug(f"Conectando ao proxy HTTP {proxy_host}:{proxy_port}...")
            proxy_reader, proxy_writer = await asyncio.wait_for(
                asyncio.open_connection(proxy_host, proxy_port),
                timeout=timeout
            )
            
            # Monta requisição CONNECT
            connect_request = f"CONNECT {self.host}:{self.port} HTTP/1.1\r\n"
            connect_request += f"Host: {self.host}:{self.port}\r\n"
            
            # Adiciona autenticação Basic se disponível
            if proxy_username and proxy_password:
                auth_string = f"{proxy_username}:{proxy_password}"
                auth_bytes = auth_string.encode('ascii')
                auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
                connect_request += f"Proxy-Authorization: Basic {auth_b64}\r\n"
            
            connect_request += "\r\n"
            
            # Envia requisição CONNECT
            proxy_writer.write(connect_request.encode('ascii'))
            await proxy_writer.drain()
            
            # Lê linha de status da resposta
            response_line_bytes = await asyncio.wait_for(
                proxy_reader.readline(),
                timeout=timeout
            )
            
            if not response_line_bytes:
                raise ConnectionError("Proxy não respondeu à requisição CONNECT")
            
            response_line = response_line_bytes.decode('ascii', errors='ignore').strip()
            logger.debug(f"Resposta do proxy: {response_line}")
            
            # Parse status code
            parts = response_line.split(' ', 2)
            if len(parts) < 2:
                raise ConnectionError(f"Resposta de proxy inválida: {response_line}")
            
            try:
                status_code = int(parts[1])
            except (ValueError, IndexError):
                raise ConnectionError(f"Status code inválido na resposta: {response_line}")
            
            # Lê headers restantes (até linha vazia)
            while True:
                header_line = await asyncio.wait_for(
                    proxy_reader.readline(),
                    timeout=timeout
                )
                if header_line == b"\r\n" or header_line == b"\n":
                    break
                # Log header para debug se necessário
                logger.debug(f"Proxy header: {header_line.decode('ascii', errors='ignore').strip()}")
            
            # Verifica status code
            if status_code != 200:
                # Lê body da resposta se houver (para log de erro)
                error_body = b""
                while proxy_reader.at_eof() == False:
                    try:
                        chunk = await asyncio.wait_for(
                            proxy_reader.read(1024),
                            timeout=2.0
                        )
                        if not chunk:
                            break
                        error_body += chunk
                    except asyncio.TimeoutError:
                        break
                
                error_msg = error_body.decode('ascii', errors='ignore')[:200] if error_body else ""
                raise ConnectionError(
                    f"Proxy CONNECT falhou com status {status_code}: {response_line}. {error_msg}"
                )
            
            logger.info(f"Conectado via proxy HTTP CONNECT {proxy_host}:{proxy_port} -> {self.host}:{self.port}")
            return proxy_reader, proxy_writer
            
        except asyncio.TimeoutError as e:
            raise ConnectionError(f"Timeout ao conectar via proxy HTTP: {e}") from e
        except Exception as e:
            raise ConnectionError(f"Erro ao conectar via proxy HTTP: {e}") from e
    
    async def _connect_via_proxy_pysocks(self, timeout: float) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """
        Conecta via proxy SOCKS5 usando PySocks em thread pool.
        """
        try:
            import socks
            
            proxy_host = self.proxy.get("host")
            proxy_port = self.proxy.get("port")
            proxy_username = self.proxy.get("username")
            proxy_password = self.proxy.get("password")
            
            # Usa PySocks síncrono em thread pool
            def _connect_sync():
                sock = socks.socksocket(socket.AF_INET, socket.SOCK_STREAM)
                
                if proxy_username and proxy_password:
                    sock.set_proxy(
                        socks.PROXY_TYPE_SOCKS5,
                        proxy_host,
                        proxy_port,
                        username=proxy_username,
                        password=proxy_password,
                        rdns=True
                    )
                else:
                    sock.set_proxy(
                        socks.PROXY_TYPE_SOCKS5,
                        proxy_host,
                        proxy_port,
                        rdns=True
                    )
                
                sock.connect((self.host, self.port))
                return sock
            

            logger.info(f"Conectando via proxy SOCKS5 (PySocks) {proxy_host}:{proxy_port}")
            # Conecta em thread pool
            sock = await asyncio.wait_for(
                asyncio.to_thread(_connect_sync),
                timeout=timeout
            )
            
            # Cria StreamReader/Writer a partir do socket conectado
            loop = asyncio.get_event_loop()
            reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(reader)
            
            try:
                transport, _ = await loop._make_socket_transport(sock, protocol, None, None)
            except AttributeError:
                raise ConnectionError(
                    "Proxy SOCKS5 requer 'socksio' para suporte assíncrono completo. "
                    "Instale com: pip install socksio"
                )
            
            writer = asyncio.StreamWriter(transport, protocol, reader, loop)
            
            logger.info(f"Conectado via proxy SOCKS5 (PySocks) {proxy_host}:{proxy_port}")
            return reader, writer
            
        except ImportError:
            raise ConnectionError(
                "Proxy SOCKS5 requer 'PySocks' ou 'socksio'. "
                "Instale com: pip install PySocks ou pip install socksio"
            )
        except Exception as e:
            raise ConnectionError(f"Erro ao conectar via proxy: {e}") from e
    
    async def send_header(self) -> None:
        """
        Envia header WA\x06\x03 após conexão.
        
        Baseado no zowsuplib: NoiseLayer.toLower(self.HEADER)
        """
        if self._header_sent:
            return
        
        if not self.writer:
            raise ConnectionError("Writer não disponível")
        
        try:
            logger.debug("Enviando header WA\\x06\\x03")
            self.writer.write(WA_HEADER)
            await self.writer.drain()
            self._header_sent = True
            logger.info("Header WA\\x06\\x03 enviado")
        except Exception as e:
            logger.error(f"Erro ao enviar header: {e}")
            raise ConnectionError(f"Erro ao enviar header: {e}") from e
    
    async def read_chunk(self, size: int = 4096) -> bytes:
        """
        Lê chunk do TCP de forma assíncrona.
        
        Args:
            size: Tamanho do chunk a ler
        
        Returns:
            bytes: Dados lidos (pode ser menor que size se EOF)
        
        Raises:
            ConnectionError: Se não estiver conectado
        """
        if not self._connected or not self.reader:
            raise ConnectionError("Não conectado")
        
        try:
            data = await self.reader.read(size)
            if not data:
                # EOF - conexão fechada
                logger.warning("Socket fechado pelo servidor (EOF)")
                self._connected = False
            return data
        except Exception as e:
            logger.error(f"Erro ao ler do TCP: {e}")
            self._connected = False
            raise ConnectionError(f"Erro ao ler: {e}") from e
    
    async def write(self, data: bytes) -> None:
        """
        Escreve dados no TCP de forma assíncrona.
        
        Args:
            data: Dados para escrever
        
        Raises:
            ConnectionError: Se não estiver conectado
        """
        if not self._connected or not self.writer:
            raise ConnectionError("Não conectado")
        
        try:
            self.writer.write(data)
            await self.writer.drain()
        except Exception as e:
            logger.error(f"Erro ao escrever no TCP: {e}")
            self._connected = False
            raise ConnectionError(f"Erro ao escrever: {e}") from e
    
    async def disconnect(self) -> None:
        """Desconecta de forma assíncrona"""
        self._connected = False
        
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception as e:
                logger.debug(f"Erro ao fechar writer: {e}")
        
        logger.info("TCP socket desconectado")
    
    def is_connected(self) -> bool:
        """Verifica se está conectado"""
        return self._connected and self.writer is not None and not self.writer.is_closing()

