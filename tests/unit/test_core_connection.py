"""
Testes unitários para core/connection.py (TCP socket).
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from zowpy.core.connection import AsyncConnection, ConnectionError


class _DummyWriter:
    def __init__(self):
        self.buffer = bytearray()
        self.closed = False

    def write(self, data: bytes):
        self.buffer.extend(data)

    async def drain(self):
        return None

    def close(self):
        self.closed = True

    async def wait_closed(self):
        return None


@pytest.mark.asyncio
async def test_connection_init():
    """Testa inicialização da conexão"""
    connection = AsyncConnection(("test.com", 5222))
    assert connection.host == "test.com"
    assert connection.port == 5222
    assert connection.writer is None
    assert not connection.is_connected()


@pytest.mark.asyncio
async def test_connection_connect_sends_header():
    """Ao conectar, deve enviar header WA\\x06\\x03 e marcar conectado."""
    connection = AsyncConnection(("test.com", 5222))

    dummy_reader = AsyncMock()
    dummy_reader.read = AsyncMock(side_effect=[b"", b""])  # EOF
    dummy_writer = _DummyWriter()

    with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_open:
        mock_open.return_value = (dummy_reader, dummy_writer)

        await connection.connect()
        assert connection.is_connected()

        assert bytes(dummy_writer.buffer).startswith(b"WA\x06\x03")

        await connection.disconnect()


@pytest.mark.asyncio
async def test_connection_connect_timeout():
    """Testa timeout na conexão"""
    connection = AsyncConnection(("test.com", 5222))

    with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_open:
        mock_open.side_effect = asyncio.TimeoutError()

        with pytest.raises(ConnectionError):
            await connection.connect(timeout=0.01)


@pytest.mark.asyncio
async def test_connection_send_writes_to_socket():
    """send() deve enfileirar e o write_loop deve escrever no writer."""
    connection = AsyncConnection(("test.com", 5222))

    dummy_reader = AsyncMock()

    async def _read(_n: int):
        # Mantém o read loop vivo até o disconnect cancelar a task.
        await asyncio.sleep(0.05)
        return b"ping"

    dummy_reader.read = AsyncMock(side_effect=_read)
    dummy_writer = _DummyWriter()

    with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_open:
        mock_open.return_value = (dummy_reader, dummy_writer)

        await connection.connect()
        await connection.send(b"test data")

        # dá chance do loop drenar a fila
        await asyncio.sleep(0)

        assert b"test data" in bytes(dummy_writer.buffer)
        await connection.disconnect()


@pytest.mark.asyncio
async def test_connection_send_not_connected():
    """Testa envio sem estar conectado"""
    connection = AsyncConnection(("test.com", 5222))

    with pytest.raises(ConnectionError):
        await connection.send(b"test data")


@pytest.mark.asyncio
async def test_connection_on_message_callback():
    """Read loop deve repassar bytes para on_message."""
    connection = AsyncConnection(("test.com", 5222))
    received = []

    async def on_message(data: bytes):
        received.append(data)

    connection.on_message = on_message

    dummy_reader = AsyncMock()
    dummy_reader.read = AsyncMock(side_effect=[b"hello", b""])  # 1 msg + EOF
    dummy_writer = _DummyWriter()

    with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_open:
        mock_open.return_value = (dummy_reader, dummy_writer)

        await connection.connect()
        await asyncio.sleep(0)
        await connection.disconnect()

    assert received == [b"hello"]


@pytest.mark.asyncio
async def test_connection_wait_for_connection():
    """wait_for_connection deve resolver quando _connected é setado."""
    connection = AsyncConnection(("test.com", 5222))

    dummy_reader = AsyncMock()
    dummy_reader.read = AsyncMock(side_effect=[b"", b""])  # EOF
    dummy_writer = _DummyWriter()

    with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_open:
        mock_open.return_value = (dummy_reader, dummy_writer)

        connect_task = asyncio.create_task(connection.connect())
        await connection.wait_for_connection(timeout=1.0)
        await connect_task

        assert connection.is_connected()
        await connection.disconnect()

