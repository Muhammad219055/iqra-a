# Claude now owns the takeover

User transferred the remaining work to Claude. Start with
`docs/CLAUDE_TAKEOVER.md`; it supersedes earlier agent ownership splits and
collects engine state, REA findings, testing, signing and next steps.

# Current checkpoint — installed offline engine; Tarteel review

22 October 2026: native engine and Expo bridge are integrated; signed Release
Quran Tutor (`com.mki15.qurantutor`) installed and launched on the paired iPhone.
Signing account mki_15@outlook.com, verified Personal Team GUY9JCSF5U.
Ten muted native tests pass (`on-device/evidence/vad-gate.xcresult`); bundled
Whisper/Silero and local prompts require no recognition server. Al-Fatihah only.
The user tested recognition: it works but is inaccurate and unlike Tarteel.
Do not describe phone accuracy, calibration or continuous listening as verified.

Requested APK re-review completed: see `docs/TARTEEL_LISTENING_REVIEW.md` for REA
evidence IDs and Hermes function offsets. Tarteel's examined path streams to its
voice service with Quran range context, interim results and server word-state
updates. Ours stops capture and decodes a final chunk. Continuous local capture,
stable progress and cautious corrections are the next engine slice; not yet built.
The production server model cannot be recovered from this client APK.

Claude owns UI and the Remain crash investigation; do not touch Remain.
Keep automated audio tests muted. Earlier checkpoints below are historical and
their claims of a missing Expo bridge or uninstalled app are superseded.

# Historical checkpoint — Codex owns on-device ASR; Claude owns UI

2026-10-22 update: native listening lab now implements microphone PCM capture,
silence endpointing, incremental word alignment, bundled word/next-ayah playback,
request cancellation and stale-result suppression. Al-Fatihah text/audio only.
Final muted simulator run: 9 tests PASS, zero failures
(`on-device/evidence/listening-muted.xcresult`, log alongside). Updated unsigned
iPhone build PASS (`listening-device-build.log`). Real microphone and physical
phone airplane-mode/calibration/performance remain unverified; Expo bridge is
not yet implemented. Automated playback now uses volume 0; production lab uses
normal playback volume. No mobile UI files changed during this engine work.

User asked to include Claude in model work too. Give Claude the disjoint task in
`docs/CLAUDE_MODEL_EVALUATION_HANDOFF.md`: own `on-device/evaluation/` only,
measure native CLI recognition/mistake reliability, keep all tests silent.
Codex retains native engine/capture/playback and integration ownership.

Native ASR milestone saved 2026-10-21: `on-device/README.md` has reproducible
steps and API boundary. Pinned Quran Whisper converted to 147,951,465-byte F16
GGML. Native iOS 27 simulator exact-transcript tests PASS (2 tests); omission
fixture preserves missing الرحمن. Unsigned physical-iPhone build PASS. Evidence:
`on-device/evidence/verification.json`, native `.xcresult` bundles remain local.
No `mobile/` files changed during this engine slice. Next: live capture, stable
alignment, local spoken prompts, Expo bridge, physical-phone airplane-mode and
performance checks. Current harness has tests plus a label, no recording UI.

User explicitly assigned Codex the on-device model and Claude the UI. Claude UI
handoff: docs/CLAUDE_UI_HANDOFF.md. Current UI native tests are NOT passing; older
PASS evidence is superseded. Do not edit mobile/ while Claude works there. Codex
will isolate the engine prototype under on-device/. See docs/ON_DEVICE_LISTENING.md.

---

# Resumed after restart — iOS 27 reader verification (2026-10-21)

This supersedes the paused checkpoint below. User returned and authorized continuing.

- Native XCTest on iPhone 18 Pro / iOS 27.0 PASSED: 1 test, zero failures, 101.757 seconds. Passing log saved as `docs/ui-verification/evidence-2026-10-21/reader-passed.log`.
- Verified native next/previous buttons, RIGHT swipe next / LEFT swipe previous, tap to hide/restore chrome, left drawer bounds, Juz 2 -> page22, invalid605 rejection, page604/end bounds, hidden-word hit targets, settings.
- Native screenshot review found drawer title/status-bar overlap. Added a SafeAreaProvider inside each Modal; drawer now has correct top inset. Settings use only bottom/side safe edges to avoid excess top spacing.
- RN0.88 backdrop uses StyleSheet.absoluteFill. Full stationary dim overlay is visible in native screenshots.
- Added explicit button accessibility role to Go to page. Improved XCTest to query grouped chapter accessibility label, clear existing page input, wait for hittable controls/modal dismissal, and tap visible hidden words rather than offscreen preloaded pages.
- FINAL re-run after settings inset adjustment and stronger visible-word peek assertion PASSED: 1 test, zero failures, 170.777 seconds. Result `/private/tmp/quran-ios27-ui/reader-final.xcresult`; final log and eight screenshots saved in the evidence directory. Native screenshot review confirms whole ayah markers, removed word glyphs, contained short-surah titles, correct drawer safe area, and compact settings spacing. The earlier immediate memorization screenshot caught an intermediate render; the final capture waits for hidden-word state and is correct.
- Screenshots: `docs/ui-verification/evidence-2026-10-21/{page-001,page-002,page-003,page-604,reading-focus,navigation-drawer,memorize,settings}.png`. These are evidence only, never bundled reader assets. Blue floating gear is Expo Go's development control, not our UI.
- Added root DESIGN.md and docs/ui-verification/README.md. Component checks and full data/font validator still PASS; git diff --check PASS.
- Metro currently running IPv4 localhost port8081 (session93020). Simulator booted `830C6FCA-5642-40A2-AA5D-DCAC71EEB441`. Xcode-generated test harness recreated in `/private/tmp/quran-ios27-ui` after restart cleared tmp.
- No standalone release-build/physical-device audio verification. On-device ASR and PCM streaming remain unimplemented. Full-edition dot-perfect visual comparison is not yet proved; do not equate completeness validator with facsimile proof.

---

# STOPPED for user computer restart — 2026-10-21 (latest checkpoint)

User explicitly asked to save and stop for restart. Resume the same task after they return. All code is saved on disk, no commit made. This checkpoint overrides obsolete license/setup notes below.

## iOS 27 migration completed
- Xcode 27.1 build 27A9275 installed; license accepted. iOS 27.0 simulator boots, Expo Go SDK 58 installed.
- Active app is `mobile/`; root `ios/` is an older separate Swift prototype. Do NOT prebuild over root ios.
- Expo 58.0.16, React 19.3.0, RN 0.88.0. Installed matching Expo asset/font/audio/splash/status-bar and safe-area packages, explicit babel-preset-expo. expo-av removed, App.js migrated to expo-audio recording/player APIs with cancellation guards.
- Legacy splash config replaced with expo-splash-screen plugin; obsolete newArchEnabled removed. Root SafeAreaProvider and scene-aware safe area widths installed.
- Rollback source/package copies are in `.compat-backup/sdk52/mobile/` (ignored).
- Expo doctor: 20/20 PASS. iOS export PASS (`/private/tmp/quran-ios27-export`). Reader behavior checks PASS (`cd mobile && npm run check:reader`). Full font/data check PASS (`.venv/bin/python scripts/check_madani.py`): 604 pages, 6236 ayahs, 114 headers, 83665 word/marker glyphs. `git diff --check` PASS.

## Actual simulator findings (do not oversell)
- Native vector reader LAUNCHED on iOS 27.0 and first page visually inspected. Native settings also captured.
- Durable screenshots and test logs: `docs/ui-verification/evidence-2026-10-21/`. Screenshots are verification evidence ONLY, not app/raster Mushaf assets.
- Expo --localhost initially bound ::1 but advertised 127.0.0.1. Fixed server command: `NODE_OPTIONS=--dns-result-order=ipv4first npx expo start --localhost --port 8081` from mobile. Confirmed IPv4 listener and status response. Need escalation for simulator/network commands when sandbox blocks.
- Found RN 0.88 REMOVED StyleSheet.absoluteFillObject. Replaced backdrop with StyleSheet.absoluteFill; added assertion for all four edges. Component check passes; backdrop fix still needs native visual re-check.
- Native XCTest has NOT passed. First run failed because XCUITest computed {-1,-1} hit point for Next page, opening settings instead. Diagnostic rerun launched Expo Go Home rather than reader. Tests now open recent Quran Tutor if Home and close any existing panel first.
- Latest serial retry interrupted for user restart; Xcode emitted simulator service-hub errors. No physical swipe or full native geometry verification yet.
- Use `-parallel-testing-enabled NO` to avoid Expo Go simulator clone issues. Original test project is `docs/ui-verification/`; generated project lives `/private/tmp/quran-ios27-ui`. Rebuild after restart if needed with xcodegen.
- Simulator UDID: iPhone 18 Pro iOS 27.0 `830C6FCA-5642-40A2-AA5D-DCAC71EEB441`.

## Next work
1. Start simulator + IPv4 Metro, open exp://127.0.0.1:8081. Recheck dim overlay after absoluteFill fix.
2. Fix test harness targeting/hit point issue using actual accessibility frames; verify next/previous buttons AND swipe RIGHT next / LEFT previous. Inspect pages 2/3/604, drawer/Juz, title containment, settings, focus-mode resize, memorize/peek. Existing component tests are not native proof.
3. Complete native audio migration smoke check. Local ASR/live PCM streaming and next-word/ayah spoken assistance remain UNIMPLEMENTED; do not claim working recitation tutor.
4. Finish UI review and DESIGN.md per .impeccable surface contract. Exact print-layout visual verification still outstanding; do not claim dot-perfect yet.

---

# User feedback implemented while Xcode setup is pending

Latest user correction overrides the older direction note: **swipe RIGHT = next page, swipe LEFT = previous**. `FlatList` is now inverted, and next/previous chevrons are on the corresponding book edges. Update physical gesture verification accordingly.

Changes in mobile/MushafReader.js:
- Left navigation drawer with Surahs and Juz tabs, all 30 juz and page jumps.
- Both drawer and settings use native Modal fade (no translating background overlay). Reduced motion is instant.
- Surah lettering fitted into explicit vector-frame bounds; top chapter label and drawer Arabic names constrained.
- Page/juz numerals use system text rather than the Quran font that renders digits in ayah ornaments.
- Tap the reading page to hide/restore header and footer controls. Line grid now fills the available height. Memorization word taps still peek without toggling chrome.
- Hidden words now render **no glyph Text at all**: only invisible accessible tap areas preserve word positions. Removed the colored masking backgrounds. Verse markers remain visible.

Added `mobile/scripts/check-reader.cjs` (`cd mobile && npm run check:reader`). Component-state checks PASS for hidden glyph removal/peek, chrome toggle, drawer/Juz navigation, page direction configuration and stationary fade-modal configuration. This uses native component mocks and does NOT prove native geometry, touch arbitration, physical swipe direction or motion appearance.

Updated docs/ui-verification/Tests/ReaderTests.swift to exercise reversed swipes, chrome hiding/restoration, drawer bounds and Juz 2 navigation. It still needs to run after the user completes Xcode license/setup. Do not re-ask while they are working on it. The user said they are handling it.

---

# Latest resume checkpoint — 2026-10-21

- Resumed after the macOS update. Xcode/simulator now refuse commands because the Xcode license has not been accepted. Asked the user to open Xcode and accept its setup/license, or run `sudo xcodebuild -license`. Do not accept legal terms on the user's behalf. Await their reply, then resume native verification.
- Metro was started again on port 8081. iOS JavaScript bundle compiled successfully to /private/tmp/quran-ios-resume.bundle and passed Node syntax checking via stdin. Babel transforms also pass; git diff --check passes.
- Added `scripts/check_madani.py`. PASS: 604 pages, 6,236 ayahs, 114 headers, 83,665 word/marker glyphs; no missing/duplicate/reordered words; each glyph exists in its matching font and each stored advance matches that font.
- IMPORTANT CORRECTION to earlier assumptions below: the 18 row-0 surah headers belong on the PREVIOUS page's line 15. Verified against printed reference pages 76/77. Fixed `prepare_madani.py` and shipped madani.json. There are now no extra header rows. Surah navigation finds the first actual word, so An-Nisa opens page 77 rather than its title on page 76.
- Corrected API end-marker ordering for 84:21: it was wrongly on line 13 ahead of words on line 14. Fixed both saved datasets and the downloader. The full validator now passes.
- Saved source provenance in data/madani-sources/README.md. Header SVG/WOFF2 source files are durable in that directory.
- Prepared UI test project was built at /private/tmp/quran-ui-resume. Test launch failed before exercising the app (test runner NotFound; Expo launch also timed out). Later simctl commands explicitly reported unaccepted Xcode license. No NEW-reader screenshot has been inspected yet. Do not report the UI as visually verified.
- Other Android builds were heavily loading the Mac; left them untouched.

---

# Resume here — Codex UI work paused for macOS update (2026-10-21)

User explicitly requested a pause to update macOS. Resume the same UI task; do not restart discovery.

## User requirements (override the older handoff below)

- The reader must be **identical to the 15-line Madinah Mushaf**, not a general Uthmanic-font approximation.
- **No PNG/raster Mushaf pages.** Render native vector glyphs, including verse markers, headers and basmalah.
- User supplied Ayah and Tarteel screenshots; both have essentially the same canonical reader. They authorized choosing whichever implementation best matches it.
- Horizontal paging, no vertical reader scroll. Per earlier handoff: swipe left = next page; swipe right = previous.
- Long-term product: free, fully on-phone ASR and spoken next-ayah/mistaken-word assistance. This is NOT complete in the current app.
- Apply the user's requested visual-design-fundamentals, interaction-design-principles, premium-design-craft, animate, and Impeccable skills. The existing screenshot references define the visual world; do not start a new style tournament.

## Final checkpoint before restart

- Native font/data generation completed successfully: `Prepared 604 pages and matching native fonts.`
- `mobile/assets/data/madani.json` (about 10 MB) and `mobile/madaniFonts.js` are saved. All glyph-coverage and 6,236-ending assertions passed. No regeneration is required merely to resume UI verification.
- Metro was stopped cleanly. Start it again after the macOS update.
- REA session was closed.
- No new-reader simulator verification or UI tests have run yet.

## Files saved

- `mobile/MushafReader.js`: new native vector reader; horizontal FlatList, measured glyph advances, page controls, surah search, page jump, memorize/peek, recitation sheet, reduced-motion handling.
- `mobile/App.js`: connects the new reader to existing settings/events; old vertical layout removed. Existing audio implementation largely preserved. A truthful status now identifies that live audio streaming is not connected.
- `mobile/app.json`: light appearance and matching paper splash.
- `mobile/package.json` and lock: @expo/vector-icons 14.0.4 explicitly declared (already installed through Expo).
- `scripts/download_mushaf.py`: downloads all public Quran Foundation word text, QCF v2 glyphs and line metadata, then groups by WORD page rather than verse endpoint page.
- `mobile/assets/data/mushaf.json`: full intermediate source bundle, 604 pages, all 6,236 ayah endings. Saved; no need to download again.
- `scripts/prepare_madani.py`: prepares page-specific TTF subsets and hmtx advance metadata. Source fonts from `https://static.qurancdn.com/fonts/quran/hafs/v2/woff2/p{page}.woff2`.
- `mobile/assets/fonts/madani/`: all 604 native page font files plus SurahNames.ttf and SurahFrame.ttf. Latest regeneration may still have been in progress at pause; see status below.
- `scripts/prepare_madani_headers.py` + `data/madani-sources/`: header lettering and frame saved durably; frame SVG converted to a native TTF outline, no SVG runtime dependency and no raster page.
- `docs/ui-verification/`: prepared XcodeGen/XCTest external-app UI runner. NOT executed yet. It activates Expo Go, tests navigation, invalid page input, page 604, memorization, settings, and captures attachments.

## Important findings

1. **Do not trust the old backend/mobile completeness claims.** Mobile uses expo-av file recording and does not send PCM chunks to the WebSocket. The native Swift client has separate PCM capture, but neither client has an integrated on-device ASR engine. Do not claim local-server inference means phone-local inference.
2. **Open-source reference data has missing verses.** `adelpro/open-quran-view` was inspected. Its bundled QCF v2 pages omit 56 ayah endings (6,180 instead of 6,236), because verse endpoint pagination and glyph page boundaries differ. Our script corrected this by assigning each word to its own page; do NOT revert to that library's page JSON.
3. QCF v2 fonts have word glyphs, occasionally multiple glyphs with spaces. Most omit an actual space glyph. The preparation script adds a blank quarter-em space to prevent platform-font fallback inside those strings; validate exact spacing on screen.
4. Some chapter starts have Quran text starting at line 2, with basmalah on line 1 and a header above the numbered grid (header row 0). Reader computes row count and reserves the extra header row instead of overwriting text.
5. Each page's glyph outlines and advance widths come from its matching QCF v2 font. No inferred character-count font sizing. The current renderer still needs native visual comparison, including negative side bearings and diacritics.
6. The header frame/name font files are from open-quran-view public assets. Add durable source attribution/license notes before shipping. Repo declares MIT, but confirm font/ornament asset terms separately.

## Verification status and next steps

- Babel transform passed for App.js and MushafReader.js.
- Full intermediate dataset passed count checks for 604 pages and 6,236 verse endings.
- Native visual verification of the NEW reader has NOT happened. Last simulator screenshot still showed the old cached app.
- Final `madani.json` / `madaniFonts.js` generation was running while pause was requested. Check their existence. If missing, run `.venv/bin/python scripts/prepare_madani.py` (source intermediate is saved). It checks every glyph against its matching font and 6,236 endings before writing both files. Font cache in /private/tmp/quran-tutor-qcf2 may or may not survive macOS restart; it can redownload.
- Then run `.venv/bin/python scripts/prepare_madani_headers.py` if needed.
- Start Metro: `cd mobile && npx expo start --localhost --port 8081`. Sandbox prevents port binding; tool escalation was necessary.
- Simulator: iPhone 17 Pro `CB15493B-AB98-4693-B18E-1123247CEF83` (iOS 26.1), Expo Go bundle `host.exp.Exponent`.
- Reload fresh: terminate Expo Go if needed, then `xcrun simctl openurl booted exp://127.0.0.1:8081`.
- Simulator operations and localhost curl require escalation in this environment. Lack of sandbox localhost access is not proof Metro is down.
- GUI Simulator had no accessible front window even after `open -a Simulator`; use the prepared XCTest runner for taps/screenshots if necessary. `xcodegen` and `cliclick` are installed.
- Review opening pages 1/2, dense page 3, page 77 (extra header row), page 604 (three headers), word masks, settings, font load/error states, and phone/tablet fit.
- Fix App.js connection cancellation/cleanup edge cases and unused state/comments as needed. Do not add a new ASR architecture during this UI task.
- Remove unused `opening` variable in MushafReader.js, check screenshot typography and masks; the current mask uses full-height word backgrounds and may need thinner bars while preserving positions.
- Add meaningful source-data validation (all verse keys exactly once, all 114 chapter headers, all word IDs exactly once, glyph coverage, line counts).
- Finish Impeccable review/documentation once actual simulator evidence exists; DESIGN.md not yet written. Do not call it pixel-perfect without comparison evidence.

No commits were made. Existing user/Gemini changes (including deleted PNGs and older HANDOFF modifications) were preserved.

---

# Previous Gemini handoff (historical; completeness claims unverified)

# Master Handoff: Quran Recitation & Memorization Tutor

## 1. Executive Summary & Current State

This project is a **local-first, open-source Quran recitation tutor** inspired by **Tarteel** and **Ayah**.
- **Backend (`src/`):** **100% COMPLETE & TESTED.** Local Whisper ASR fine-tuned on Quranic Arabic (`tarteel-ai/whisper-base-ar-quran`), WebSocket streaming gateway (`/ws/recite`), Levenshtein sequence alignment, hesitation detection (>2.5s), cosine-windowed audio prompt slicer in Mishari/Husary voices, and SQLite persistence. All pytest test suites pass.
- **Mobile Client (`mobile/`):** React Native Expo app running on iOS simulator (iPhone 17 Pro).
  - Audio permissions, 16kHz PCM recording, and WebSocket streaming to the backend are functional.
  - Official King Fahd Uthmanic font (`assets/fonts/UthmanicHafs.ttf`) is bundled and loading properly.
  - Floating green microphone FAB with pulsing listening state is implemented.
  - Tutor settings sheet (server IP, Qari voice, mistake mode) is implemented.

---

## 2. Critical UI Issues & What Failed (Read This Before Coding)

The user was strongly dissatisfied with previous iterations due to two major flaws:

### Flaw 1: Static PNG Page Images (Borderline Wrong)
- Previous agents tried loading static scanned PNG images of Mushaf pages with pixel-coordinate overlays.
- **Why this failed:** Scanned pages have a fixed 1:1.62 aspect ratio, causing harsh black/white letterbox bars on modern phones (~9:19.5). Bounding boxes misaligned, text was blurry on Retina, and it was not a true native reader.

### Flaw 2: Vertical Scroll & Lack of Horizontal Page Navigation (The Current Defect)
- The latest agent attempted native typography, but placed the text inside a standard **vertical `ScrollView`**.
- **User feedback:** *"why would there by vertical scroll????? I cannot go front or back"*.
- **The Core Rule:** A Mushaf is a **physical book**, NOT a vertical website. Quran apps like **Ayah** and **Tarteel (Mushaf Mode)** strictly use **horizontal page-by-page turning**:
  - **Zero vertical scroll:** Each Mushaf page must fit comfortably within the screen viewport.
  - **Horizontal Pagination / Page Flip:** The user must be able to flip between pages (Page 1, Page 2, Page 3, ...).
  - **RTL Book Physics:**
    - Swiping **Right to Left (`←`)** turns to the **Next Page** (Page 1 ➔ Page 2).
    - Swiping **Left to Right (`→`)** turns to the **Previous Page** (Page 2 ➔ Page 1).
    - Top header or swipe gestures must allow easy page navigation.

---

## 3. Exact Architecture Requirements for the Next Agent

### A. Horizontal Paginated Mushaf Reader
1. **Container:** Implement horizontal paging (e.g. `FlatList` with `horizontal={true}`, `pagingEnabled={true}`, `inverted={true}` or explicit gesture-driven RTL page state).
2. **Viewport Fitting:** Each page must render as a single discrete page container that fits within the viewport between the top bar and the bottom floating dock—**no vertical scrolling**.
3. **Data per Page:**
   - Page 1: Surah Al-Fatiha (Ayahs 1–7) with Surah header banner and calligraphic Bismillah.
   - Page 2: Surah Al-Baqarah (Ayahs 1–5) with Surah header banner and Bismillah.
   - Page 3+: Subsequent pages.
4. **Typography:**
   - Use `fontFamily: 'UthmanicHafs'` (`assets/fonts/UthmanicHafs.ttf`).
   - Line-height and font-size tuned so that all 15 lines (or Page 1's 7 ayahs) fit cleanly without clipping Arabic diacritics (*tashkeel*, *maddah*, *sukun*).
   - Ayah end rosettes (`۝` with embedded Arabic numeral) placed inline at verse ends.

### B. Live Recitation Feedback & Word States
Wire the incoming WebSocket events to the words on the active page:
- **`'normal'`**: Warm charcoal ink (`#1C1917`).
- **`'matched'`**: Soft emerald green pill (`#D1FAE5` background, `#047857` text).
- **`'mistake'`**: Soft crimson pill (`#FEE2E2` background, `#B91C1C` text).
- **`'prompted'`**: Royal blue pill (`#DBEAFE` background, `#1D4ED8` text).
- **`'hidden'` (Memorize Mode)**: Word is masked/hidden until recited or tapped to peek.

### C. Controls & Chrome (Ayah / Tarteel Minimal Style)
- **Top Bar:** Page number (`الصَّفْحَة ١`), Juz indicator (`الجُزْءُ الأَوَّل`), and Settings button.
- **Bottom Dock:**
  - Floating circular emerald green microphone button (`#059669`).
  - Active pulsing ring (`#DC2626`) during recording.
  - Single-line status text ("Listening...", "✓ [Word]", "⚠ [Mistake]").
- **Settings Sheet:** Slide-up modal for Server IP, Qari voice, and feedback mode (already written in `mobile/App.js`).

---

## 4. Repository Manifest & Key Commands

### Backend
- **Start server:**
  ```bash
  /Users/muhammad/quran-tutor/.venv/bin/python /Users/muhammad/quran-tutor/start.py
  ```
  Runs on `0.0.0.0:8000` with WebSocket at `ws://<host>:8000/ws/recite`.
- **Run tests:**
  ```bash
  /Users/muhammad/quran-tutor/.venv/bin/pytest tests/
  ```

### Mobile App (`mobile/`)
- **Directory:** `/Users/muhammad/quran-tutor/mobile`
- **Main file:** `mobile/App.js`
- **Start Metro:**
  ```bash
  cd /Users/muhammad/quran-tutor/mobile && npx expo start --ios
  ```
- **Simulator Device:** iPhone 17 Pro (`CB15493B-AB98-4693-B18E-1123247CEF83`).
- **Open URL in simulator:**
  ```bash
  xcrun simctl openurl CB15493B-AB98-4693-B18E-1123247CEF83 "exp://127.0.0.1:8081"
  ```
- **Take simulator screenshot:**
  ```bash
  xcrun simctl io CB15493B-AB98-4693-B18E-1123247CEF83 screenshot /tmp/sim.png
  ```
