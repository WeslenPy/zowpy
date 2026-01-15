# Protobuf - Sistema Assíncrono Estilo Whatsmeow

Este módulo implementa um sistema de protobuf assíncrono inspirado no whatsmeow (biblioteca Go para WhatsApp).

## Características

- **100% Assíncrono**: Todas operações de serialização/deserialização são assíncronas
- **Builders Centralizados**: Builders para construção de mensagens (estilo whatsmeow)
- **Parsers Centralizados**: Parsers para parsing de mensagens recebidas
- **Thread Pool**: Operações pesadas executadas em thread pool automaticamente
- **Type-Safe**: Dataclasses para tipos de mensagem

## Estrutura

```
proto/
├── __init__.py          # Exports principais
├── helpers.py           # Helpers assíncronos (serialize_async, deserialize_async)
├── messages.py          # Builders e parsers de mensagens
├── handshake.py         # Builders e parsers de handshake
└── client_payload.py    # Builder de ClientPayload
```

## Uso

### Serialização/Deserialização

```python
from zowpy.proto.helpers import serialize_async, deserialize_async
from zowsuplib.proto.e2e_pb2 import Message

# Serializar
data = await serialize_async(message)

# Deserializar
message = await deserialize_async(data, Message)
```

### Construir Mensagens

```python
from zowpy.proto.messages import AsyncMessageBuilder

# Mensagem de texto
text_data = await AsyncMessageBuilder.build_text("Hello World")

# Mensagem de imagem
image_data = await AsyncMessageBuilder.build_image(
    url="https://example.com/image.jpg",
    mimetype="image/jpeg",
    caption="My image"
)
```

### Parse Mensagens

```python
from zowpy.proto.messages import AsyncMessageParser

# Parse mensagem recebida
parsed = await AsyncMessageParser.parse(message_bytes)
print(f"Type: {parsed['type']}")
print(f"Data: {parsed['data']}")
```

### Handshake

```python
from zowpy.proto.handshake import AsyncHandshakeMessageBuilder

# ClientHello
client_hello = await AsyncHandshakeMessageBuilder.build_client_hello(
    ephemeral=ephemeral_key,
    static=static_key,
    payload=payload_data
)
```

### ClientPayload

```python
from zowpy.proto.client_payload import AsyncClientPayloadBuilder
from zowpy.noise.config import ClientConfig

# Construir ClientPayload
payload = await AsyncClientPayloadBuilder.build(
    client_config=client_config,
    session_id=12345
)
```

## Integração com Handlers

O `AsyncMessageHandler` já usa o sistema de protobuf automaticamente:

```python
from zowpy.protocol.messages import AsyncMessageHandler

handler = AsyncMessageHandler(events)
await handler.handle_message(message_bytes)  # Usa AsyncMessageParser internamente
```

## Princípios

1. **Await Everywhere**: Todas operações são await
2. **Thread Pool**: Operações pesadas em thread pool
3. **Builders**: Construção centralizada (estilo whatsmeow)
4. **Parsers**: Parsing centralizado
5. **Type Safety**: Dataclasses para tipos

## Compatibilidade

- Suporta Google Protobuf (`protobuf`)
- Suporta Betterproto (`betterproto`)
- Fallback para código legado via `zowpy.utils.protobuf`

