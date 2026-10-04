"""
languages.py
------------
Lightweight language-code tables shared across the project.

Kept free of heavy imports (torch / transformers) so that checking
whether a language is Indic never triggers loading the IndicTrans2 stack.
"""

# Whisper language code -> IndicTrans2 language code
INDIC_LANGUAGE_CODES = {
    "as": "asm_Beng",
    "bn": "ben_Beng",
    "brx": "brx_Deva",
    "doi": "doi_Deva",
    "gom": "gom_Deva",
    "gu": "guj_Gujr",
    "hi": "hin_Deva",
    "kn": "kan_Knda",
    "ks": "kas_Arab",
    "mai": "mai_Deva",
    "ml": "mal_Mlym",
    "mr": "mar_Deva",
    "mni": "mni_Mtei",
    "ne": "npi_Deva",
    "or": "ory_Orya",
    "pa": "pan_Guru",
    "sa": "san_Deva",
    "sat": "sat_Olck",
    "sd": "snd_Arab",
    "ta": "tam_Taml",
    "te": "tel_Telu",
    "ur": "urd_Arab",
}


def is_indic_language(language) -> bool:
    """Return True if the Whisper language is supported by IndicTrans2."""

    return language in INDIC_LANGUAGE_CODES
