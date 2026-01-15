"""
Group Builder - Constrói IQs para operações de grupo.

Baseado nos protocol entities do zowsuplib, mas totalmente assíncrono e moderno.
"""

import uuid
from typing import List, Optional
from loguru import logger

from ...protocol.structs import ProtocolNode
from .iq_builder import IQBuilder


class GroupBuilder:
    """
    Constrói IQs para operações de grupo.
    
    Baseado nos protocol entities do zowsuplib:
    - CreateGroupsIqProtocolEntity
    - AddParticipantsIqProtocolEntity
    - RemoveParticipantsIqProtocolEntity
    - PromoteParticipantsIqProtocolEntity
    - DemoteParticipantsIqProtocolEntity
    - LeaveGroupsIqProtocolEntity
    - SubjectGroupsIqProtocolEntity
    - DescriptionGroupsIqProtocolEntity
    - GetInviteCodeGroupsIqProtocolEntity
    - JoinWithCodeGroupsIqProtocolEntity
    - InfoGroupsIqProtocolEntity
    - ListGroupsIqProtocolEntity
    - ApproveParticipantsGroupsIqProtocolEntity
    - SetGroupsIqProtocolEntity
    """
    
    # Constantes
    WHATSAPP_GROUP_SERVER = "g.us"
    XMLNS_GROUPS = "w:g2"
    
    @staticmethod
    def build_create_group(
        subject: str,
        participants: List[str],
        creator: Optional[str] = None,
        iq_id: Optional[str] = None
    ) -> ProtocolNode:
        """
        Constrói IQ para criar grupo.
        
        Baseado em CreateGroupsIqProtocolEntity.
        
        Args:
            subject: Assunto do grupo
            participants: Lista de JIDs dos participantes
            creator: JID do criador (opcional)
            iq_id: ID do IQ (gerado se None)
        
        Returns:
            ProtocolNode: Node IQ para criar grupo
        """
        if not iq_id:
            iq_id = IQBuilder.generate_iq_id()
        
        # Limpa creator se tiver @
        if creator and '@' in creator:
            creator = creator.split('@')[0]
        
        # Cria key único para o grupo
        key = f"{creator or 'unknown'}-{uuid.uuid4().hex}@temp"
        
        # Cria node base
        node = IQBuilder.build_base_iq(
            xmlns=GroupBuilder.XMLNS_GROUPS,
            iq_type="set",
            iq_id=iq_id,
            to=GroupBuilder.WHATSAPP_GROUP_SERVER
        )
        
        # Cria node <create>
        create_node = ProtocolNode(
            tag="create",
            attributes={
                "subject": subject,
                "key": key
            },
            children=[]
        )
        
        # Adiciona participantes
        participant_nodes = [
            ProtocolNode(
                tag="participant",
                attributes={"jid": participant},
                children=[]
            )
            for participant in participants
        ]
        
        create_node.children.extend(participant_nodes)
        node.children.append(create_node)
        
        logger.debug(f"Group create IQ construído: subject={subject}, participants={len(participants)}")
        return node
    
    @staticmethod
    def build_add_participants(
        group_jid: str,
        participants: List[str],
        iq_id: Optional[str] = None
    ) -> ProtocolNode:
        """
        Constrói IQ para adicionar participantes.
        
        Baseado em AddParticipantsIqProtocolEntity.
        
        Args:
            group_jid: JID do grupo
            participants: Lista de JIDs dos participantes a adicionar
            iq_id: ID do IQ (gerado se None)
        
        Returns:
            ProtocolNode: Node IQ para adicionar participantes
        """
        return GroupBuilder._build_participants_operation(
            group_jid=group_jid,
            participants=participants,
            operation="add",
            iq_id=iq_id
        )
    
    @staticmethod
    def build_remove_participants(
        group_jid: str,
        participants: List[str],
        iq_id: Optional[str] = None
    ) -> ProtocolNode:
        """
        Constrói IQ para remover participantes.
        
        Baseado em RemoveParticipantsIqProtocolEntity.
        """
        return GroupBuilder._build_participants_operation(
            group_jid=group_jid,
            participants=participants,
            operation="remove",
            iq_id=iq_id
        )
    
    @staticmethod
    def build_promote_participants(
        group_jid: str,
        participants: List[str],
        iq_id: Optional[str] = None
    ) -> ProtocolNode:
        """
        Constrói IQ para promover participantes a admin.
        
        Baseado em PromoteParticipantsIqProtocolEntity.
        """
        return GroupBuilder._build_participants_operation(
            group_jid=group_jid,
            participants=participants,
            operation="promote",
            iq_id=iq_id
        )
    
    @staticmethod
    def build_demote_participants(
        group_jid: str,
        participants: List[str],
        iq_id: Optional[str] = None
    ) -> ProtocolNode:
        """
        Constrói IQ para rebaixar participantes de admin.
        
        Baseado em DemoteParticipantsIqProtocolEntity.
        """
        return GroupBuilder._build_participants_operation(
            group_jid=group_jid,
            participants=participants,
            operation="demote",
            iq_id=iq_id
        )
    
    @staticmethod
    def _build_participants_operation(
        group_jid: str,
        participants: List[str],
        operation: str,
        iq_id: Optional[str] = None
    ) -> ProtocolNode:
        """
        Constrói IQ para operações de participantes (add, remove, promote, demote).
        
        Args:
            group_jid: JID do grupo
            participants: Lista de JIDs
            operation: Operação (add, remove, promote, demote)
            iq_id: ID do IQ (gerado se None)
        
        Returns:
            ProtocolNode: Node IQ
        """
        if not iq_id:
            iq_id = IQBuilder.generate_iq_id()
        
        node = IQBuilder.build_base_iq(
            xmlns=GroupBuilder.XMLNS_GROUPS,
            iq_type="set",
            iq_id=iq_id,
            to=group_jid
        )
        
        # Cria node da operação (add, remove, promote, demote)
        participant_nodes = [
            ProtocolNode(
                tag="participant",
                attributes={"jid": participant},
                children=[]
            )
            for participant in participants
        ]
        
        op_node = ProtocolNode(
            tag=operation,
            attributes={},
            children=participant_nodes
        )
        
        node.children.append(op_node)
        logger.debug(f"Group {operation} IQ construído: group={group_jid}, participants={len(participants)}")
        return node
    
    @staticmethod
    def build_leave_group(
        group_jids: List[str],
        iq_id: Optional[str] = None
    ) -> ProtocolNode:
        """
        Constrói IQ para sair de grupo(s).
        
        Baseado em LeaveGroupsIqProtocolEntity.
        
        Args:
            group_jids: Lista de JIDs dos grupos
            iq_id: ID do IQ (gerado se None)
        
        Returns:
            ProtocolNode: Node IQ para sair de grupos
        """
        if not iq_id:
            iq_id = IQBuilder.generate_iq_id()
        
        # Para múltiplos grupos, envia para cada um
        # Por enquanto, suporta apenas um grupo
        if len(group_jids) > 1:
            logger.warning(f"Múltiplos grupos para leave, usando apenas o primeiro: {group_jids[0]}")
        
        group_jid = group_jids[0]
        
        node = IQBuilder.build_base_iq(
            xmlns=GroupBuilder.XMLNS_GROUPS,
            iq_type="set",
            iq_id=iq_id,
            to=group_jid
        )
        
        # Adiciona node <leave>
        leave_node = ProtocolNode(
            tag="leave",
            attributes={},
            children=[]
        )
        
        node.children.append(leave_node)
        logger.debug(f"Group leave IQ construído: group={group_jid}")
        return node
    
    @staticmethod
    def build_set_subject(
        group_jid: str,
        subject: str,
        iq_id: Optional[str] = None
    ) -> ProtocolNode:
        """
        Constrói IQ para definir assunto do grupo.
        
        Baseado em SubjectGroupsIqProtocolEntity.
        
        Args:
            group_jid: JID do grupo
            subject: Novo assunto
            iq_id: ID do IQ (gerado se None)
        
        Returns:
            ProtocolNode: Node IQ para definir assunto
        """
        if not iq_id:
            iq_id = IQBuilder.generate_iq_id()
        
        node = IQBuilder.build_base_iq(
            xmlns=GroupBuilder.XMLNS_GROUPS,
            iq_type="set",
            iq_id=iq_id,
            to=group_jid
        )
        
        # Cria node <subject> com dados
        subject_data = subject.encode("utf-8") if isinstance(subject, str) else subject
        subject_node = ProtocolNode(
            tag="subject",
            attributes={},
            data=subject_data
        )
        
        node.children.append(subject_node)
        logger.debug(f"Group set subject IQ construído: group={group_jid}, subject={subject[:50]}")
        return node
    
    @staticmethod
    def build_set_description(
        group_jid: str,
        description: str,
        new_id: Optional[str] = None,
        previous_id: Optional[str] = None,
        iq_id: Optional[str] = None
    ) -> ProtocolNode:
        """
        Constrói IQ para definir descrição do grupo.
        
        Baseado em DescriptionGroupsIqProtocolEntity.
        
        Args:
            group_jid: JID do grupo
            description: Nova descrição
            new_id: ID da nova descrição (opcional)
            previous_id: ID da descrição anterior (opcional)
            iq_id: ID do IQ (gerado se None)
        
        Returns:
            ProtocolNode: Node IQ para definir descrição
        """
        if not iq_id:
            iq_id = IQBuilder.generate_iq_id()
        
        node = IQBuilder.build_base_iq(
            xmlns=GroupBuilder.XMLNS_GROUPS,
            iq_type="set",
            iq_id=iq_id,
            to=group_jid
        )
        
        # Atributos do node description
        attrs = {}
        if new_id:
            attrs["id"] = new_id
        if previous_id:
            attrs["prev"] = previous_id
        
        # Se descrição vazia, marca para deletar
        is_delete = not description or len(description.strip()) == 0
        if is_delete:
            attrs["delete"] = "true"
        
        # Conteúdo
        children = []
        if not is_delete:
            description_data = description.encode("utf-8") if isinstance(description, str) else description
            body_node = ProtocolNode(
                tag="body",
                attributes={},
                data=description_data
            )
            children.append(body_node)
        
        description_node = ProtocolNode(
            tag="description",
            attributes=attrs,
            children=children
        )
        
        node.children.append(description_node)
        logger.debug(f"Group set description IQ construído: group={group_jid}, delete={is_delete}")
        return node
    
    @staticmethod
    def build_get_invite_code(
        group_jid: str,
        iq_id: Optional[str] = None
    ) -> ProtocolNode:
        """
        Constrói IQ para obter código de convite do grupo.
        
        Baseado em GetInviteCodeGroupsIqProtocolEntity.
        
        Args:
            group_jid: JID do grupo
            iq_id: ID do IQ (gerado se None)
        
        Returns:
            ProtocolNode: Node IQ para obter código de convite
        """
        if not iq_id:
            iq_id = IQBuilder.generate_iq_id()
        
        node = IQBuilder.build_base_iq(
            xmlns=GroupBuilder.XMLNS_GROUPS,
            iq_type="get",
            iq_id=iq_id,
            to=group_jid
        )
        
        # Adiciona node <invite>
        invite_node = ProtocolNode(
            tag="invite",
            attributes={},
            children=[]
        )
        
        node.children.append(invite_node)
        logger.debug(f"Group get invite code IQ construído: group={group_jid}")
        return node
    
    @staticmethod
    def build_join_with_code(
        code: str,
        iq_id: Optional[str] = None
    ) -> ProtocolNode:
        """
        Constrói IQ para entrar em grupo com código de convite.
        
        Baseado em JoinWithCodeGroupsIqProtocolEntity.
        
        Args:
            code: Código de convite
            iq_id: ID do IQ (gerado se None)
        
        Returns:
            ProtocolNode: Node IQ para entrar com código
        """
        if not iq_id:
            iq_id = IQBuilder.generate_iq_id()
        
        node = IQBuilder.build_base_iq(
            xmlns=GroupBuilder.XMLNS_GROUPS,
            iq_type="set",
            iq_id=iq_id,
            to=GroupBuilder.WHATSAPP_GROUP_SERVER
        )
        
        # Adiciona node <invite> com código
        invite_node = ProtocolNode(
            tag="invite",
            attributes={"code": code},
            children=[]
        )
        
        node.children.append(invite_node)
        logger.debug(f"Group join with code IQ construído: code={code}")
        return node
    
    @staticmethod
    def build_get_info(
        group_jid: str,
        iq_id: Optional[str] = None
    ) -> ProtocolNode:
        """
        Constrói IQ para obter informações do grupo.
        
        Baseado em InfoGroupsIqProtocolEntity.
        
        Args:
            group_jid: JID do grupo
            iq_id: ID do IQ (gerado se None)
        
        Returns:
            ProtocolNode: Node IQ para obter informações
        """
        if not iq_id:
            iq_id = IQBuilder.generate_iq_id()
        
        node = IQBuilder.build_base_iq(
            xmlns=GroupBuilder.XMLNS_GROUPS,
            iq_type="get",
            iq_id=iq_id,
            to=group_jid
        )
        
        # Adiciona node <group> vazio (servidor retorna informações)
        group_node = ProtocolNode(
            tag="group",
            attributes={},
            children=[]
        )
        
        node.children.append(group_node)
        logger.debug(f"Group get info IQ construído: group={group_jid}")
        return node
    
    @staticmethod
    def build_list_groups(
        include_participants: bool = True,
        iq_id: Optional[str] = None
    ) -> ProtocolNode:
        """
        Constrói IQ para listar grupos.
        
        Baseado em ListGroupsIqProtocolEntity.
        
        Args:
            include_participants: Se deve incluir lista de participantes
            iq_id: ID do IQ (gerado se None)
        
        Returns:
            ProtocolNode: Node IQ para listar grupos
        """
        if not iq_id:
            iq_id = IQBuilder.generate_iq_id()
        
        node = IQBuilder.build_base_iq(
            xmlns=GroupBuilder.XMLNS_GROUPS,
            iq_type="get",
            iq_id=iq_id,
            to=GroupBuilder.WHATSAPP_GROUP_SERVER
        )
        
        # Adiciona node <participating>
        participating_node = ProtocolNode(
            tag="participating",
            attributes={},
            children=[]
        )
        
        if include_participants:
            participants_node = ProtocolNode(
                tag="participants",
                attributes={},
                children=[]
            )
            participating_node.children.append(participants_node)
        
        description_node = ProtocolNode(
            tag="description",
            attributes={},
            children=[]
        )
        participating_node.children.append(description_node)
        
        node.children.append(participating_node)
        logger.debug(f"Group list IQ construído: include_participants={include_participants}")
        return node
    
    @staticmethod
    def build_approve_participants(
        group_jid: str,
        participants: List[str],
        action: str = "approve",  # "approve" ou "reject"
        iq_id: Optional[str] = None
    ) -> ProtocolNode:
        """
        Constrói IQ para aprovar/rejeitar participantes.
        
        Baseado em ApproveParticipantsGroupsIqProtocolEntity.
        
        Args:
            group_jid: JID do grupo
            participants: Lista de JIDs dos participantes
            action: Ação ("approve" ou "reject")
            iq_id: ID do IQ (gerado se None)
        
        Returns:
            ProtocolNode: Node IQ para aprovar/rejeitar participantes
        """
        if not iq_id:
            iq_id = IQBuilder.generate_iq_id()
        
        node = IQBuilder.build_base_iq(
            xmlns=GroupBuilder.XMLNS_GROUPS,
            iq_type="set",
            iq_id=iq_id,
            to=group_jid
        )
        
        # Cria estrutura: <membership_requests_action><approve/reject><participant>...</participant></approve/reject></membership_requests_action>
        participant_nodes = [
            ProtocolNode(
                tag="participant",
                attributes={"jid": participant},
                children=[]
            )
            for participant in participants
        ]
        
        action_node = ProtocolNode(
            tag=action,
            attributes={},
            children=participant_nodes
        )
        
        membership_node = ProtocolNode(
            tag="membership_requests_action",
            attributes={},
            children=[action_node]
        )
        
        node.children.append(membership_node)
        logger.debug(f"Group approve/reject IQ construído: group={group_jid}, action={action}, participants={len(participants)}")
        return node
    
    @staticmethod
    def build_set_settings(
        group_jid: str,
        setting: str,
        value: Optional[str] = None,
        iq_id: Optional[str] = None
    ) -> ProtocolNode:
        """
        Constrói IQ para definir configurações do grupo.
        
        Baseado em SetGroupsIqProtocolEntity.
        
        Settings disponíveis:
        - "announcement" / "not_announcement": Apenas admins podem enviar mensagens
        - "locked" / "unlocked": Grupo bloqueado/desbloqueado
        - "member_add_mode": Modo de adicionar membros ("all" ou "admin")
        - "membership_approval_mode": Modo de aprovação de membros
        
        Args:
            group_jid: JID do grupo
            setting: Nome da configuração
            value: Valor da configuração (opcional, para member_add_mode e membership_approval_mode)
            iq_id: ID do IQ (gerado se None)
        
        Returns:
            ProtocolNode: Node IQ para definir configurações
        """
        if not iq_id:
            iq_id = IQBuilder.generate_iq_id()
        
        node = IQBuilder.build_base_iq(
            xmlns=GroupBuilder.XMLNS_GROUPS,
            iq_type="set",
            iq_id=iq_id,
            to=group_jid
        )
        
        # Cria node da configuração
        if value is None:
            # Configuração simples (announcement, locked, etc.)
            setting_node = ProtocolNode(
                tag=setting,
                attributes={},
                children=[]
            )
            node.children.append(setting_node)
        
        elif setting == "member_add_mode":
            # Modo de adicionar membros
            setting_data = value.encode("utf-8") if isinstance(value, str) else value
            setting_node = ProtocolNode(
                tag=setting,
                attributes={},
                data=setting_data
            )
            node.children.append(setting_node)
        
        elif setting == "membership_approval_mode":
            # Modo de aprovação de membros
            group_join_node = ProtocolNode(
                tag="group_join",
                attributes={"state": value},
                children=[]
            )
            setting_node = ProtocolNode(
                tag=setting,
                attributes={},
                children=[group_join_node]
            )
            node.children.append(setting_node)
        
        logger.debug(f"Group set settings IQ construído: group={group_jid}, setting={setting}, value={value}")
        return node

