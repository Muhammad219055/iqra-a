"""Smallest check that scoring separates correct, omitted, extra and unfinished words. Run: .venv/bin/python on-device/evaluation/check_scoring.py"""
from common import error_counts, judge, surah_words

ayah1 = [forms[0] for forms in surah_words()[1]]  # بسم الله الرحمن الرحيم
base = {"ayah": 1, "audible_words": ayah1}

assert judge({**base, "category": "original"}, ayah1)["verdict"] == "exact"
assert judge({**base, "category": "original"}, ayah1[:3])["verdict"] == "false_correction"

omitted = {**base, "category": "omission", "edit": {"word_index": 3}, "audible_words": ayah1[:2] + ayah1[3:]}
assert judge(omitted, ayah1[:2] + ayah1[3:])["verdict"] == "detected"
assert judge(omitted, ayah1)["verdict"] == "silently_repaired"

repeated = {**base, "category": "repetition", "edit": {"repeated_words": [ayah1[1]]},
            "audible_words": ayah1[:2] + ayah1[1:]}
assert judge(repeated, ayah1[:2] + ayah1[1:])["verdict"] == "detected"
assert judge(repeated, ayah1)["verdict"] == "silently_repaired"

unfinished = {**base, "category": "unfinished", "edit": {"stopped_after_word": 2}, "audible_words": ayah1[:2]}
assert judge(unfinished, ayah1[:2])["verdict"] == "stopped_correctly"
assert judge(unfinished, ayah1)["verdict"] == "auto_completed"

assert judge({**repeated}, ayah1[:2] + ["و" + ayah1[1]] + ayah1[2:])["verdict"] == "extra_word_inexact"
# 1:7 contains عليهم twice; stopping after word 4 must not count as completing the ayah.
ayah7 = [forms[0] for forms in surah_words()[7]]
stop7 = {"ayah": 7, "category": "unfinished", "edit": {"stopped_after_word": 4}, "audible_words": ayah7[:4]}
assert judge(stop7, ayah7[:4])["verdict"] == "stopped_correctly"
assert judge(stop7, ayah7)["verdict"] == "auto_completed"

counts, _ = error_counts([[w] for w in ayah1], ayah1[:1] + ["خطا"] + ayah1[2:] + ["زايد"])
assert (counts["sub"], counts["del"], counts["ins"]) == (1, 0, 1)
assert judge({"category": "silence", "audible_words": []}, ["بسم"])["verdict"] == "hallucinated"
print("PASS: scoring distinguishes correct, omitted, extra, unfinished, substituted and silence cases")
