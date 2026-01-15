"""
Consonance Utils - Portado para zowpy.

Porta ByteUtil do consonance.
"""


class ByteUtil:
    """Utilitários para manipulação de bytes."""

    @staticmethod
    def split(
        input_data: bytes, first_len: int, second_len: int, third_len: int | None = None
    ) -> list[bytes]:
        """
        Divide bytes em partes.
        
        Compatível com zowsuplib.consonance.util.byte.ByteUtil.split()

        :param input_data: Dados de entrada
        :type input_data: bytes
        :param first_len: Tamanho da primeira parte
        :type first_len: int
        :param second_len: Tamanho da segunda parte
        :type second_len: int
        :param third_len: Tamanho da terceira parte (opcional). 
                          Se fornecido, pega exatamente third_len bytes.
                          Se None, retorna apenas 2 partes.
        :type third_len: int | None
        :return: Lista de partes
        :rtype: list[bytes]
        """
        parts = []
        parts.append(input_data[:first_len])
        parts.append(input_data[first_len : first_len + second_len])
        if third_len is not None:
            # Se third_len foi fornecido, pega exatamente third_len bytes a partir de first_len + second_len
            # Isso é compatível com o comportamento do zowsuplib
            start_idx = first_len + second_len
            end_idx = start_idx + third_len
            # Garante que não ultrapasse o tamanho dos dados
            if end_idx > len(input_data):
                # Se third_len é maior que o restante, pega apenas o restante
                parts.append(input_data[start_idx:])
            else:
                parts.append(input_data[start_idx:end_idx])
        return parts

