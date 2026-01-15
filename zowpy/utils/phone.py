"""
Phone Utilities - Utilitários para números de telefone.

Substitui zowsuplib.common.utils.Utils
"""

from typing import Tuple, Optional


# Mapeamento de código de país para código de localização
COUNTRY_TO_LOCALE = {
    "1": "us",  # USA/Canada
    "7": "ru",  # Russia
    "20": "eg",  # Egypt
    "27": "za",  # South Africa
    "30": "gr",  # Greece
    "31": "nl",  # Netherlands
    "32": "be",  # Belgium
    "33": "fr",  # France
    "34": "es",  # Spain
    "36": "hu",  # Hungary
    "39": "it",  # Italy
    "40": "ro",  # Romania
    "41": "ch",  # Switzerland
    "43": "at",  # Austria
    "44": "gb",  # UK
    "45": "dk",  # Denmark
    "46": "se",  # Sweden
    "47": "no",  # Norway
    "48": "pl",  # Poland
    "49": "de",  # Germany
    "51": "pe",  # Peru
    "52": "mx",  # Mexico
    "53": "cu",  # Cuba
    "54": "ar",  # Argentina
    "55": "br",  # Brazil
    "56": "cl",  # Chile
    "57": "co",  # Colombia
    "58": "ve",  # Venezuela
    "60": "my",  # Malaysia
    "61": "au",  # Australia
    "62": "id",  # Indonesia
    "63": "ph",  # Philippines
    "64": "nz",  # New Zealand
    "65": "sg",  # Singapore
    "66": "th",  # Thailand
    "81": "jp",  # Japan
    "82": "kr",  # South Korea
    "84": "vn",  # Vietnam
    "86": "cn",  # China
    "90": "tr",  # Turkey
    "91": "in",  # India
    "92": "pk",  # Pakistan
    "93": "af",  # Afghanistan
    "94": "lk",  # Sri Lanka
    "95": "mm",  # Myanmar
    "98": "ir",  # Iran
    "212": "ma",  # Morocco
    "213": "dz",  # Algeria
    "216": "tn",  # Tunisia
    "218": "ly",  # Libya
    "220": "gm",  # Gambia
    "221": "sn",  # Senegal
    "222": "mr",  # Mauritania
    "223": "ml",  # Mali
    "224": "gn",  # Guinea
    "225": "ci",  # Ivory Coast
    "226": "bf",  # Burkina Faso
    "227": "ne",  # Niger
    "228": "tg",  # Togo
    "229": "bj",  # Benin
    "230": "mu",  # Mauritius
    "231": "lr",  # Liberia
    "232": "sl",  # Sierra Leone
    "233": "gh",  # Ghana
    "234": "ng",  # Nigeria
    "235": "td",  # Chad
    "236": "cf",  # Central African Republic
    "237": "cm",  # Cameroon
    "238": "cv",  # Cape Verde
    "239": "st",  # Sao Tome and Principe
    "240": "gq",  # Equatorial Guinea
    "241": "ga",  # Gabon
    "242": "cg",  # Republic of the Congo
    "243": "cd",  # Democratic Republic of the Congo
    "244": "ao",  # Angola
    "245": "gw",  # Guinea-Bissau
    "246": "io",  # British Indian Ocean Territory
    "248": "sc",  # Seychelles
    "249": "sd",  # Sudan
    "250": "rw",  # Rwanda
    "251": "et",  # Ethiopia
    "252": "so",  # Somalia
    "253": "dj",  # Djibouti
    "254": "ke",  # Kenya
    "255": "tz",  # Tanzania
    "256": "ug",  # Uganda
    "257": "bi",  # Burundi
    "258": "mz",  # Mozambique
    "260": "zm",  # Zambia
    "261": "mg",  # Madagascar
    "262": "re",  # Reunion
    "263": "zw",  # Zimbabwe
    "264": "na",  # Namibia
    "265": "mw",  # Malawi
    "266": "ls",  # Lesotho
    "267": "bw",  # Botswana
    "268": "sz",  # Swaziland
    "269": "km",  # Comoros
    "290": "sh",  # Saint Helena
    "291": "er",  # Eritrea
    "297": "aw",  # Aruba
    "298": "fo",  # Faroe Islands
    "299": "gl",  # Greenland
    "350": "gi",  # Gibraltar
    "351": "pt",  # Portugal
    "352": "lu",  # Luxembourg
    "353": "ie",  # Ireland
    "354": "is",  # Iceland
    "355": "al",  # Albania
    "356": "mt",  # Malta
    "357": "cy",  # Cyprus
    "358": "fi",  # Finland
    "359": "bg",  # Bulgaria
    "370": "lt",  # Lithuania
    "371": "lv",  # Latvia
    "372": "ee",  # Estonia
    "373": "md",  # Moldova
    "374": "am",  # Armenia
    "375": "by",  # Belarus
    "376": "ad",  # Andorra
    "377": "mc",  # Monaco
    "378": "sm",  # San Marino
    "380": "ua",  # Ukraine
    "381": "rs",  # Serbia
    "382": "me",  # Montenegro
    "383": "xk",  # Kosovo
    "385": "hr",  # Croatia
    "386": "si",  # Slovenia
    "387": "ba",  # Bosnia and Herzegovina
    "389": "mk",  # North Macedonia
    "420": "cz",  # Czech Republic
    "421": "sk",  # Slovakia
    "423": "li",  # Liechtenstein
    "500": "fk",  # Falkland Islands
    "501": "bz",  # Belize
    "502": "gt",  # Guatemala
    "503": "sv",  # El Salvador
    "504": "hn",  # Honduras
    "505": "ni",  # Nicaragua
    "506": "cr",  # Costa Rica
    "507": "pa",  # Panama
    "508": "pm",  # Saint Pierre and Miquelon
    "509": "ht",  # Haiti
    "590": "gp",  # Guadeloupe
    "591": "bo",  # Bolivia
    "592": "gy",  # Guyana
    "593": "ec",  # Ecuador
    "594": "gf",  # French Guiana
    "595": "py",  # Paraguay
    "596": "mq",  # Martinique
    "597": "sr",  # Suriname
    "598": "uy",  # Uruguay
    "599": "cw",  # Curacao
    "670": "tl",  # East Timor
    "672": "nf",  # Norfolk Island
    "673": "bn",  # Brunei
    "674": "nr",  # Nauru
    "675": "pg",  # Papua New Guinea
    "676": "to",  # Tonga
    "677": "sb",  # Solomon Islands
    "678": "vu",  # Vanuatu
    "679": "fj",  # Fiji
    "680": "pw",  # Palau
    "681": "wf",  # Wallis and Futuna
    "682": "ck",  # Cook Islands
    "683": "nu",  # Niue
    "685": "ws",  # Samoa
    "686": "ki",  # Kiribati
    "687": "nc",  # New Caledonia
    "688": "tv",  # Tuvalu
    "689": "pf",  # French Polynesia
    "690": "tk",  # Tokelau
    "691": "fm",  # Micronesia
    "692": "mh",  # Marshall Islands
    "850": "kp",  # North Korea
    "852": "hk",  # Hong Kong
    "853": "mo",  # Macau
    "855": "kh",  # Cambodia
    "856": "la",  # Laos
    "880": "bd",  # Bangladesh
    "886": "tw",  # Taiwan
    "960": "mv",  # Maldives
    "961": "lb",  # Lebanon
    "962": "jo",  # Jordan
    "963": "sy",  # Syria
    "964": "iq",  # Iraq
    "965": "kw",  # Kuwait
    "966": "sa",  # Saudi Arabia
    "967": "ye",  # Yemen
    "968": "om",  # Oman
    "970": "ps",  # Palestine
    "971": "ae",  # UAE
    "972": "il",  # Israel
    "973": "bh",  # Bahrain
    "974": "qa",  # Qatar
    "975": "bt",  # Bhutan
    "976": "mn",  # Mongolia
    "977": "np",  # Nepal
    "992": "tj",  # Tajikistan
    "993": "tm",  # Turkmenistan
    "994": "az",  # Azerbaijan
    "995": "ge",  # Georgia
    "996": "kg",  # Kyrgyzstan
    "998": "uz",  # Uzbekistan
}


def get_mobile_cc(phone_number: str) -> str:
    """
    Obtém código de país (country code) do número de telefone.
    
    Args:
        phone_number: Número de telefone (com ou sem código de país)
    
    Returns:
        Código de país (ex: "55" para Brasil)
    """
    # Remove caracteres não numéricos
    digits = ''.join(filter(str.isdigit, phone_number))
    
    if not digits:
        return "1"  # Default USA
    
    # Tenta códigos de 1 a 3 dígitos
    # Códigos de 1 dígito
    if digits.startswith("1") and len(digits) >= 10:
        return "1"
    
    # Códigos de 2 dígitos
    for code_len in [2, 3]:
        if len(digits) >= code_len:
            code = digits[:code_len]
            if code in COUNTRY_TO_LOCALE:
                return code
    
    # Se não encontrou, assume código de 1 dígito
    return digits[0] if digits else "1"


def get_lg_lc(country_code: str) -> Tuple[str, str]:
    """
    Obtém código de idioma (lg) e localização (lc) a partir do código de país.
    
    Args:
        country_code: Código de país (ex: "55")
    
    Returns:
        Tupla (lg, lc) - código de idioma e localização
    """
    locale = COUNTRY_TO_LOCALE.get(country_code, "us")
    
    # Mapeamento básico de locale para idioma
    locale_to_lang = {
        "us": "en",
        "gb": "en",
        "br": "pt",
        "pt": "pt",
        "es": "es",
        "mx": "es",
        "ar": "es",
        "fr": "fr",
        "de": "de",
        "it": "it",
        "ru": "ru",
        "cn": "zh",
        "jp": "ja",
        "kr": "ko",
        "in": "hi",
        "pk": "ur",
        "tr": "tr",
        "sa": "ar",
        "ae": "ar",
        "eg": "ar",
        "il": "he",
        "th": "th",
        "id": "id",
        "my": "ms",
        "ph": "en",
        "vn": "vi",
        "sg": "en",
        "au": "en",
        "nz": "en",
        "ca": "en",
    }
    
    lg = locale_to_lang.get(locale, "en")
    
    return lg, locale


# Mapeamento de código de país para MCC (Mobile Country Code)
# Valores padrão comuns para WhatsApp
COUNTRY_TO_MCC = {
    "1": "310",  # USA/Canada
    "7": "250",  # Russia
    "20": "602",  # Egypt
    "27": "655",  # South Africa
    "30": "202",  # Greece
    "31": "204",  # Netherlands
    "32": "206",  # Belgium
    "33": "208",  # France
    "34": "214",  # Spain
    "36": "216",  # Hungary
    "39": "222",  # Italy
    "40": "226",  # Romania
    "41": "228",  # Switzerland
    "43": "232",  # Austria
    "44": "234",  # UK
    "45": "238",  # Denmark
    "46": "240",  # Sweden
    "47": "242",  # Norway
    "48": "260",  # Poland
    "49": "262",  # Germany
    "51": "716",  # Peru
    "52": "334",  # Mexico
    "53": "368",  # Cuba
    "54": "722",  # Argentina
    "55": "724",  # Brazil
    "56": "730",  # Chile
    "57": "732",  # Colombia
    "58": "734",  # Venezuela
    "60": "502",  # Malaysia
    "61": "505",  # Australia
    "62": "510",  # Indonesia
    "63": "515",  # Philippines
    "64": "530",  # New Zealand
    "65": "525",  # Singapore
    "66": "520",  # Thailand
    "81": "440",  # Japan
    "82": "450",  # South Korea
    "84": "452",  # Vietnam
    "86": "460",  # China
    "90": "286",  # Turkey
    "91": "404",  # India
    "92": "410",  # Pakistan
    "351": "268",  # Portugal
    "351": "268",  # Portugal
    "55": "724",  # Brazil (mais comum)
}

# MNC padrão (Mobile Network Code) - geralmente "05" ou "01"
DEFAULT_MNC = "05"


def get_mcc_mnc(phone_number: str) -> Tuple[str, str]:
    """
    Obtém MCC (Mobile Country Code) e MNC (Mobile Network Code) do número de telefone.
    
    Args:
        phone_number: Número de telefone (com ou sem código de país)
    
    Returns:
        Tupla (MCC, MNC) - códigos de país móvel e rede móvel
    """
    country_code = get_mobile_cc(phone_number)
    mcc = COUNTRY_TO_MCC.get(country_code, "724")  # Default Brasil
    mnc = DEFAULT_MNC
    return mcc, mnc


class PhoneUtils:
    """
    Utilitários para números de telefone.
    Substitui zowsuplib.common.utils.Utils
    """
    
    @staticmethod
    def getMobileCC(phone_number: str) -> str:
        """Obtém código de país do número de telefone."""
        return get_mobile_cc(phone_number)
    
    @staticmethod
    def getLGLC(country_code: str) -> Tuple[str, str]:
        """Obtém código de idioma e localização."""
        return get_lg_lc(country_code)
    
    @staticmethod
    def get_mcc_mnc(phone_number: str) -> Tuple[str, str]:
        """Obtém MCC e MNC do número de telefone."""
        return get_mcc_mnc(phone_number)  # Chama função global

