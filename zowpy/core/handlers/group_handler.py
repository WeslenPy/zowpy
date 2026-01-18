"""
Group Handler - Gerencia operações de grupo.

Handler público para todas as operações de grupo do WhatsApp.
"""

import asyncio
from typing import List, Dict, Any, Optional
from loguru import logger

from ...protocol.structs import ProtocolNode
from ..builders.group_builder import GroupBuilder
from ..processors.iq_response import IQResponseProcessor


class GroupHandler:
    """
    Gerencia operações de grupo.
    
    Métodos públicos para criar, gerenciar e obter informações de grupos.
    """
    
    def __init__(
        self,
        send_iq_fn: callable,
        iq_response_processor: IQResponseProcessor
    ):
        """
        Inicializa handler.
        
        Args:
            send_iq_fn: Função async para enviar IQ (recebe ProtocolNode)
            iq_response_processor: Processor para gerenciar respostas de IQ
        """
        self._send_iq = send_iq_fn
        self._iq_processor = iq_response_processor
    
    async def create_group(
        self,
        subject: str,
        participants: List[str],
        creator: Optional[str] = None
    ) -> str:
        """
        Cria um novo grupo.
        
        Args:
            subject: Assunto do grupo
            participants: Lista de JIDs dos participantes
            creator: JID do criador (opcional)
        
        Returns:
            JID do grupo criado
        
        Raises:
            Exception: Se criação falhar
        """
        logger.info(f"Criando grupo: subject={subject}, participants={len(participants)}")
        
        # Constrói IQ
        iq_node = GroupBuilder.build_create_group(
            subject=subject,
            participants=participants,
            creator=creator
        )
        
        iq_id = iq_node.get_attribute("id")
        
        # Cria Future para aguardar resposta
        future = asyncio.Future()
        
        async def on_response(node: ProtocolNode):
            """Processa resposta de criação de grupo"""
            try:
                # Verifica se é resultado
                if node.get_attribute("type") != "result":
                    future.set_exception(Exception(f"Erro ao criar grupo: tipo={node.get_attribute('type')}"))
                    return
                
                # Procura node <group> com atributo jid
                group_node = node.get_child("group")
                if group_node:
                    group_jid = group_node.get_attribute("jid")
                    if group_jid:
                        logger.info(f"Grupo criado com sucesso: {group_jid}")
                        future.set_result(group_jid)
                        return
                
                # Tenta obter do atributo "from" se for de g.us
                from_jid = node.get_attribute("from")
                if from_jid and from_jid.endswith("@g.us"):
                    logger.info(f"Grupo criado com sucesso: {from_jid}")
                    future.set_result(from_jid)
                    return
                
                future.set_exception(Exception("Resposta de criação de grupo sem JID"))
            
            except Exception as e:
                future.set_exception(e)
        
        # Registra callback
        self._iq_processor.register_callback(iq_id, on_response, timeout=30.0)
        
        # Envia IQ
        await self._send_iq(iq_node)
        
        # Aguarda resposta
        try:
            group_jid = await asyncio.wait_for(future, timeout=30.0)
            return group_jid
        except asyncio.TimeoutError:
            self._iq_processor.unregister_callback(iq_id)
            raise Exception("Timeout aguardando criação de grupo")
    
    async def get_group_info(self, group_jid: str) -> Dict[str, Any]:
        """
        Obtém informações do grupo.
        
        Args:
            group_jid: JID do grupo
        
        Returns:
            Dict com informações do grupo (subject, participants, admins, etc.)
        
        Raises:
            Exception: Se obtenção falhar
        """
        logger.info(f"Obtendo informações do grupo: {group_jid}")
        
        iq_node = GroupBuilder.build_get_info(group_jid)
        iq_id = iq_node.get_attribute("id")
        
        future = asyncio.Future()
        
        async def on_response(node: ProtocolNode):
            """Processa resposta de informações do grupo"""
            try:
                if node.get_attribute("type") != "result":
                    future.set_exception(Exception(f"Erro ao obter informações: tipo={node.get_attribute('type')}"))
                    return
                
                # Extrai informações do node <group>
                group_node = node.get_child("group")
                if not group_node:
                    future.set_exception(Exception("Resposta sem node <group>"))
                    return
                
                info = {
                    "jid": group_node.get_attribute("jid") or group_jid,
                    "subject": group_node.get_attribute("subject") or "",
                    "subject_owner": group_node.get_attribute("s_o") or "",
                    "subject_time": group_node.get_attribute("s_t") or "",
                    "creation": group_node.get_attribute("creation") or "",
                    "creator": group_node.get_attribute("creator") or "",
                    "participants": [],
                    "admins": []
                }
                
                # Extrai participantes
                for child in group_node.children:
                    if child.tag == "participant":
                        jid = child.get_attribute("jid")
                        participant_type = child.get_attribute("type")
                        if jid:
                            info["participants"].append(jid)
                            if participant_type == "admin":
                                info["admins"].append(jid)
                
                logger.info(f"Informações do grupo obtidas: {info['jid']}, participants={len(info['participants'])}")
                future.set_result(info)
            
            except Exception as e:
                future.set_exception(e)
        
        self._iq_processor.register_callback(iq_id, on_response, timeout=30.0)
        await self._send_iq(iq_node)
        
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._iq_processor.unregister_callback(iq_id)
            raise Exception("Timeout aguardando informações do grupo")
    
    async def get_group_participants(self, group_jid: str, own_jid: Optional[str] = None) -> List[str]:
        """
        Obtém lista de participantes do grupo (apenas JIDs).
        
        Método auxiliar para sender key distribution.
        
        Args:
            group_jid: JID do grupo
            own_jid: JID próprio para remover da lista (opcional)
        
        Returns:
            Lista de JIDs dos participantes (sem o próprio JID)
        
        Raises:
            Exception: Se obtenção falhar
        """
        info = await self.get_group_info(group_jid)
        participants = info.get("participants", [])
        
        # Remove próprio JID se estiver na lista
        if own_jid and own_jid in participants:
            participants.remove(own_jid)
        
        return participants
    
    async def list_groups(self, include_participants: bool = True) -> List[Dict[str, Any]]:
        """
        Lista todos os grupos.
        
        Args:
            include_participants: Se deve incluir lista de participantes
        
        Returns:
            Lista de dicts com informações dos grupos
        
        Raises:
            Exception: Se listagem falhar
        """
        logger.info("Listando grupos")
        
        iq_node = GroupBuilder.build_list_groups(include_participants=include_participants)
        iq_id = iq_node.get_attribute("id")
        
        future = asyncio.Future()
        
        async def on_response(node: ProtocolNode):
            """Processa resposta de listagem de grupos"""
            try:
                if node.get_attribute("type") != "result":
                    future.set_exception(Exception(f"Erro ao listar grupos: tipo={node.get_attribute('type')}"))
                    return
                
                groups = []
                groups_node = node.get_child("groups")
                
                if groups_node:
                    for group_node in groups_node.children:
                        if group_node.tag == "group":
                            group_info = {
                                "jid": group_node.get_attribute("id") or "",
                                "subject": group_node.get_attribute("subject") or "",
                                "subject_owner": group_node.get_attribute("s_o") or "",
                                "subject_time": group_node.get_attribute("s_t") or "",
                                "creation": group_node.get_attribute("creation") or "",
                                "creator": group_node.get_attribute("creator") or "",
                                "participants": [],
                                "admins": []
                            }
                            
                            # Extrai participantes se incluídos
                            if include_participants:
                                for child in group_node.children:
                                    if child.tag == "participant":
                                        jid = child.get_attribute("jid")
                                        participant_type = child.get_attribute("type")
                                        if jid:
                                            group_info["participants"].append(jid)
                                            if participant_type == "admin":
                                                group_info["admins"].append(jid)
                            
                            groups.append(group_info)
                
                logger.info(f"Listagem de grupos obtida: {len(groups)} grupos")
                future.set_result(groups)
            
            except Exception as e:
                future.set_exception(e)
        
        self._iq_processor.register_callback(iq_id, on_response, timeout=30.0)
        await self._send_iq(iq_node)
        
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._iq_processor.unregister_callback(iq_id)
            raise Exception("Timeout aguardando listagem de grupos")
    
    async def add_participants(
        self,
        group_jid: str,
        participants: List[str]
    ) -> Dict[str, Any]:
        """
        Adiciona participantes ao grupo.
        
        Args:
            group_jid: JID do grupo
            participants: Lista de JIDs dos participantes a adicionar
        
        Returns:
            Dict com resultado (success_jids, failed_jids)
        
        Raises:
            Exception: Se adição falhar
        """
        logger.info(f"Adicionando participantes ao grupo {group_jid}: {len(participants)} participantes")
        
        iq_node = GroupBuilder.build_add_participants(group_jid, participants)
        iq_id = iq_node.get_attribute("id")
        
        future = asyncio.Future()
        
        async def on_response(node: ProtocolNode):
            """Processa resposta de adição de participantes"""
            try:
                if node.get_attribute("type") != "result":
                    future.set_exception(Exception(f"Erro ao adicionar participantes: tipo={node.get_attribute('type')}"))
                    return
                
                result = {
                    "success_jids": [],
                    "failed_jids": []
                }
                
                # Procura node <add> com resultados
                add_node = node.get_child("add")
                if add_node:
                    for child in add_node.children:
                        if child.tag == "participant":
                            jid = child.get_attribute("jid")
                            error = child.get_attribute("error")
                            if error:
                                result["failed_jids"].append(jid)
                            else:
                                result["success_jids"].append(jid)
                
                logger.info(f"Participantes adicionados: success={len(result['success_jids'])}, failed={len(result['failed_jids'])}")
                future.set_result(result)
            
            except Exception as e:
                future.set_exception(e)
        
        self._iq_processor.register_callback(iq_id, on_response, timeout=30.0)
        await self._send_iq(iq_node)
        
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._iq_processor.unregister_callback(iq_id)
            raise Exception("Timeout aguardando adição de participantes")
    
    async def remove_participants(
        self,
        group_jid: str,
        participants: List[str]
    ) -> Dict[str, Any]:
        """
        Remove participantes do grupo.
        
        Args:
            group_jid: JID do grupo
            participants: Lista de JIDs dos participantes a remover
        
        Returns:
            Dict com resultado (success_jids, failed_jids)
        """
        logger.info(f"Removendo participantes do grupo {group_jid}: {len(participants)} participantes")
        
        iq_node = GroupBuilder.build_remove_participants(group_jid, participants)
        iq_id = iq_node.get_attribute("id")
        
        future = asyncio.Future()
        
        async def on_response(node: ProtocolNode):
            """Processa resposta de remoção de participantes"""
            try:
                if node.get_attribute("type") != "result":
                    future.set_exception(Exception(f"Erro ao remover participantes: tipo={node.get_attribute('type')}"))
                    return
                
                result = {
                    "success_jids": participants.copy(),  # Assume sucesso se não houver erro
                    "failed_jids": []
                }
                
                # Verifica se há erros
                remove_node = node.get_child("remove")
                if remove_node:
                    for child in remove_node.children:
                        if child.tag == "participant":
                            jid = child.get_attribute("jid")
                            error = child.get_attribute("error")
                            if error:
                                if jid in result["success_jids"]:
                                    result["success_jids"].remove(jid)
                                result["failed_jids"].append(jid)
                
                logger.info(f"Participantes removidos: success={len(result['success_jids'])}, failed={len(result['failed_jids'])}")
                future.set_result(result)
            
            except Exception as e:
                future.set_exception(e)
        
        self._iq_processor.register_callback(iq_id, on_response, timeout=30.0)
        await self._send_iq(iq_node)
        
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._iq_processor.unregister_callback(iq_id)
            raise Exception("Timeout aguardando remoção de participantes")
    
    async def promote_participants(
        self,
        group_jid: str,
        participants: List[str]
    ) -> bool:
        """
        Promove participantes a admin.
        
        Args:
            group_jid: JID do grupo
            participants: Lista de JIDs dos participantes a promover
        
        Returns:
            True se sucesso
        """
        logger.info(f"Promovendo participantes do grupo {group_jid}: {len(participants)} participantes")
        
        iq_node = GroupBuilder.build_promote_participants(group_jid, participants)
        iq_id = iq_node.get_attribute("id")
        
        future = asyncio.Future()
        
        async def on_response(node: ProtocolNode):
            """Processa resposta de promoção"""
            try:
                if node.get_attribute("type") != "result":
                    future.set_exception(Exception(f"Erro ao promover participantes: tipo={node.get_attribute('type')}"))
                    return
                
                logger.info("Participantes promovidos com sucesso")
                future.set_result(True)
            
            except Exception as e:
                future.set_exception(e)
        
        self._iq_processor.register_callback(iq_id, on_response, timeout=30.0)
        await self._send_iq(iq_node)
        
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._iq_processor.unregister_callback(iq_id)
            raise Exception("Timeout aguardando promoção de participantes")
    
    async def demote_participants(
        self,
        group_jid: str,
        participants: List[str]
    ) -> bool:
        """
        Rebaixa participantes de admin.
        
        Args:
            group_jid: JID do grupo
            participants: Lista de JIDs dos participantes a rebaixar
        
        Returns:
            True se sucesso
        """
        logger.info(f"Rebaixando participantes do grupo {group_jid}: {len(participants)} participantes")
        
        iq_node = GroupBuilder.build_demote_participants(group_jid, participants)
        iq_id = iq_node.get_attribute("id")
        
        future = asyncio.Future()
        
        async def on_response(node: ProtocolNode):
            """Processa resposta de rebaixamento"""
            try:
                if node.get_attribute("type") != "result":
                    future.set_exception(Exception(f"Erro ao rebaixar participantes: tipo={node.get_attribute('type')}"))
                    return
                
                logger.info("Participantes rebaixados com sucesso")
                future.set_result(True)
            
            except Exception as e:
                future.set_exception(e)
        
        self._iq_processor.register_callback(iq_id, on_response, timeout=30.0)
        await self._send_iq(iq_node)
        
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._iq_processor.unregister_callback(iq_id)
            raise Exception("Timeout aguardando rebaixamento de participantes")
    
    async def leave_group(self, group_jid: str) -> bool:
        """
        Sai do grupo.
        
        Args:
            group_jid: JID do grupo
        
        Returns:
            True se sucesso
        """
        logger.info(f"Saindo do grupo: {group_jid}")
        
        iq_node = GroupBuilder.build_leave_group([group_jid])
        iq_id = iq_node.get_attribute("id")
        
        future = asyncio.Future()
        
        async def on_response(node: ProtocolNode):
            """Processa resposta de saída"""
            try:
                if node.get_attribute("type") != "result":
                    future.set_exception(Exception(f"Erro ao sair do grupo: tipo={node.get_attribute('type')}"))
                    return
                
                logger.info("Saiu do grupo com sucesso")
                future.set_result(True)
            
            except Exception as e:
                future.set_exception(e)
        
        self._iq_processor.register_callback(iq_id, on_response, timeout=30.0)
        await self._send_iq(iq_node)
        
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._iq_processor.unregister_callback(iq_id)
            raise Exception("Timeout aguardando saída do grupo")
    
    async def set_subject(self, group_jid: str, subject: str) -> bool:
        """
        Define assunto do grupo.
        
        Args:
            group_jid: JID do grupo
            subject: Novo assunto
        
        Returns:
            True se sucesso
        """
        logger.info(f"Definindo assunto do grupo {group_jid}: {subject[:50]}")
        
        iq_node = GroupBuilder.build_set_subject(group_jid, subject)
        iq_id = iq_node.get_attribute("id")
        
        future = asyncio.Future()
        
        async def on_response(node: ProtocolNode):
            """Processa resposta de definição de assunto"""
            try:
                if node.get_attribute("type") != "result":
                    future.set_exception(Exception(f"Erro ao definir assunto: tipo={node.get_attribute('type')}"))
                    return
                
                logger.info("Assunto definido com sucesso")
                future.set_result(True)
            
            except Exception as e:
                future.set_exception(e)
        
        self._iq_processor.register_callback(iq_id, on_response, timeout=30.0)
        await self._send_iq(iq_node)
        
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._iq_processor.unregister_callback(iq_id)
            raise Exception("Timeout aguardando definição de assunto")
    
    async def set_description(
        self,
        group_jid: str,
        description: str,
        new_id: Optional[str] = None,
        previous_id: Optional[str] = None
    ) -> bool:
        """
        Define descrição do grupo.
        
        Args:
            group_jid: JID do grupo
            description: Nova descrição
            new_id: ID da nova descrição (opcional)
            previous_id: ID da descrição anterior (opcional)
        
        Returns:
            True se sucesso
        """
        logger.info(f"Definindo descrição do grupo {group_jid}")
        
        iq_node = GroupBuilder.build_set_description(
            group_jid,
            description,
            new_id=new_id,
            previous_id=previous_id
        )
        iq_id = iq_node.get_attribute("id")
        
        future = asyncio.Future()
        
        async def on_response(node: ProtocolNode):
            """Processa resposta de definição de descrição"""
            try:
                if node.get_attribute("type") != "result":
                    future.set_exception(Exception(f"Erro ao definir descrição: tipo={node.get_attribute('type')}"))
                    return
                
                logger.info("Descrição definida com sucesso")
                future.set_result(True)
            
            except Exception as e:
                future.set_exception(e)
        
        self._iq_processor.register_callback(iq_id, on_response, timeout=30.0)
        await self._send_iq(iq_node)
        
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._iq_processor.unregister_callback(iq_id)
            raise Exception("Timeout aguardando definição de descrição")
    
    async def get_invite_code(self, group_jid: str) -> str:
        """
        Obtém código de convite do grupo.
        
        Args:
            group_jid: JID do grupo
        
        Returns:
            Código de convite
        
        Raises:
            Exception: Se obtenção falhar
        """
        logger.info(f"Obtendo código de convite do grupo: {group_jid}")
        
        iq_node = GroupBuilder.build_get_invite_code(group_jid)
        iq_id = iq_node.get_attribute("id")
        
        future = asyncio.Future()
        
        async def on_response(node: ProtocolNode):
            """Processa resposta de código de convite"""
            try:
                if node.get_attribute("type") != "result":
                    future.set_exception(Exception(f"Erro ao obter código: tipo={node.get_attribute('type')}"))
                    return
                
                # Procura node <invite> com código
                invite_node = node.get_child("invite")
                if invite_node:
                    code = invite_node.get_attribute("code")
                    if code:
                        logger.info(f"Código de convite obtido: {code}")
                        future.set_result(code)
                        return
                
                future.set_exception(Exception("Resposta sem código de convite"))
            
            except Exception as e:
                future.set_exception(e)
        
        self._iq_processor.register_callback(iq_id, on_response, timeout=30.0)
        await self._send_iq(iq_node)
        
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._iq_processor.unregister_callback(iq_id)
            raise Exception("Timeout aguardando código de convite")
    
    async def join_with_code(self, code: str) -> str:
        """
        Entra em grupo com código de convite.
        
        Args:
            code: Código de convite
        
        Returns:
            JID do grupo
        
        Raises:
            Exception: Se entrada falhar
        """
        logger.info(f"Entrando em grupo com código: {code}")
        
        iq_node = GroupBuilder.build_join_with_code(code)
        iq_id = iq_node.get_attribute("id")
        
        future = asyncio.Future()
        
        async def on_response(node: ProtocolNode):
            """Processa resposta de entrada com código"""
            try:
                if node.get_attribute("type") != "result":
                    future.set_exception(Exception(f"Erro ao entrar no grupo: tipo={node.get_attribute('type')}"))
                    return
                
                # Procura node <group> com jid
                group_node = node.get_child("group")
                if group_node:
                    group_jid = group_node.get_attribute("jid")
                    if group_jid:
                        logger.info(f"Entrou no grupo com sucesso: {group_jid}")
                        future.set_result(group_jid)
                        return
                
                # Tenta obter do atributo "from"
                from_jid = node.get_attribute("from")
                if from_jid and from_jid.endswith("@g.us"):
                    logger.info(f"Entrou no grupo com sucesso: {from_jid}")
                    future.set_result(from_jid)
                    return
                
                future.set_exception(Exception("Resposta de entrada sem JID do grupo"))
            
            except Exception as e:
                future.set_exception(e)
        
        self._iq_processor.register_callback(iq_id, on_response, timeout=30.0)
        await self._send_iq(iq_node)
        
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._iq_processor.unregister_callback(iq_id)
            raise Exception("Timeout aguardando entrada no grupo")
    
    async def approve_participants(
        self,
        group_jid: str,
        participants: List[str],
        action: str = "approve"  # "approve" ou "reject"
    ) -> bool:
        """
        Aprova ou rejeita participantes pendentes.
        
        Args:
            group_jid: JID do grupo
            participants: Lista de JIDs dos participantes
            action: Ação ("approve" ou "reject")
        
        Returns:
            True se sucesso
        """
        logger.info(f"{action.capitalize()} participantes do grupo {group_jid}: {len(participants)} participantes")
        
        iq_node = GroupBuilder.build_approve_participants(group_jid, participants, action)
        iq_id = iq_node.get_attribute("id")
        
        future = asyncio.Future()
        
        async def on_response(node: ProtocolNode):
            """Processa resposta de aprovação/rejeição"""
            try:
                if node.get_attribute("type") != "result":
                    future.set_exception(Exception(f"Erro ao {action} participantes: tipo={node.get_attribute('type')}"))
                    return
                
                logger.info(f"Participantes {action} com sucesso")
                future.set_result(True)
            
            except Exception as e:
                future.set_exception(e)
        
        self._iq_processor.register_callback(iq_id, on_response, timeout=30.0)
        await self._send_iq(iq_node)
        
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._iq_processor.unregister_callback(iq_id)
            raise Exception(f"Timeout aguardando {action} de participantes")
    
    async def set_settings(
        self,
        group_jid: str,
        setting: str,
        value: Optional[str] = None
    ) -> bool:
        """
        Define configurações do grupo.
        
        Settings disponíveis:
        - "announcement" / "not_announcement": Apenas admins podem enviar mensagens
        - "locked" / "unlocked": Grupo bloqueado/desbloqueado
        - "member_add_mode": Modo de adicionar membros ("all" ou "admin")
        - "membership_approval_mode": Modo de aprovação de membros
        
        Args:
            group_jid: JID do grupo
            setting: Nome da configuração
            value: Valor da configuração (opcional)
        
        Returns:
            True se sucesso
        """
        logger.info(f"Definindo configuração do grupo {group_jid}: {setting}={value}")
        
        iq_node = GroupBuilder.build_set_settings(group_jid, setting, value)
        iq_id = iq_node.get_attribute("id")
        
        future = asyncio.Future()
        
        async def on_response(node: ProtocolNode):
            """Processa resposta de definição de configuração"""
            try:
                if node.get_attribute("type") != "result":
                    future.set_exception(Exception(f"Erro ao definir configuração: tipo={node.get_attribute('type')}"))
                    return
                
                logger.info("Configuração definida com sucesso")
                future.set_result(True)
            
            except Exception as e:
                future.set_exception(e)
        
        self._iq_processor.register_callback(iq_id, on_response, timeout=30.0)
        await self._send_iq(iq_node)
        
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._iq_processor.unregister_callback(iq_id)
            raise Exception("Timeout aguardando definição de configuração")

