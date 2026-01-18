"""
Network Environment - Configuração de rede.

Portado do projeto original, mantendo compatibilidade.
"""

from typing import Optional, Literal, Dict, Any
from dataclasses import dataclass
from loguru import logger


class NetworkEnv:
    """
    Ambiente de rede.
    Portado do projeto original, mantendo compatibilidade.
    """
    
    TYPE_DIRECT = "direct"
    TYPE_PROXY = "proxy"
    
    def __init__(
        self,
        type: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        proxy_str: Optional[str] = None
    ):
        """
        Inicializa ambiente de rede.
        
        Args:
            type: Tipo de conexão ("direct" ou "proxy")
            host: Host do proxy (se proxy)
            port: Porta do proxy (se proxy)
            username: Usuário do proxy (se proxy)
            password: Senha do proxy (se proxy)
            proxy_str: String de proxy no formato "host:port:username:password"
        """
        self.type = type
        self.raw_proxy_str = None
        self.proxy_str = None
        
        if type == "proxy":
            if proxy_str is None:
                if host and port and username and password:
                    proxy_str = f"{host}:{port}:{username}:{password}"
                else:
                    raise ValueError("Proxy requires host, port, username, and password")
            
            self.update_proxy_str(proxy_str, proxy_str)
    
    def __str__(self) -> str:
        return f"NetworkType={self.type}, Proxy={self.proxy_str}"
    
    def update_proxy_str(self, proxy_str: str, raw_proxy_str: Optional[str] = None) -> None:
        """
        Atualiza string de proxy.
        
        Args:
            proxy_str: String de proxy no formato "host:port:username:password"
            raw_proxy_str: String de proxy original (com placeholders)
        """
        if raw_proxy_str:
            self.raw_proxy_str = raw_proxy_str
        
        self.proxy_str = proxy_str
        params = proxy_str.split(":")
        
        if len(params) == 4:
            self.type = "proxy"
            self.host = params[0]
            self.port = int(params[1])
            self.username = params[2]
            self.password = params[3]
            logger.debug(f"[PROXY] NetworkEnv.updateProxyStr() | Proxy atualizado: {self.host}:{self.port} | Auth: Sim")
        else:
            raise ValueError("Proxy string format error: expected 'host:port:username:password'")
    
    def update_by_wa_num(self, wa_num: str) -> None:
        """
        Atualiza proxy baseado no número WhatsApp.
        
        Args:
            wa_num: Número WhatsApp
        """
        if self.type == "direct":
            return
        
        # Usa utilitários do projeto
        from ..utils.phone import get_mobile_cc, get_lg_lc
        cc = get_mobile_cc(wa_num)
        lg, lc = get_lg_lc(cc)
        
        if lc.lower() == "cn":
            lc = "us"
        
        session_id = wa_num[-8:]
        proxy_str = self.raw_proxy_str or self.proxy_str
        
        if proxy_str and "[location]" in proxy_str:
            proxy_str = proxy_str.replace("[location]", lc.lower())
        if proxy_str and "[session_id]" in proxy_str:
            proxy_str = proxy_str.replace("[session_id]", session_id)
        
        if proxy_str:
            self.update_proxy_str(proxy_str)
    
    def change_ip(self, wa_num: str) -> None:
        """
        Muda IP do proxy baseado no número WhatsApp.
        
        Args:
            wa_num: Número WhatsApp
        """
        import random
        
        from ..utils.phone import get_mobile_cc, get_lg_lc
        cc = get_mobile_cc(wa_num)
        lg, lc = get_lg_lc(cc)
        
        if lc.lower() == "cn":
            lc = "us"
        
        alp = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        session_id = ''.join(random.sample(alp, 8))
        proxy_str = self.raw_proxy_str or self.proxy_str
        
        if proxy_str and "[location]" in proxy_str:
            proxy_str = proxy_str.replace("[location]", lc.lower())
        if proxy_str and "[session_id]" in proxy_str:
            proxy_str = proxy_str.replace("[session_id]", session_id)
        
        if proxy_str:
            self.update_proxy_str(proxy_str)
    
    def get_proxy_url(self) -> Optional[str]:
        """
        Obtém URL de proxy para uso com websockets.
        
        Returns:
            URL de proxy ou None se direto
        """
        if self.type == "direct":
            return None
        
        if hasattr(self, 'host') and hasattr(self, 'port'):
            if hasattr(self, 'username') and hasattr(self, 'password'):
                return f"http://{self.username}:{self.password}@{self.host}:{self.port}"
            else:
                return f"http://{self.host}:{self.port}"
        
        return None


@dataclass
class ProxyConfig:
    """
    Configuração moderna de proxy HTTP/SOCKS5.
    
    Representa configuração de proxy de forma type-safe e moderna.
    """
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    proxy_type: Literal["http", "socks5"] = "socks5"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte para dict compatível com AsyncConnection.
        
        Returns:
            Dict com configuração de proxy
        """
        return {
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "type": self.proxy_type,
        }
    
    def to_string(self) -> str:
        """
        Converte para string no formato "host:port[:username:password]".
        
        Returns:
            String de proxy
        """
        proxy_str = f"{self.host}:{self.port}"
        if self.username and self.password:
            proxy_str += f":{self.username}:{self.password}"
        return proxy_str
    
    @classmethod
    def from_string(
        cls,
        proxy_string: str,
        proxy_type: Literal["http", "socks5"] = "socks5"
    ) -> "ProxyConfig":
        """
        Cria ProxyConfig a partir de string.
        
        Formatos aceitos:
        - "host:port" (sem autenticação)
        - "host:port:username:password" (com autenticação)
        
        Args:
            proxy_string: String de proxy
            proxy_type: Tipo de proxy ("http" ou "socks5")
            
        Returns:
            ProxyConfig criado
            
        Raises:
            ValueError: Se formato inválido
        """
        if not proxy_string or proxy_string.strip() == "":
            raise ValueError("Proxy string não pode ser vazia")
        
        parts = proxy_string.strip().split(":")
        
        if len(parts) < 2:
            raise ValueError(
                "Formato de proxy inválido. Use 'host:port' ou 'host:port:username:password'"
            )
        
        host = parts[0]
        
        try:
            port = int(parts[1])
            if not (1 <= port <= 65535):
                raise ValueError(f"Porta inválida: {port}. Deve estar entre 1 e 65535")
        except ValueError as e:
            if "invalid literal" in str(e).lower():
                raise ValueError(f"Porta inválida: {parts[1]}")
            raise
        
        username = None
        password = None
        
        if len(parts) == 4:
            username = parts[2]
            password = parts[3]
        elif len(parts) == 3:
            raise ValueError(
                "Formato de proxy inválido. Se fornecer username, deve fornecer password também"
            )
        elif len(parts) > 4:
            raise ValueError("Formato de proxy inválido. Muitos campos")
        
        return cls(
            host=host,
            port=port,
            username=username,
            password=password,
            proxy_type=proxy_type
        )
    
    def __str__(self) -> str:
        auth_str = " (com auth)" if self.username and self.password else " (sem auth)"
        return f"ProxyConfig({self.proxy_type}://{self.host}:{self.port}{auth_str})"


@dataclass
class NetworkConfig:
    """
    Configuração moderna de rede (direta ou via proxy).
    
    Representa configuração de rede de forma type-safe e moderna.
    """
    type: Literal["direct", "proxy"]
    proxy: Optional[ProxyConfig] = None
    
    @classmethod
    def direct(cls) -> "NetworkConfig":
        """Cria configuração de rede direta."""
        return cls(type="direct", proxy=None)
    
    @classmethod
    def proxy_config(cls, proxy_config: ProxyConfig) -> "NetworkConfig":
        """Cria configuração de rede via proxy."""
        return cls(type="proxy", proxy=proxy_config)
    
    def to_proxy_dict(self) -> Optional[Dict[str, Any]]:
        """
        Converte proxy para dict compatível com AsyncConnection.
        
        Returns:
            Dict de proxy ou None se direto
        """
        if self.type == "direct" or not self.proxy:
            return None
        return self.proxy.to_dict()
    
    def __str__(self) -> str:
        if self.type == "direct":
            return "NetworkConfig(direct)"
        return f"NetworkConfig(proxy={self.proxy})"


