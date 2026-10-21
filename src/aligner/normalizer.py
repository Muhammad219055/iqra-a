"""
Arabic & Quranic Text Normalizer
Provides two-layer representation:
- Layer A: Canonical Uthmani text (with Harakat / diacritics preserved)
- Layer B: Normalized phonetic/consonant skeleton for robust acoustic alignment
"""

import re
import unicodedata

# Tashkeel / Harakat Unicode range: 0x064B to 0x065F, plus 0x0670 (superscript alif)
HARAKAT_RE = re.compile(r'[\u064B-\u065F\u0670\u06D6-\u06ED]')

# Quranic pause / waqf annotation marks
WAQF_RE = re.compile(r'[\u06D6-\u06DC\u06DF-\u06E4\u06E9-\u06EA]')

# Tatweel / Kashida
TATWEEL_RE = re.compile(r'\u0640')


def strip_harakat(text: str) -> str:
    """Removes all diacritics (harakat, sukun, tanween, dagger alif, and Quranic waqf marks)."""
    return HARAKAT_RE.sub('', text)


def normalize_for_matching(text: str) -> str:
    """
    Normalizes Quranic Arabic text into a consonant skeleton suitable for ASR alignment.
    Handles orthographic variations:
    - Normalizes hamzas: أ, إ, آ, ء, ٱ -> ا (or appropriate base)
    - Normalizes Alif Maqsura: ى -> ي
    - Normalizes Taa Marbuta: ة -> ه
    - Strips tatweel (kashida)
    - Strips punctuation and non-Arabic marks
    - Strips all harakat/vowels
    """
    if not text:
        return ""

    # Strip harakat first
    t = strip_harakat(text)

    # Strip tatweel
    t = TATWEEL_RE.sub('', t)

    # Normalize forms of Alif (including Alif Wasl \u0671)
    t = re.sub(r'[\u0622\u0623\u0625\u0671]', '\u0627', t)

    # Normalize Alif Maqsura to Yaa
    t = re.sub(r'\u0649', '\u064A', t)

    # Normalize Taa Marbuta to Haa
    t = re.sub(r'\u0629', '\u0647', t)

    # Normalize Waw with Hamza and Yaa with Hamza
    t = re.sub(r'\u0624', '\u0648', t)
    t = re.sub(r'\u0626', '\u064A', t)

    # Remove non-Arabic characters except whitespace
    t = re.sub(r'[^\u0621-\u064A\s]', '', t)

    # Normalize multiple spaces
    t = re.sub(r'\s+', ' ', t).strip()

    return t


def tokenize_words(text: str) -> list[str]:
    """Splits text into words by whitespace."""
    return [w for w in text.split() if w.strip()]
