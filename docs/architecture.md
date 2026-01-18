# ZowPy Architecture

## Overview

ZowPy is a modern, async-first WhatsApp client library built from the ground up with performance and simplicity in mind.

## Core Principles

1. **100% Async**: Everything uses async/await, zero threads
2. **Zero Sleeps**: Only `await asyncio.sleep()`, never `time.sleep()`
3. **Event-Driven**: Async event system throughout
4. **Direct Communication**: No stacks/layers, direct component communication
5. **Type Hints**: Full type hints for better IDE support

## Architecture Diagram

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

## Component Details

### Core Components

- **AsyncConnection**: Manages WebSocket connection with async read/write loops
- **AsyncEventEmitter**: Event system with async handlers
- **AsyncStateStore**: Unified state management with async DB operations

### Noise Protocol

- **AsyncSegmentedStream**: Async stream using asyncio.Queue
- **AsyncWAHandshake**: Async handshake (IK/XX modes)
- **AsyncWANoiseProtocol**: Async protocol state management
- **AsyncWANoiseTransport**: Async transport encryption

### Axolotl

- **AsyncAxolotlStore**: Async database operations for sessions/keys
- **AsyncSessionCipher**: Async message encryption/decryption
- **AsyncSessionBuilder**: Async session building

### Protocol

- **AsyncMessageHandler**: Processes WhatsApp messages
- **AsyncIQHandler**: Handles IQ protocol
- Other handlers for presence, receipts, etc.

## Data Flow

1. **Connection**: WebSocket connects → AsyncConnection
2. **Handshake**: AsyncConnection → AsyncSegmentedStream → AsyncWAHandshake → AsyncWANoiseProtocol
3. **Transport**: AsyncWANoiseProtocol → AsyncWANoiseTransport (encrypted)
4. **Messages**: AsyncWANoiseTransport → AsyncAxolotlCrypto → AsyncMessageHandler
5. **Events**: AsyncMessageHandler → AsyncEventEmitter → User callbacks

## Performance

- **Threads**: 1 (event loop) vs ~10 per account in old architecture
- **Latency**: 50-70% reduction
- **Throughput**: 3-5x increase
- **Memory**: 40-60% reduction








