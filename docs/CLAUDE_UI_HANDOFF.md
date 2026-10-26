# Claude owns UI; Codex owns on-device speech

User changed the split: finish reader UI in `mobile/`; Codex is building the
speech engine separately in `on-device/`. Do not modify on-device/. Current work
is uncommitted; do not reset/stash/overwrite it. Root `ios/` is an older separate
Swift prototype, not the active Expo app. Do not prebuild over it.

## Current user requirements

- Exact 604-page 15-line Madinah reader with native QCF2 vector glyphs. NO raster
  Mushaf pages. Preserve data/fonts/preparation scripts and word geometry.
- Default full-screen reading; show top/bottom controls on a deliberate tap as
  overlays. Never resize/reflow the page when controls appear/disappear.
- Native RTL paging: swipe RIGHT next, LEFT previous. Fix interrupted/partial
  page transitions and rapid input. Current PagerView replaces inverted FlatList.
- Quick PRESS to reveal memorization words, not hold. Cancel presses after
  8-point movement. Normal reading words have no per-word actions. Hidden words
  render no glyph Text; retain positions and ayah markers.
- Pure black night background and pure white Quran text/markers. Accent is the
  surah ornament gold in BOTH modes; no teal. Appearance saved with AsyncStorage.
- User disliked two outlined floating pills. Current top and bottom controls are
  edge-attached native Liquid Glass, with solid fallback. Refine taste as needed.
- Left drawer translates horizontally; settings sheet vertically. Backdrops
  fade separately and never translate. Reduced-motion support required.
- Native page scrubber at bottom, preview page/surah while dragging; commit page
  change only on release. Slider direction RTL (1 right, 604 left).
- Haptics for controls, page turns, reveal, slider surah-boundary ticks (100ms
  minimum spacing), release confirmation and drag dismissal. Do not buzz from
  renders or canceled gestures. Simulator cannot verify physical feel.
- Latest user explicitly requires STATUS BAR HIDDEN in read mode, restored when
  chrome opens. Keep geometry fixed. This still needs native verification.
- Surah/juz metadata became tiny when constrained by percentage maxWidth and
  adjustsFontSizeToFit. Latest patch restores explicit widths and fixed 14pt
  labels in a slim row below the system bar; page number centered. User had
  proposed safe-area side spaces, but clock/island conflicts remain. Use judgment,
  do not shrink labels or overlay the system indicators.

## Implementation and checks

`mobile/MushafReader.js` holds Page, native IntentButton/WordTarget, animated
Sheet, PageScrubber and theme provider. Installed Expo 58.0.16 / RN0.88 / React19.3
plus matched PagerView9.0.7, Gesture Handler3.3, Reanimated4.7.1 / Worklets0.13,
AsyncStorage, expo-glass-effect, Slider, expo-haptics. These are installed.
App.js retains the old server experiment; do not claim on-device ASR works.

`npm --prefix mobile run check:reader` PASS with mocked native/state checks.
`git diff --check` PASS. iOS export passed before the latest slider/haptics
changes. Expo Doctor was 20/20 before those two additions. Full dataset/font
validator passed (604 pages / 6236 ayahs / 114 headers / 83665 glyphs).

Native tests are NOT green for the current UI. Earlier checkpoint PASS belongs
to superseded layout. Latest tests in docs/ui-verification/Tests/ReaderTests.swift
have been failing as implementation and user manual interactions change. Do NOT
claim current native verification passed. Last logs: /private/tmp/quran-ios27-ui/
{glass-gutter,scrubber}.log. Failures include controls not responding after modal
dismissal, appearance option missing, and page-button progression. Investigate.

Important findings:
- Core RN Pressable sometimes missed taps inside transformed panels while the
  page field had focus. Native Gesture.Tap IntentButton fixed the focused Go
  validation test. Latest patch switched all controls to this shared native tap.
- Explicit worklet directives were added to gesture callbacks; verify no runtime
  warnings remain. Gesture Handler v3 still exports the legacy Gesture builder.
- Tests must tap the page margin (x=.02), not center, for chrome in memorize mode.
  Center taps legitimately reveal a word. Scope hidden targets to current page
  (neighbor pages are mounted and native AX may call them hittable).
- Native PagerView child views need width/height 100%, not flex:1. Only current
  and adjacent pages render glyphs. Do not eagerly load 604 page fonts.
- StatusBar RN calls in SDK58 use deprecated UIApplication status-bar API.
  Expo Go plist UIViewControllerBasedStatusBarAppearance=false. Latest component
  again passes hidden={!chromeVisible}; actual hiding is unverified. expo-status-bar
  wraps the same RN API, so switching imports alone will not solve native issues.
- Last haptics patch is unverified natively; all Promise failures are nonfatal.

## Running

Metro is running session27556 / IPv4 localhost8081. Start command from mobile:
`NODE_OPTIONS=--dns-result-order=ipv4first npx expo start --localhost --port 8081 --clear`.
Expo Go SDK58 installed; iPhone18Pro iOS27.0 UDID
830C6FCA-5642-40A2-AA5D-DCAC71EEB441 is booted.

Native test harness source docs/ui-verification/, generated project
/private/tmp/quran-ios27-ui/QuranUICheck.xcodeproj. Copy updated Tests before run;
use -parallel-testing-enabled NO and a fresh resultBundlePath. Xcode27.1 installed.
Do not accept Apple legal terms on the user's behalf if asked again.

Design references: user supplied Ayah/Tarteel reader and open/closed chrome
screenshots. See DESIGN.md and PRODUCT.md, but latest user corrections win.
Existing evidence under docs/ui-verification/ is historical unless labeled with
an actual new passing run. Blue floating gear is Expo Go's dev control, not UI.
