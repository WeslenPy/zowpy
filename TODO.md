# TODO - Próximas Implementações

## Prioridade Alta

### 1. Completar Handshake Payload
- [ ] Implementar `_create_full_payload()` completo em `AsyncWAHandshake`
- [ ] Integrar com configuração de device (DeviceEnv)
- [ ] Suportar todos modos (registration, login, pairing)

### 2. Implementar Criptografia Axolotl Completa
- [ ] Completar `_encrypt_with_session()` em `AsyncSessionCipher`
- [ ] Completar `_decrypt_with_session()` em `AsyncSessionCipher`
- [ ] Integrar com biblioteca axolotl original
- [ ] Testar encrypt/decrypt end-to-end

### 3. Deserialização de Mensagens
- [ ] Implementar `_deserialize_message()` completo
- [ ] Implementar `_deserialize_iq()` completo
- [ ] Suportar todos tipos de mensagem (text, media, etc.)
- [ ] Parsing de ProtocolTreeNode completo

### 4. Suporte a Proxy
- [ ] Implementar proxy via httpx ou wrapper
- [ ] Suportar SOCKS5 proxy
- [ ] Integrar com NetworkEnv
- [ ] Testar conexão via proxy

## Prioridade Média

### 5. Integração com Código Original
- [ ] Importar código de consonance/handshake.py
- [ ] Importar código de axolotl/
- [ ] Adaptar para async mantendo lógica
- [ ] Testar compatibilidade

### 6. Testes Adicionais
- [ ] Mais testes unitários (cobertura >80%)
- [ ] Testes de integração end-to-end
- [ ] Testes de performance
- [ ] Testes de carga

### 7. Documentação
- [ ] API reference completa
- [ ] Tutoriais detalhados
- [ ] Guias de troubleshooting
- [ ] Exemplos avançados

## Prioridade Baixa

### 8. Features Adicionais
- [ ] Reconexão automática
- [ ] Rate limiting
- [ ] Retry logic
- [ ] Health checks

### 9. Otimizações
- [ ] Connection pooling
- [ ] Message batching
- [ ] Cache otimizado
- [ ] Memory profiling

### 10. Ferramentas
- [ ] CLI tool
- [ ] Admin dashboard
- [ ] Monitoring
- [ ] Logging avançado

## Notas

- Alguns componentes têm stubs que precisam ser completados
- Integração com código original requer cuidado para manter async
- Testes devem cobrir todos cenários assíncronos
- Documentação deve ser clara sobre diferenças do projeto antigo





