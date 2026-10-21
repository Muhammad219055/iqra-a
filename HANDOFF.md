# Master Handoff: Quran Recitation & Memorization Tutor

## 1. Project Overview & Vision

This repository implements a **free, open-source, local-first Quran recitation and memorization tutor** inspired by the commercial app **Tarteel**. The project specifications derive from:
1. `~/GEMINI_QURAN_APP_PROMPT.md`: Functional requirements, speech recognition pipeline, mistake detection taxonomy, audio prompt slicer, and local-first architecture.
2. `~/TARTEEL_RESEARCH.md`: Deep static reverse-engineering report of the Tarteel Android APK (`com.mmmoussa.iqra` v5.81.7), detailing its client-server WebSocket protocol, audio capture settings, SQLite layout schemas, and mistake classifications.

### Core Value Proposition
- **100% Free & Open Source**: No proprietary cloud APIs, no subscriptions, no vendor lock-in.
- **Local-First AI Engine**: Runs Whisper ASR fine-tuned on Quranic Arabic (`tarteel-ai/whisper-base-ar-quran`) locally on Apple Silicon GPU (`mps`) or CPU.
- **Teacher Audio Prompting**: When the user hesitates (> 2.5s) or makes a mistake, the engine slices the exact words $N$ to $N+2$ in a real Qari's voice (Mishari Alafasy or Mahmoud Al-Husary) and plays it back, muting the microphone during playback with a 150ms echo drain.
- **Cross-Platform**: Tested web interface (`web/`) and React Native iOS/Android app (`mobile/`).

---

## 2. Repository Layout & File Manifest

```
/Users/muhammad/quran-tutor/
├── start.py                            # Main launcher: binds FastAPI server to 0.0.0.0:8000
├── requirements.txt                    # Python dependencies
├── .gitignore                          # Git ignore rules
├── HANDOFF.md                          # This document
│
├── src/                                # Core Python Engine
│   ├── aligner/
│   │   ├── normalizer.py               # Arabic text normalizer (strips Tashkeel, normalizes Alif/Waslah)
│   │   ├── diff.py                     # Levenshtein sequence aligner & mistake classifier
│   │   ├── tracker.py                  # Recitation progress tracker & word state manager
│   │   └── hesitation.py               # 2.5-second silence & hesitation detector
│   ├── asr/
│   │   ├── engine.py                   # Local Whisper ASR (tarteel-ai/whisper-base-ar-quran on MPS)
│   │   └── vad.py                      # Voice Activity Detection (energy/VAD filter)
│   ├── audio/
│   │   └── slicer.py                   # Cosine-windowed prompt audio slicer (words N to N+2)
│   └── server/
│       ├── app.py                      # FastAPI application & REST endpoints
│       ├── ws_handler.py               # Real-time WebSocket recitation gateway (/ws/recite)
│       └── db.py                       # SQLite database for sessions, mistakes, and history
│
├── data/                               # Offline Datasets & Audio Assets
│   ├── text/
│   │   └── quran_surah_1.json          # Pre-tokenized Surah Al-Fatiha with Uthmani & normalized text
│   ├── timings/
│   │   ├── surah_1_mishari.json        # Word-level millisecond timing intervals for Mishari Alafasy
│   │   └── surah_1_husary.json         # Word-level millisecond timing intervals for Mahmoud Al-Husary
│   └── audio_cache/
│       ├── mishari/001_16k.wav         # Offline high-quality 16kHz audio for Surah 1 (Mishari)
│       └── husary/001_16k.wav          # Offline high-quality 16kHz audio for Surah 1 (Husary)
│
├── tests/                              # Automated Pytest Suites (All passing)
│   ├── test_milestone_1.py             # Normalizer & Levenshtein alignment unit tests
│   ├── test_milestone_2.py             # Audio prompt slicer & cosine windowing tests
│   ├── test_milestone_3_ws.py          # WebSocket client-server streaming integration tests
│   └── test_milestone_4_db.py          # SQLite session persistence & mistake tracking tests
│
├── web/                                # Functional Web Prototype
│   ├── index.html                      # Clean web client with live Mushaf rendering
│   ├── js/
│   │   ├── app.js                      # WebSocket client & audio prompt handler
│   │   └── audio_worklet.js            # Raw PCM 16kHz audio capture worklet
│   └── css/
│       └── style.css                   # Classic Islamic dark/gold UI styling
│
└── mobile/                             # React Native / Expo Mobile App (Needs UI Redesign)
    ├── App.js                          # Main React Native component
    ├── app.json                        # Expo configuration
    ├── package.json                    # Dependencies (Expo 52, expo-av, expo-font, url-polyfill)
    └── assets/
        ├── fonts/
        │   ├── UthmanicHafs.ttf        # King Fahd Complex authentic Uthmanic font (242 KB)
        │   └── AmiriQuran-Regular.ttf  # Amiri Quran font (137 KB)
        ├── data/
        │   └── quran_surah_1.json      # Bundled Surah 1 token data
        └── mushaf_pages/
            ├── page001.png             # Medina Mushaf Page 1 (Surah Al-Fatiha)
            ├── page002.png             # Medina Mushaf Page 2 (Al-Baqarah 1-5)
            └── page003.png             # Medina Mushaf Page 3 (Al-Baqarah 6-16)
```

---

## 3. Core Engine Components & Technical Details

### 3.1 Arabic Normalizer (`src/aligner/normalizer.py`)
Standardizes spoken ASR outputs against canonical Quranic text:
- Strips all diacritics / Tashkeel (`Fathah`, `Dammah`, `Kasrah`, `Sukun`, `Shaddah`, `Tanwin`, `Maddah`, `Superscript Alef`).
- Unifies Alef variants: `[إأآٱ]` $\to$ `ا`.
- Normalizes Ta Marbuta: `ة` $\to$ `ه`.
- Normalizes Alef Maqsurah: `ى` $\to$ `ي`.
- Removes Quranic pause marks, Sajdah signs, Rub el Hizb, and punctuation.

### 3.2 Sequence Aligner & Mistake Classifier (`src/aligner/diff.py`)
Computes the dynamic Levenshtein edit distance between the canonical Quranic token stream and user speech transcripts:
- **`WORD_MATCH`**: Token match. Advances cursor $N \to N+1$.
- **`MISSED_WORDS`**: User skipped expected tokens (omission). Triggers audio prompt if $\ge 2$ words skipped.
- **`INCORRECT_WORDS`**: User articulated a different Arabic word (substitution). Triggers teacher audio prompt.
- **`EXTRA_WORDS`**: User inserted words not in the canonical text (addition).
- **`PEEKED_WORDS`**: User tapped on a hidden word during Memorize Mode.

### 3.3 Audio Prompt Slicer (`src/audio/slicer.py`)
Extracts teacher prompt audio dynamically without pre-cutting audio files:
- Reads word-level millisecond timestamps from `data/timings/`.
- Extracts words $N$ to $N+2$ (configurable prompt length, default 3 words).
- Applies a **15ms cosine ramp lead-in** and a **25ms cosine ramp lead-out** to eliminate digital audio pops and clicks at chunk boundaries.
- Encodes output as 16kHz Mono WAV, converted to Base64 for instant WebSocket transport.

### 3.4 Speech Recognition Engine (`src/asr/engine.py`)
- Model: `tarteel-ai/whisper-base-ar-quran` (HuggingFace).
- Hardware: Automatically detects Apple Silicon Metal GPU (`mps`), CUDA GPU, or CPU fallback.
- Audio Ingestion: Accepts raw 16kHz 16-bit Mono PCM.

### 3.5 WebSocket Streaming Gateway (`src/server/ws_handler.py`)
Bidirectional protocol on `ws://<HOST>:8000/ws/recite`:
1. **Client sends `START_SESSION`**:
   ```json
   {
     "event": "START_STREAM",
     "surah": 1,
     "reciter": "mishari",
     "prompt_words": 3,
     "mode": "prompt",
     "start_ayah": 1
   }
   ```
2. **Client streams raw binary PCM**: 16kHz 16-bit mono chunks (~100ms frames = 3,200 bytes).
3. **Server sends alignment events**:
   - `WORD_MATCH`: `{ "event": "WORD_MATCH", "surah": 1, "ayah": 1, "word": 1, "text_uthmani": "بِسْمِ" }`
   - `PAUSE_MIC`: Signals client to mute mic before audio prompt plays.
   - `PLAY_PROMPT`: `{ "event": "PLAY_PROMPT", "prompt_text": "...", "audio_b64": "<base64_wav>" }`
   - `RESUME_MIC`: Signals client to un-mute mic after prompt finishes and 150ms echo drain elapses.
   - `BUZZER_ALERT` / `SILENT_HIGHLIGHT`: Sent when running in buzzer or silent feedback mode.
4. **Client sends `PROMPT_FINISHED`**: Sent after local audio playback completes. Server waits 150ms echo drain, then responds with `RESUME_MIC`.

---

## 4. Current Mobile App State & Deep UI Post-Mortem

### Why the User Rejected the Current UI
The user explicitly stated: *"the UI of this is very bad"*, following earlier feedback: *"the sora presentation is kinda wrong, and the font is also wrong"*, and *"why is there big black bars on top and bottom"*.

### Root Causes of the UI Failure:
1. **HTML-style Flexbox vs. Arabic Cursive Typography**:
   - In `mobile/App.js`, each Arabic word was wrapped in an individual `<TouchableOpacity>` with margins and padding inside a `flexWrap: 'wrap'` row.
   - In Arabic typography, words connect cursively and rely on delicate ligatures and baseline kerning. Breaking words into separate Flexbox blocks creates unnatural gaps, breaks kerning, causes disjointed line wraps on different screen sizes, and looks visibly amateurish.
2. **Over-Engineered "Cards Inside Cards"**:
   - The UI stacked an outer card, double illumination borders, inner borders, and nested banners, accompanied by developer-centric buttons ("Teacher Qari: Mishari / Husary", "Server IP Input", "Memorize Mode Switch").
   - This looks like an admin debugging dashboard rather than a serene, sacred Quran reading experience like **Ayah**, **Tarteel**, or **Quran.com**.
3. **Screen Real-Estate Waste**:
   - The bottom controls and stats consumed nearly half of the viewport, squeezing the Quranic text into a small scrollable window.

---

## 5. Architectural Blueprint for the UI Redesign

To achieve **Tarteel / Ayah-grade UI polish**, the next developer/agent should implement one of the following two proven architectural paths:

### Path A (Recommended): High-Resolution Scanned Page + Coordinate Bounding Box Overlays
This is the approach used by **Quran.com** and many production Quran apps:
1. **Display**: The screen renders the authentic high-resolution Medina Mushaf page (`page001.png`, `page002.png`, etc.) filling the viewport gracefully with natural margins.
2. **Highlight Overlays**: An absolute-positioned SVG / Canvas layer sits above the page image.
3. **Word Coordinates**: When a `WORD_MATCH` or `PLAY_PROMPT` event arrives, the app looks up the word's bounding box `[x, y, width, height]` (available from Quran.com open datasets) and renders a smooth, rounded translucent highlight (emerald green for matched, soft red for mistake, blue for teacher prompt).
4. **Advantages**:
   - 100% authentic King Fahd Complex calligraphy without font-rendering discrepancies across iOS/Android.
   - Zero Arabic text-shaping bugs or clipping.
   - Natural page flipping with fluid horizontal paging (`FlatList` with `pagingEnabled`).

### Path B: Shopify React Native Skia 2D Canvas (The Exact Tarteel Approach)
As discovered during reverse engineering of the Tarteel APK (`~/TARTEEL_RESEARCH.md` §1.7 & §2.2):
1. **Library**: `@shopify/react-native-skia`.
2. **Mechanism**: Instead of native React Native `<Text>` nodes, the Quran text is drawn on a GPU-accelerated Skia Canvas.
3. **Data**: Uses the pre-compiled `qpc_v1_layout` or `qpc_v4_layout` glyph coordinate tables to position each glyph at exact sub-pixel offsets.
4. **Advantages**:
   - Allows dynamic font scaling, dark/light theme color swaps, and custom diacritic coloration.
   - Ultra-smooth 60/120 FPS animations when words light up.

### Redesigned Component Hierarchy:
```
<ScreenContainer>
  ├── <MinimalTopBar>           # Transparent/blur: Surah name, Juz, Page number, theme toggle
  ├── <MushafPageView>          # Full-bleed page reader with horizontal paging (Pages 1 to 604)
  │     ├── <PageImage>         # High-res Medina Mushaf page scan
  │     └── <HighlightOverlay>  # Translucent word-level highlight bounding boxes
  └── <FloatingActionPill>      # Minimal floating bottom bar:
        ├── <ReciteMicButton>   # Large, elegant pulsing microphone button
        └── <QuickActions>      # Audio prompt mode toggle, Qari voice switcher, Memorize mode
```

---

## 6. How to Run the Environment

### 1. Python Virtual Environment & Backend
```bash
cd /Users/muhammad/quran-tutor
source .venv/bin/activate

# Run all automated tests
pytest tests/

# Launch the FastAPI backend server
python start.py
```
* Local host: `http://127.0.0.1:8000`
* Wi-Fi host (for phone): `http://192.168.19.137:8000`

### 2. React Native / Expo Dev Server
```bash
cd /Users/muhammad/quran-tutor/mobile

# Start Expo with cache cleared
npx expo start -c

# Run on booted iOS simulator
npx expo start --ios
```
* Metro bundler runs on `exp://192.168.19.137:8081`.
* Can be opened on any physical iPhone via the **Expo Go** app.

---

## 7. Immediate Action Items for Next Developer

1. **Clean Slate for `mobile/App.js`**:
   - Remove the clunky nested flexbox word boxes.
   - Implement the **Path A** architecture (Full-bleed high-res Mushaf page with word highlight overlays).
2. **Implement Minimalist Floating Controls**:
   - Redesign the bottom controls into a single floating circular microphone button that glows/pulses when listening, with settings accessible via a subtle slide-up sheet.
3. **Verify Audio Capture on Physical Device**:
   - Ensure `expo-av` streams 16kHz PCM chunks cleanly over the WebSocket when running inside Expo Go on iOS.
