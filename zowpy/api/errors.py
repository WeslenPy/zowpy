"""
ZowPy Errors - Exceções da API pública.
"""


class ZowPyError(Exception):
    """Erro base do ZowPy"""
    pass


class ConnectionError(ZowPyError):
    """Erro de conexão"""
    pass


class AuthenticationError(ZowPyError):
    """Erro de autenticação"""
    pass


class MessageError(ZowPyError):
    """Erro ao enviar/receber mensagem"""
    pass












