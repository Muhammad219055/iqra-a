"""Shared audio I/O, text normalization and word-level scoring for the offline evaluation."""
import json
import sys
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
EVAL = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from src.aligner.normalizer import normalize_for_matching, tokenize_words  # noqa: E402

RATE = 16000


def read_wav(path):
    with wave.open(str(path)) as w:
        assert (w.getnchannels(), w.getframerate(), w.getsampwidth()) == (1, RATE, 2), f"{path}: need 16 kHz mono PCM16"
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768


def write_wav(path, samples):
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(np.round(samples * 32768), -32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE); w.writeframes(pcm.tobytes())


def words(text):
    return tokenize_words(normalize_for_matching(text))


def surah_words():
    """Per ayah: list of accepted normalized forms for each word (Uthmani and imla'i spellings)."""
    data = json.loads((ROOT / "data/text/quran_surah_1.json").read_text())
    return {a["ayah"]: [sorted({normalize_for_matching(w["text_uthmani"]), normalize_for_matching(w["text_imlaei"])})
                        for w in a["words"]] for a in data["ayahs"]}


def align(ref, hyp):
    """Levenshtein alignment. ref items are sets/lists of accepted spellings; hyp is a word list.
    Returns ops: ('match'|'sub', i, j), ('del', i, None) = reference word not heard, ('ins', None, j) = extra word."""
    n, m = len(ref), len(hyp)
    cost = np.zeros((n + 1, m + 1), dtype=int)
    cost[:, 0] = range(n + 1); cost[0, :] = range(m + 1)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            same = hyp[j - 1] in ref[i - 1]
            cost[i, j] = min(cost[i - 1, j - 1] + (0 if same else 1), cost[i - 1, j] + 1, cost[i, j - 1] + 1)
    # Backtrace prefers deleting later reference words on ties, so a repeated word (عليهم in 1:7)
    # matches its first occurrence and an unfinished ayah is not mistaken for a completed one.
    ops, i, j = [], n, m
    while i or j:
        if i and cost[i, j] == cost[i - 1, j] + 1:
            ops.append(("del", i - 1, None)); i -= 1
        elif i and j and cost[i, j] == cost[i - 1, j - 1] + (0 if hyp[j - 1] in ref[i - 1] else 1):
            ops.append(("match" if hyp[j - 1] in ref[i - 1] else "sub", i - 1, j - 1)); i -= 1; j -= 1
        else:
            ops.append(("ins", None, j - 1)); j -= 1
    return ops[::-1]


def error_counts(ref, hyp):
    ops = align(ref, hyp)
    count = {k: sum(op[0] == k for op in ops) for k in ("match", "sub", "del", "ins")}
    count["wer"] = (count["sub"] + count["del"] + count["ins"]) / max(1, len(ref))
    return count, ops


def judge(entry, hyp):
    """Category-specific verdict comparing the transcript with the canonical ayah and the audible truth."""
    truth = [[w] for w in entry["audible_words"]]
    vs_truth, _ = error_counts(truth, hyp)
    out = {"vs_audible": vs_truth}
    kind = entry["category"]
    if kind == "silence":
        out["verdict"] = "hallucinated" if hyp else "empty"
        return out
    canonical = surah_words()[entry["ayah"]] if entry.get("ayah") else [[w] for w in entry["audible_words"]]
    vs_canon, ops = error_counts(canonical, hyp)
    out["vs_canonical"] = vs_canon
    if kind == "original":
        out["verdict"] = "exact" if vs_truth["wer"] == 0 else "false_correction"
    elif kind == "omission":
        k = entry["edit"]["word_index"] - 1
        state = next(op[0] for op in ops if op[1] == k)
        out["verdict"] = {"del": "detected", "match": "silently_repaired"}.get(state, "misrecognized")
    elif kind == "repetition":
        rep = entry["edit"]["repeated_words"]
        def occurrences(seq):
            return sum(seq[i:i + len(rep)] == rep for i in range(len(seq) - len(rep) + 1))
        expected = occurrences(entry["audible_words"])
        heard = occurrences(hyp)
        out["repeat_occurrences"] = {"audible": expected, "transcribed": heard}
        if heard >= expected: out["verdict"] = "detected"
        elif vs_canon["wer"] == 0: out["verdict"] = "silently_repaired"
        # An extra word was transcribed but not as the exact repeated word (e.g. "والرحمن").
        elif vs_canon["ins"] > 0: out["verdict"] = "extra_word_inexact"
        else: out["verdict"] = "misrecognized"
    elif kind == "unfinished":
        k = entry["edit"]["stopped_after_word"]
        tail = [op[0] for op in ops if op[1] is not None and op[1] >= k]
        completed = sum(t == "match" for t in tail)
        out["completed_tail_words"] = completed
        out["verdict"] = "stopped_correctly" if completed == 0 else "auto_completed"
    return out
