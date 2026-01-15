"""
Byte Utilities - Utilitários para manipulação de bytes.

Substitui zowsuplib.consonance.util.byte.ByteUtil
"""


class ByteUtil:
    """
    Utilitários para manipulação de bytes.
    Substitui zowsuplib.consonance.util.byte.ByteUtil
    """
    
    @staticmethod
    def split(input, first_len, second_len, third_len=None):
        """
        Divide dados em partes de tamanhos especificados.
        
        Args:
            data: Dados para dividir
            *sizes: Tamanhos das partes
        
        Returns:
            Lista com as partes divididas + resto
        """
        parts = []
        parts.append(input[:first_len])
        parts.append(input[first_len:first_len + second_len])
        if third_len is not None:
            parts.append(input[first_len + second_len: first_len + second_len + third_len])
        return parts

