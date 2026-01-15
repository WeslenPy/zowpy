# ZowPy

Modern, async-first WhatsApp client library for Python.

## Features

- 🚀 **100% Async**: Zero threads, zero sleeps, just await
- ⚡ **High Performance**: Similar to whatsmeow in Go
- 🎯 **Simple API**: No stacks, no layers, direct communication
- 🔒 **Secure**: Axolotl encryption, Noise protocol
- 📦 **Modern**: Python 3.11+, type hints, async/await

## Quick Start

```python
import asyncio
from zowpy import ZowPyClient

async def main():
    # Create client
    client = ZowPyClient("5511999999999")
    
    # Events
    @client.on_message
    async def handle_message(message):
        print(f"Received: {message.text} from {message.from_jid}")
    
    # Connect
    await client.connect()
    
    # Send message
    msg_id = await client.send_text("5511888888888", "Hello!")
    print(f"Message sent: {msg_id}")
    
    # Wait for response
    response = await client.wait_for_message(timeout=30.0)
    print(f"Response: {response.text}")
    
    # Disconnect
    await client.disconnect()

asyncio.run(main())
```

## Installation

```bash
pip install zowpy
```

## Architecture

- **Zero Threads**: Only event loop, no threading
- **Zero Sleeps**: Only await, no time.sleep()
- **Direct Communication**: No stacks/layers
- **Event-Driven**: Async events everywhere

## Requirements

- Python 3.11+
- Async/await support

## Architecture

ZowPy follows a modern async-first architecture:

```
ZowPyClient (Public API)
    ↓
WhatsAppClient (Core)
    ├── AsyncConnection (WebSocket)
    ├── AsyncWANoiseProtocol (Noise Protocol)
    │   ├── AsyncWAHandshake
    │   ├── AsyncWANoiseTransport
    │   └── AsyncSegmentedStream
    ├── AsyncAxolotlCrypto (Encryption)
    │   ├── AsyncSessionCipher
    │   ├── AsyncSessionBuilder
    │   └── AsyncAxolotlStore
    ├── AsyncMessageHandler (Protocol)
    └── AsyncStateStore (State)
```

## Components

### Core
- **AsyncEventEmitter**: Async event system
- **AsyncConnection**: WebSocket connection manager
- **AsyncStateStore**: Unified state management

### Noise Protocol
- **AsyncSegmentedStream**: Async stream using asyncio.Queue
- **AsyncWAHandshake**: Async handshake (IK/XX modes)
- **AsyncWANoiseProtocol**: Async protocol state management
- **AsyncWANoiseTransport**: Async transport encryption

### Axolotl
- **AsyncAxolotlStore**: Async database operations
- **AsyncSessionCipher**: Async message encryption/decryption
- **AsyncSessionBuilder**: Async session building

### Protocol
- **AsyncMessageHandler**: Processes WhatsApp messages
- **AsyncIQHandler**: Handles IQ protocol
- **AsyncPresenceHandler**: Handles presence
- **AsyncReceiptHandler**: Handles receipts

## Development

### Setup

```bash
# Clone repository
git clone <repository-url>
cd zowpy

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit

# Run integration tests
pytest tests/integration -m integration
```

## Contributing

Contributions are welcome! Please ensure:
- All code is async/await based
- No `time.sleep()` calls (use `await asyncio.sleep()`)
- No unnecessary threads
- Type hints are provided
- Tests are included

## License

GPL-3.0-or-later

