"""
Word-Level Alignment and Mistake Detection Engine.

Implements sequence alignment (Needleman-Wunsch / Levenshtein on word tokens)
to compare recognized speech tokens against canonical Quranic text.

Mistake categories:
- INCORRECT_WORDS: Substitution (wrong word recited)
- MISSED_WORDS: Deletion (word skipped or omitted)
- EXTRA_WORDS: Insertion (hallucinated or repetitive word)
- INCORRECT_TASHKEEL: Same consonant skeleton, different diacritics
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from .normalizer import normalize_for_matching, strip_harakat


class MistakeType(str, Enum):
    INCORRECT_WORDS = "INCORRECT_WORDS"
    MISSED_WORDS = "MISSED_WORDS"
    EXTRA_WORDS = "EXTRA_WORDS"
    INCORRECT_TASHKEEL = "INCORRECT_TASHKEEL"


@dataclass
class AlignedToken:
    expected_word: Optional[dict]       # {surah, ayah, word_index_in_ayah, text_uthmani, normalized, ...}
    recognized_word: Optional[str]     # Raw recognized token from ASR
    normalized_rec: Optional[str]      # Normalized recognized token
    status: str                        # "MATCH" | "MISSED_WORDS" | "INCORRECT_WORDS" | "EXTRA_WORDS" | "INCORRECT_TASHKEEL"
    mistake_type: Optional[MistakeType] = None


def levenshtein_distance(s1: str, s2: str) -> int:
    """Character-level Levenshtein distance."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def align_sequences(expected_words: List[dict], recognized_tokens: List[str]) -> List[AlignedToken]:
    """
    Aligns recognized tokens from ASR with the expected canonical Quran words.
    Uses dynamic programming token-level sequence alignment.
    """
    M = len(expected_words)
    N = len(recognized_tokens)

    # Pre-normalize recognized tokens
    rec_norm = [normalize_for_matching(t) for t in recognized_tokens]
    exp_norm = [w["normalized"] for w in expected_words]

    # DP Table: dp[i][j] is min edit cost for expected[:i] and recognized[:j]
    # Costs:
    # Match: 0
    # Deletion (missed expected word): 1.0
    # Insertion (extra recognized word): 1.0
    # Substitution (incorrect word): 1.0 (or 0.3 if character distance is tiny)
    dp = [[0.0] * (N + 1) for _ in range(M + 1)]

    for i in range(1, M + 1):
        dp[i][0] = i * 1.0
    for j in range(1, N + 1):
        dp[0][j] = j * 1.0

    for i in range(1, M + 1):
        for j in range(1, N + 1):
            e_str = exp_norm[i - 1]
            r_str = rec_norm[j - 1]

            if e_str == r_str:
                cost_sub = 0.0
            else:
                # Check character-level closeness
                char_dist = levenshtein_distance(e_str, r_str)
                max_len = max(len(e_str), len(r_str), 1)
                sim = 1.0 - (char_dist / max_len)
                if sim >= 0.75:
                    cost_sub = 0.2  # Minor phonetic or spelling divergence (e.g. slight ASR spelling variance)
                else:
                    cost_sub = 1.0

            dp[i][j] = min(
                dp[i - 1][j] + 1.0,        # Deletion (Expected word missed)
                dp[i][j - 1] + 1.0,        # Insertion (Extra word recognized)
                dp[i - 1][j - 1] + cost_sub  # Match or Substitution
            )

    # Backtracking to build aligned path
    i, j = M, N
    alignment: List[AlignedToken] = []

    while i > 0 or j > 0:
        if i > 0 and j > 0:
            e_str = exp_norm[i - 1]
            r_str = rec_norm[j - 1]
            char_dist = levenshtein_distance(e_str, r_str)
            max_len = max(len(e_str), len(r_str), 1)
            sim = 1.0 - (char_dist / max_len)
            cost_sub = 0.0 if e_str == r_str else (0.2 if sim >= 0.75 else 1.0)

            # Check if this step came from substitution/match
            if abs(dp[i][j] - (dp[i - 1][j - 1] + cost_sub)) < 1e-5:
                if cost_sub == 0.0 or sim >= 0.75:
                    status = "MATCH"
                    m_type = None
                else:
                    status = "INCORRECT_WORDS"
                    m_type = MistakeType.INCORRECT_WORDS

                alignment.append(AlignedToken(
                    expected_word=expected_words[i - 1],
                    recognized_word=recognized_tokens[j - 1],
                    normalized_rec=r_str,
                    status=status,
                    mistake_type=m_type,
                ))
                i -= 1
                j -= 1
                continue

        if i > 0 and abs(dp[i][j] - (dp[i - 1][j] + 1.0)) < 1e-5:
            # Deletion: expected word was not spoken
            alignment.append(AlignedToken(
                expected_word=expected_words[i - 1],
                recognized_word=None,
                normalized_rec=None,
                status="MISSED_WORDS",
                mistake_type=MistakeType.MISSED_WORDS,
            ))
            i -= 1
        else:
            # Insertion: recognized word has no counterpart in expected
            alignment.append(AlignedToken(
                expected_word=None,
                recognized_word=recognized_tokens[j - 1],
                normalized_rec=rec_norm[j - 1],
                status="EXTRA_WORDS",
                mistake_type=MistakeType.EXTRA_WORDS,
            ))
            j -= 1

    alignment.reverse()
    return alignment
