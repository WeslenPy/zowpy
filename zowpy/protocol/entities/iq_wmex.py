"""
WMEX IQ Protocol Entities - Entidades para WMEX queries/results.

Baseado em WmexQueryIqProtocolEntity e WmexResultIqProtocolEntity do zowsuplib.
"""

import json
import base64
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger

from .iq import IqProtocolEntity
from ...utils.constants import YowConstants
from ...protocol.structs import ProtocolNode

# Try to import ArgoMessageDecoder - it may not be available
try:
    from zargo.argo_message_decoder import ArgoMessageDecoder
    ARGO_AVAILABLE = True
except ImportError:
    ARGO_AVAILABLE = False
    logger.warning("ArgoMessageDecoder não disponível. Respostas ARGO não serão decodificadas.")


class BytesEncoder(json.JSONEncoder):
    """JSON encoder para bytes."""
    
    def default(self, obj):
        if isinstance(obj, bytes):
            if len(obj) > 0 and (obj[0] == 250 or obj[0] == 247):
                # JID encoding - try to decode
                try:
                    # For zowpy, we'll just return base64 for now
                    # If zargo is available, we could use Jid.readJid
                    return base64.b64encode(obj).decode('utf-8')
                except Exception:
                    return base64.b64encode(obj).decode('utf-8')
            else:
                return base64.b64encode(obj).decode('utf-8')
        return json.JSONEncoder.default(self, obj)


class WmexQueryIqProtocolEntity(IqProtocolEntity):
    """
    Entidade de IQ para queries WMEX <iq xmlns="w:mex" type="get">.
    
    Baseado em WmexQueryIqProtocolEntity do zowsuplib.
    """
    
    _queryIdMap: Optional[Dict[str, str]] = None
    
    def __init__(self, query_name: Optional[str] = None, query_obj: Optional[Dict[str, Any]] = None, iq_id: Optional[str] = None):
        """
        Cria query WMEX.
        
        Args:
            query_name: Nome da query (ex: "BizIntegrityQuery")
            query_obj: Objeto da query (será serializado como JSON)
            iq_id: ID do IQ (gerado se None)
        """
        super().__init__(
            xmlns="w:mex",
            iq_type="get",
            iq_id=iq_id,
            to=YowConstants.DOMAIN
        )
        
        # Carrega dicionário na primeira vez
        if WmexQueryIqProtocolEntity._queryIdMap is None:
            WmexQueryIqProtocolEntity.load_dict()
        
        self.query_obj = query_obj or {}
        self.query_name = query_name
        self.query_id = WmexQueryIqProtocolEntity._queryIdMap.get(query_name) if query_name else None
        
        if query_name and not self.query_id:
            logger.warning(f"Query ID não encontrado para query_name: {query_name}")
    
    @staticmethod
    def load_dict():
        """Carrega argo_dict.json."""
        try:
            # Obtém caminho do arquivo proto/argo_dict.json relativo a este arquivo
            current_dir = Path(__file__).parent.parent.parent  # zowpy/
            dict_path = current_dir / "proto" / "argo_dict.json"
            
            if not dict_path.exists():
                raise FileNotFoundError(
                    f"Arquivo argo_dict.json não encontrado em: {dict_path}"
                )
            
            with open(dict_path, 'r', encoding='utf8') as f:
                WmexQueryIqProtocolEntity._queryIdMap = json.loads(f.read())
            
            logger.debug(f"Argo dict carregado de {dict_path}")
        except Exception as e:
            logger.error(f"Erro ao carregar argo_dict.json: {e}")
            WmexQueryIqProtocolEntity._queryIdMap = {}
    
    def __str__(self):
        out = super().__str__()
        out += f"\nquery_name: {self.query_name}"
        out += f"\nquery_id: {self.query_id}"
        out += f"\nquery_obj: {json.dumps(self.query_obj)}"
        return out
    
    def to_protocol_node(self) -> ProtocolNode:
        """
        Converte para ProtocolNode.
        
        Returns:
            ProtocolNode equivalente
        """
        node = super().to_protocol_node()
        
        # Registra query_name no idNameMap para processamento da resposta
        if self.iq_id and self.query_name:
            WmexResultIqProtocolEntity.idNameMap[self.iq_id] = self.query_name
        
        # Adiciona query_id ao query_obj
        if self.query_id:
            self.query_obj["queryId"] = self.query_id
        
        # Cria node <query>
        query_node = ProtocolNode(
            tag="query",
            attributes={"query_id": self.query_id} if self.query_id else {},
            data=json.dumps(self.query_obj).encode()
        )
        
        # Cria node <trace><flow_id>
        flow_id_node = ProtocolNode(
            tag="flow_id",
            data=self.query_id.encode() if self.query_id else b""
        )
        trace_node = ProtocolNode(
            tag="trace",
            children=[flow_id_node]
        )
        
        # Adiciona filhos ao node principal
        node.children.append(trace_node)
        node.children.append(query_node)
        
        return node


class WmexResultIqProtocolEntity(IqProtocolEntity):
    """
    Entidade de IQ para resultados WMEX <iq type="result">.
    
    Baseado em WmexResultIqProtocolEntity do zowsuplib.
    """
    
    idNameMap: Dict[str, str] = {}  # Mapeia IQ IDs para query names
    _schema_file_cache: Optional[str] = None
    
    def __init__(self, iq_id: str, result_obj: Optional[Any] = None, result_type: str = "json"):
        """
        Cria resultado WMEX.
        
        Args:
            iq_id: ID do IQ
            result_obj: Objeto de resultado
            result_type: Tipo do resultado ("json" ou "argo")
        """
        super().__init__(
            xmlns="",
            iq_type="result",
            iq_id=iq_id,
            from_jid=YowConstants.DOMAIN
        )
        
        self.result_obj = result_obj
        self.result_type = result_type
    
    def set_result_obj(self, result_obj: Any, result_type: str):
        """Define objeto de resultado."""
        self.result_obj = result_obj
        self.result_type = result_type
    
    def __str__(self):
        out = super().__str__()
        if self.result_type == "json":
            out += f"\nresult_obj: {json.dumps(self.result_obj)}"
        else:
            out += f"\nresult_obj: {str(self.result_obj)}"
        return out
    
    @staticmethod
    def _get_schema_file() -> str:
        """
        Obtém caminho do arquivo schema .argo.
        
        Returns:
            Caminho do arquivo schema
        """
        if WmexResultIqProtocolEntity._schema_file_cache:
            cached_path = Path(WmexResultIqProtocolEntity._schema_file_cache)
            if cached_path.exists():
                return str(cached_path.resolve())
        
        # Obtém caminho do arquivo proto/argo-wire-type-store.argo
        current_dir = Path(__file__).parent.parent.parent  # zowpy/
        schema_file = current_dir / "proto" / "argo-wire-type-store.argo"
        
        if not schema_file.exists():
            raise FileNotFoundError(
                f"Arquivo argo-wire-type-store.argo não encontrado em: {schema_file}"
            )
        
        schema_path = str(schema_file.resolve())
        WmexResultIqProtocolEntity._schema_file_cache = schema_path
        return schema_path
    
    @staticmethod
    def from_protocol_node(node: ProtocolNode) -> Optional['WmexResultIqProtocolEntity']:
        """
        Cria entidade a partir de ProtocolNode.
        
        Args:
            node: Node do protocolo
            
        Returns:
            WmexResultIqProtocolEntity ou None se não for válido
        """
        iq_id = node.get_attribute("id")
        if not iq_id:
            return None
        
        # Cria entidade base
        entity = IqProtocolEntity.from_protocol_node_iq_entity(node)
        entity.__class__ = WmexResultIqProtocolEntity
        
        # Encontra node <result>
        result_node = None
        for child in node.children:
            if child.tag == "result":
                result_node = child
                break
        
        if result_node is None:
            return None
        
        format = result_node.get_attribute("format")
        
        if format == "argo":
            data = result_node.data
            query_name = WmexResultIqProtocolEntity.idNameMap.pop(iq_id, None)
            
            if query_name and ARGO_AVAILABLE and data:
                try:
                    # Decodifica usando ArgoMessageDecoder
                    schema_file = WmexResultIqProtocolEntity._get_schema_file()
                    ArgoMessageDecoder.setSchemaFile(schema_file)
                    obj = ArgoMessageDecoder.decodeMessage(query_name, data)
                    res = json.dumps(obj, cls=BytesEncoder)
                    entity.set_result_obj(json.loads(res), "json")
                except Exception as e:
                    logger.error(f"Erro ao decodificar resposta ARGO: {e}")
                    entity.set_result_obj(data, "argo")
            else:
                if not ARGO_AVAILABLE:
                    logger.warning("ArgoMessageDecoder não disponível. Retornando dados brutos.")
                entity.set_result_obj(data, "argo")
        else:
            # Formato JSON
            if result_node.data:
                try:
                    jsonstr = result_node.data.decode('utf-8')
                    entity.set_result_obj(json.loads(jsonstr), "json")
                except Exception as e:
                    logger.error(f"Erro ao parsear JSON do resultado: {e}")
                    entity.set_result_obj(None, "json")
            else:
                entity.set_result_obj(None, "json")
        
        return entity
