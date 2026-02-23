"""
Phone Utilities - Utilitários para números de telefone.

Fonte de dados: proto/countries.json (estrutura por código de país).
Substitui zowsuplib.common.utils.Utils.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Caminho do JSON em relação ao pacote proto
_COUNTRIES_JSON_PATH = Path(__file__).resolve().parent.parent / "proto" / "countries.json"

# Fallbacks quando o código não está no JSON
_DEFAULT_LOCALE = "us"
_DEFAULT_LANGUAGE = "en"
_DEFAULT_MCC = "000"
_DEFAULT_MNC = "000"


_countries_cache: Optional[Dict[str, Any]] = None


def _load_countries_data() -> Dict[str, Any]:
    """Carrega countries.json uma vez (cache em módulo)."""
    global _countries_cache
    if _countries_cache is None:
        with open(_COUNTRIES_JSON_PATH, "r", encoding="utf-8") as f:
            _countries_cache = json.load(f)
    return _countries_cache


class CountryPhoneData:
    """
    Dados de país/telefone a partir de proto/countries.json.

    Expõe código de país (cc), locale, language, MCC/MNC, nome do país e
    operadoras de forma estruturada via properties e métodos auxiliares.
    """

    __slots__ = ("_cc", "_raw")

    def __init__(self, country_code: str):
        """
        :param country_code: Código de discagem do país (ex: "55", "1").
        """
        self._cc = country_code
        data = _load_countries_data()
        self._raw: Optional[Dict[str, Any]] = data.get(country_code)

    @property
    def country_code(self) -> str:
        """Código de discagem do país (cc)."""
        return self._cc

    @property
    def locale(self) -> str:
        """Código de localização (lc), ex: br, us, gb."""
        if self._raw and "locale" in self._raw and self._raw["locale"]:
            return self._raw["locale"]
        op = self._first_operator
        if op and op.get("iso"):
            return op["iso"]
        return _DEFAULT_LOCALE

    @property
    def language(self) -> str:
        """Código de idioma (lg), ex: pt, en."""
        if self._raw and "language" in self._raw and self._raw["language"]:
            return self._raw["language"]
        return _DEFAULT_LANGUAGE

    @property
    def country_name(self) -> str:
        """Nome do país em inglês."""
        op = self._first_operator
        if op and op.get("country"):
            return op["country"].strip()
        return ""

    @property
    def _first_operator(self) -> Optional[Dict[str, Any]]:
        """Primeiro operador da lista (usado para mcc, mnc, iso, country)."""
        if not self._raw:
            return None
        ddi = self._raw.get("ddi") or {}
        operators = ddi.get("operators") or []
        if not operators:
            return None
        first = operators[0]
        return first.get("operator") if isinstance(first, dict) else None

    @property
    def default_mcc(self) -> str:
        """MCC (Mobile Country Code) padrão para o país."""
        op = self._first_operator
        if op and op.get("mcc"):
            return op["mcc"]
        return _DEFAULT_MCC

    @property
    def default_mnc(self) -> str:
        """MNC (Mobile Network Code) padrão para o país."""
        op = self._first_operator
        if op and op.get("mnc"):
            return op["mnc"]
        return _DEFAULT_MNC

    def get_lg_lc(self) -> Tuple[str, str]:
        """Retorna (language, locale) para uso em registro/API."""
        return self.language, self.locale

    def get_mcc_mnc(self) -> Tuple[str, str]:
        """Retorna (MCC, MNC) padrão para o país."""
        return self.default_mcc, self.default_mnc

    @property
    def operators(self) -> List[Dict[str, Any]]:
        """Lista de operadoras (operator dicts: mcc, mnc, iso, country, network)."""
        if not self._raw:
            return []
        ddi = self._raw.get("ddi") or {}
        operators = ddi.get("operators") or []
        out = []
        for item in operators:
            if isinstance(item, dict) and "operator" in item:
                out.append(item["operator"])
        return out

    @property
    def is_known(self) -> bool:
        """True se o código de país existe no JSON."""
        return self._raw is not None

    def __repr__(self) -> str:
        return f"CountryPhoneData(cc={self._cc!r}, locale={self.locale!r}, language={self.language!r})"


class PhoneCountryHelper:
    """
    Acesso central aos dados de países/telefone a partir de countries.json.

    Uso:
        helper = PhoneCountryHelper()
        cc = helper.get_country_code("+5511999999999")
        data = helper.get_data(cc)
        data.locale, data.language, data.get_mcc_mnc()
    """

    def __init__(self) -> None:
        self._data = _load_countries_data()
        self._cc_set = set(self._data.keys())

    @property
    def country_codes(self) -> List[str]:
        """Lista de códigos de país presentes no JSON (ordenados por tamanho desc para matching)."""
        return sorted(self._cc_set, key=lambda x: (-len(x), x))

    def get_country_code(self, phone_number: str) -> str:
        """
        Obtém o código de país a partir do número (apenas dígitos, matching no JSON).
        Tenta prefixos mais longos primeiro (3, 2, 1 dígito).
        """
        digits = "".join(c for c in phone_number if c.isdigit())
        if not digits:
            return "1"
        # Código 1 (EUA/Canadá): só aceita se tiver pelo menos 10 dígitos
        if digits.startswith("1") and len(digits) >= 10:
            return "1"
        for length in (3, 2, 1):
            if len(digits) >= length:
                code = digits[:length]
                if code in self._cc_set:
                    return code
        return digits[0] if digits else "1"

    def get_data(self, country_code: str) -> CountryPhoneData:
        """Retorna um CountryPhoneData para o código informado."""
        return CountryPhoneData(country_code)

    def get_locale(self, country_code: str) -> str:
        """Atalho para locale do país."""
        return self.get_data(country_code).locale

    def get_language(self, country_code: str) -> str:
        """Atalho para idioma do país."""
        return self.get_data(country_code).language

    def get_lg_lc(self, country_code: str) -> Tuple[str, str]:
        """Retorna (language, locale) para o código de país."""
        return self.get_data(country_code).get_lg_lc()

    def get_mcc_mnc(self, country_code: str) -> Tuple[str, str]:
        """Retorna (MCC, MNC) padrão para o código de país."""
        return self.get_data(country_code).get_mcc_mnc()


# Instância global para uso pelas funções legadas e PhoneUtils
_helper: Optional[PhoneCountryHelper] = None


def _get_helper() -> PhoneCountryHelper:
    global _helper
    if _helper is None:
        _helper = PhoneCountryHelper()
    return _helper


# ---- Funções auxiliares (compatibilidade com código existente) ----

def get_mobile_cc(phone_number: str) -> str:
    """
    Obtém código de país (country code) do número de telefone.

    Args:
        phone_number: Número de telefone (com ou sem código de país)

    Returns:
        Código de país (ex: "55" para Brasil)
    """
    return _get_helper().get_country_code(phone_number)


def get_lg_lc(country_code: str) -> Tuple[str, str]:
    """
    Obtém código de idioma (lg) e localização (lc) a partir do código de país.

    Args:
        country_code: Código de país (ex: "55")

    Returns:
        Tupla (lg, lc) - código de idioma e localização
    """
    return _get_helper().get_lg_lc(country_code)


def get_mcc_mnc(phone_number: str) -> Tuple[str, str]:
    """
    Obtém MCC (Mobile Country Code) e MNC (Mobile Network Code) do número.

    Args:
        phone_number: Número de telefone (com ou sem código de país)

    Returns:
        Tupla (MCC, MNC)
    """
    cc = get_mobile_cc(phone_number)
    return _get_helper().get_mcc_mnc(cc)


def get_country_data(country_code: str) -> CountryPhoneData:
    """Retorna dados estruturados do país (locale, language, mcc, mnc, etc.)."""
    return _get_helper().get_data(country_code)


def get_country_data_from_phone(phone_number: str) -> CountryPhoneData:
    """Obtém CountryPhoneData a partir do número (extrai cc e retorna dados)."""
    cc = get_mobile_cc(phone_number)
    return _get_helper().get_data(cc)


class PhoneUtils:
    """
    Utilitários para números de telefone (fachada estática).
    Dados vêm de proto/countries.json.
    """

    @staticmethod
    def getMobileCC(phone_number: str) -> str:
        """Obtém código de país do número de telefone."""
        return get_mobile_cc(phone_number)

    @staticmethod
    def getLGLC(country_code: str) -> Tuple[str, str]:
        """Obtém código de idioma e localização (lg, lc)."""
        return get_lg_lc(country_code)

    @staticmethod
    def get_mcc_mnc(phone_number: str) -> Tuple[str, str]:
        """Obtém MCC e MNC do número de telefone."""
        return get_mcc_mnc(phone_number)
