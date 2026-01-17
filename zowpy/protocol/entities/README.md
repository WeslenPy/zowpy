# Protocol Entities

Classes que herdam de `ProtocolNode` para abstrair a construção de nodes, similar ao padrão do zowsuplib.

## Estrutura

Todas as entidades herdam de `ProtocolEntity`, que por sua vez herda de `ProtocolNode`. Isso significa que todas as entidades são `ProtocolNode` válidos e podem ser usados diretamente.

## Exemplos de Uso

### Autenticação

```python
from zowpy.protocol.entities import AuthProtocolEntity

# Criar node de autenticação
auth = AuthProtocolEntity(
    mechanism="WAUTH-2",
    user="1234567890",
    passive="false"
)

# auth é um ProtocolNode válido e pode ser enviado diretamente
await client._send_protocol_node(auth)
```

### Mensagens

```python
from zowpy.protocol.entities import TextMessageProtocolEntity, EncProtocolEntity

# Criar node de criptografia
enc = EncProtocolEntity(
    enc_type=EncProtocolEntity.TYPE_MSG,
    ciphertext=encrypted_bytes,
    mediatype="text"
)

# Criar mensagem de texto
message = TextMessageProtocolEntity(
    to="1234567890@s.whatsapp.net",
    text="Hello World",
    enc_node=enc,
    proto_data=proto_bytes
)

# message é um ProtocolNode válido
await client._send_protocol_node(message)
```

### IQ (Info/Query)

```python
from zowpy.protocol.entities import GetKeysIqProtocolEntity, SetKeysIqProtocolEntity

# Obter chaves
get_keys = GetKeysIqProtocolEntity(
    jids=["1234567890@s.whatsapp.net", "0987654321@s.whatsapp.net"]
)

# Definir chaves
set_keys = SetKeysIqProtocolEntity(
    identity_key=identity_bytes,
    signed_pre_key=signed_pre_key_bytes,
    pre_keys=[
        {"id": 1, "key": pre_key_1_bytes},
        {"id": 2, "key": pre_key_2_bytes},
    ],
    registration_id=12345
)
```

### Presence

```python
from zowpy.protocol.entities import PresenceProtocolEntity

# Marcar como disponível
presence = PresenceProtocolEntity(
    presence_type=PresenceProtocolEntity.TYPE_AVAILABLE
)

# Marcar como digitando
composing = PresenceProtocolEntity(
    presence_type=PresenceProtocolEntity.TYPE_COMPOSING,
    to="1234567890@s.whatsapp.net"
)
```

### Receipts e Acks

```python
from zowpy.protocol.entities import ReceiptProtocolEntity, AckProtocolEntity

# Enviar receipt de leitura
receipt = ReceiptProtocolEntity(
    receipt_type=ReceiptProtocolEntity.TYPE_READ,
    message_ids=["msg_id_1", "msg_id_2"],
    to="1234567890@s.whatsapp.net"
)

# Enviar ack
ack = AckProtocolEntity(
    message_id="msg_id_1",
    ack_class="message"
)
```

## Conversão de/para ProtocolNode

Todas as entidades podem ser convertidas de/para `ProtocolNode`:

```python
from zowpy.protocol.entities import ProtocolEntity, AuthProtocolEntity
from zowpy.protocol.structs import ProtocolNode

# Criar ProtocolNode manualmente
node = ProtocolNode(
    tag="auth",
    attributes={"mechanism": "WAUTH-2", "user": "1234567890"}
)

# Converter para entidade
auth = ProtocolEntity.from_protocol_node(node)

# Converter entidade para ProtocolNode (já é um ProtocolNode)
node = auth.to_protocol_node()
```

## Vantagens

1. **Type Safety**: Type hints completos para todos os parâmetros
2. **Abstração**: Não precisa lembrar a estrutura exata do XML
3. **Validação**: Valores padrão corretos seguindo o padrão do zowsuplib
4. **Compatibilidade**: Todas as entidades são `ProtocolNode` válidos
5. **Extensibilidade**: Fácil adicionar novas entidades seguindo o mesmo padrão

