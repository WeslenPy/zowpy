"""
TCP Stream Bridge - Bridge único que gerencia TCP ↔ Stream.

Baseado no zowsuplib NoiseLayer._handle_stream_event(), mas totalmente assíncrono.
Dois loops paralelos: TCP→Stream e Stream→TCP
"""

import asyncio
import struct
from typing import Optional
from loguru import logger

from .connection import AsyncConnection
from ..noise.stream import AsyncSegmentedStream, StreamCancelledError


class TCPStreamBridge:
    """
    Bridge único que gerencia comunicação TCP ↔ Stream.
    
    Baseado no zowsuplib:
    - NoiseLayer._handle_stream_event() para eventos do stream
    - NoiseSegmentsLayer para segmentação
    
    Fluxo:
    - TCP → Stream: recebe dados TCP, processa segmentação (3 bytes + dados), adiciona ao stream
    - Stream → TCP: pega dados do stream, segmenta (3 bytes + dados), envia via TCP
    """
    
    def __init__(self, connection: AsyncConnection, stream: AsyncSegmentedStream):
        """
        Inicializa bridge.
        
        Args:
            connection: Conexão TCP
            stream: Stream segmentado
        """
        self._connection = connection
        self._stream = stream
        self._running = False
        self._read_task: Optional[asyncio.Task] = None
        self._write_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """
        Inicia bridge (dois loops paralelos).
        
        CRÍTICO: Este método deve ser chamado ANTES do handshake começar.
        O handshake precisa do bridge ativo para enviar/receber dados.
        """
        if self._running:
            logger.warning("Bridge já está rodando")
            return
        
        logger.info("Iniciando bridge TCP ↔ Stream")
        self._running = True
        
        # Inicia dois loops paralelos
        self._read_task = asyncio.create_task(self._tcp_to_stream_loop())
        self._write_task = asyncio.create_task(self._stream_to_tcp_loop())
        
        logger.info("Bridge TCP ↔ Stream iniciado (dois loops paralelos)")
    
    async def stop(self) -> None:
        """Para o bridge"""
        if not self._running:
            return
        
        logger.info("Parando bridge TCP ↔ Stream")
        self._running = False
        
        # Cancela tasks
        if self._read_task:
            self._read_task.cancel()
        if self._write_task:
            self._write_task.cancel()
        
        # Aguarda tasks terminarem
        await asyncio.gather(
            self._read_task,
            self._write_task,
            return_exceptions=True
        )
        
        logger.info("Bridge TCP ↔ Stream parado")
    
    async def _tcp_to_stream_loop(self) -> None:
        """
        Loop: TCP → segmentação → Stream
        
        Baseado no zowsuplib:
        - NoiseSegmentsLayer.receive() processa segmentação
        - NoiseLayer.receive() adiciona à incoming_segments_queue
        - _handle_stream_event(EVENT_READ) → put_read_segment()
        """
        logger.info("Bridge: loop TCP→Stream iniciado")
        buffer = bytearray()
        
        try:
            # Pequeno delay inicial para evitar ler antes do handshake começar
            await asyncio.sleep(0.1)
            
            while self._running:
                try:
                    # Verifica se conexão ainda está ativa
                    if not self._connection.is_connected():
                        logger.warning("Bridge: conexão não está mais ativa, encerrando loop TCP→Stream")
                        break
                    
                    # Lê chunk do TCP
                    data = await self._connection.read_chunk(4096)
                    
                    if not data:
                        # EOF - conexão fechada
                        logger.info("Bridge: EOF recebido do TCP, encerrando loop")
                        await self._stream.cancel()
                        break
                    
                    logger.debug(f"Bridge: recebidos {len(data)} bytes do TCP")
                    
                    # Adiciona ao buffer
                    buffer.extend(data)
                    
                    # Processa segmentação (3 bytes big-endian + dados)
                    # Baseado em NoiseSegmentsLayer.receive()
                    segments_processed = 0
                    while len(buffer) >= 3:
                        # Lê tamanho (3 bytes big-endian)
                        size_bytes = bytes(buffer[:3])
                        size = struct.unpack('>I', b'\x00' + size_bytes)[0]
                        
                        # Valida tamanho (máximo 16MB - 1)
                        if size >= 16777216:
                            logger.error(f"Bridge: segmento muito grande: {size} bytes")
                            buffer.clear()
                            break
                        
                        # Verifica se temos dados completos
                        total_size = 3 + size
                        if len(buffer) < total_size:
                            # Ainda não temos o segmento completo, aguarda mais dados
                            logger.debug(f"Bridge: aguardando mais dados (temos {len(buffer)}, precisamos {total_size})")
                            break
                        
                        # Extrai segmento completo (sem os 3 bytes de tamanho)
                        segment = bytes(buffer[3:total_size])
                        buffer = buffer[total_size:]
                        
                        logger.info(f"Bridge: segmento completo de {len(segment)} bytes extraído do TCP")
                        logger.debug(f"Bridge: primeiros 50 bytes do segmento (hex): {segment[:50].hex() if len(segment) >= 50 else segment.hex()}")
                        
                        # Adiciona segmento ao stream (equivalente a put_read_segment)
                        await self._stream.put_read_segment(segment)
                        segments_processed += 1
                        logger.info(f"Bridge: ✓ segmento de {len(segment)} bytes adicionado ao stream (total processados: {segments_processed})")
                    
                    if segments_processed > 0:
                        logger.debug(f"Bridge: processados {segments_processed} segmentos nesta iteração")
                
                except StreamCancelledError:
                    logger.info("Bridge: stream cancelado, encerrando loop TCP→Stream")
                    await self._stream.cancel()
                    break
                except ConnectionError as e:
                    logger.error(f"Bridge: erro de conexão no loop TCP→Stream: {e}")
                    break
                except Exception as e:
                    logger.error(f"Bridge: erro no loop TCP→Stream: {e}", exc_info=True)
                    await asyncio.sleep(0.1)  # Pequeno delay antes de tentar novamente
        
        except asyncio.CancelledError:
            logger.debug("Bridge: loop TCP→Stream cancelado")
        finally:
            logger.info("Bridge: loop TCP→Stream encerrado")
    
    async def _stream_to_tcp_loop(self) -> None:
        """
        Loop: Stream → segmentação → TCP
        
        Baseado no zowsuplib:
        - NoiseLayer._handle_stream_event(EVENT_WRITE) → get_write_segment()
        - NoiseSegmentsLayer.send() segmenta dados (3 bytes + dados)
        - toLower() envia via TCP
        """
        logger.info("Bridge: loop Stream→TCP iniciado")
        
        try:
            while self._running:
                try:
                    # Verifica se conexão ainda está ativa antes de aguardar dados
                    if not self._connection.is_connected():
                        logger.warning("Bridge: conexão não está mais ativa, encerrando loop Stream→TCP")
                        break
                    
                    # Obtém dados do stream para enviar (equivalente a get_write_segment)
                    # Timeout de 1s para não bloquear indefinidamente
                    logger.debug("Bridge: aguardando dados do stream para enviar via TCP...")
                    data = await self._stream.get_write_segment(timeout=1.0)
                    
                    if not data:
                        logger.debug("Bridge: dados vazios, ignorando")
                        continue
                    
                    # Verifica novamente se conexão ainda está ativa antes de enviar
                    if not self._connection.is_connected():
                        logger.warning("Bridge: conexão fechada durante espera, descartando dados")
                        break
                    
                    logger.info(f"Bridge: recebidos {len(data)} bytes do stream para enviar via TCP")
                    logger.debug(f"Bridge: primeiros 50 bytes (hex): {data[:50].hex() if len(data) >= 50 else data.hex()}")
                    
                    # Valida tamanho máximo (3 bytes = 16MB - 1)
                    if len(data) >= 16777216:
                        raise ValueError(f"Data too large to write; length={len(data)}")
                    
                    # Segmenta dados: 3 bytes (tamanho big-endian) + dados
                    # Baseado em NoiseSegmentsLayer.send()
                    # Formato: struct.pack('>I', len(data))[1:] + data
                    size_bytes = struct.pack('>I', len(data))[1:]
                    segment = size_bytes + data
                    
                    logger.debug(f"Bridge: segmento preparado: {len(size_bytes)} bytes (tamanho) + {len(data)} bytes (dados) = {len(segment)} bytes total")
                    logger.debug(f"Bridge: bytes de tamanho (hex): {size_bytes.hex()}")
                    
                    # Envia via TCP
                    await self._connection.write(segment)
                    logger.info(f"Bridge: ✓ enviados {len(data)} bytes via TCP (segmento total: {len(segment)} bytes)")
                    
                except asyncio.TimeoutError:
                    # Timeout normal - verifica se ainda está rodando
                    logger.debug("Bridge: timeout aguardando dados do stream (normal)")
                    if not self._running:
                        break
                    continue
                except StreamCancelledError:
                    logger.info("Bridge: stream cancelado, encerrando loop Stream→TCP")
                    break
                except ConnectionError as e:
                    logger.error(f"Bridge: erro de conexão no loop Stream→TCP: {e}")
                    break
                except Exception as e:
                    logger.error(f"Bridge: erro no loop Stream→TCP: {e}", exc_info=True)
                    await asyncio.sleep(0.1)  # Pequeno delay antes de tentar novamente
        
        except asyncio.CancelledError:
            logger.debug("Bridge: loop Stream→TCP cancelado")
        finally:
            logger.info("Bridge: loop Stream→TCP encerrado")
    
    def is_running(self) -> bool:
        """Verifica se o bridge está rodando"""
        return self._running

