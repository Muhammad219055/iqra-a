# Quran Recitation & Memorization Tutor (Local-First)

An independent, 100% free, local-first Quran recitation and memorization tutor inspired by Tarteel. Built with open-source models and datasets, running entirely on Apple Silicon with zero cloud inference costs.

---

## Features
- **Local Speech Recognition (ASR):** Powered by `tarteel-ai/whisper-base-ar-quran` (Apache 2.0) running on Apple Silicon Metal Performance Shaders (`mps`).
- **Word-Level Sequence Alignment:** Levenshtein DP aligner detecting `MATCH`, `MISSED_WORDS`, `INCORRECT_WORDS`, `EXTRA_WORDS`.
- **Teacher Prompting (Headline Feature):** When you make a mistake or hesitate for $>2.5$ seconds, the app plays the correct next 2–3 words in a real Qari's voice (Mishari or Husary) and gates the microphone to prevent audio feedback.
- **Authentic Madani Mushaf UI:** 15-line Medina layout rendered with canonical Uthmani script and real-time word highlighting.
- **Memorization Mode:** Blurs upcoming words; tap to reveal with a `PEEKED_WORDS` counter.
- **Session History:** Persisted locally in SQLite (`data/user_db.sqlite`).

---

## Quick Start (Web Prototype on Mac)

### 1. Launch the Local Server
```bash
cd /Users/muhammad/quran-tutor
.venv/bin/python start.py
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in Chrome or Safari.

### 2. Run the Offline CLI (Milestone 1)
```bash
PYTHONPATH=. .venv/bin/python src/cli.py tests/audio/al_fatiha_full.wav --surah 1 --start-ayah 1 --end-ayah 7
```

### 3. Test Audio Prompt Slicing (Milestone 2)
```bash
PYTHONPATH=. .venv/bin/python src/prompt_cli.py --surah 1 --ayah 1 --word 1 --count 3 --reciter mishari --play
```

### 4. Run Automated Test Suite
```bash
PYTHONPATH=. .venv/bin/python tests/test_milestone_1.py
PYTHONPATH=. .venv/bin/python tests/test_milestone_2.py
PYTHONPATH=. .venv/bin/python tests/test_milestone_3_ws.py
PYTHONPATH=. .venv/bin/python tests/test_milestone_4_db.py
```

---

## iOS Native Roadmap (Phase 2)
See [`docs/IOS_IMPLEMENTATION_GUIDE.md`](docs/IOS_IMPLEMENTATION_GUIDE.md) for the complete Swift, CoreML, and AVAudioEngine implementation guide.
