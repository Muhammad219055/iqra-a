# Native reader verification

The test host drives Quran Tutor inside Expo Go. It does not replace a standalone
release build or physical-device microphone testing.

Start Metro from `mobile/` with:

```sh
NODE_OPTIONS=--dns-result-order=ipv4first npx expo start --localhost --port 8081
```

Boot the iPhone 18 Pro iOS 27.0 simulator and open `exp://127.0.0.1:8081`.
The simulator identifier used here is `830C6FCA-5642-40A2-AA5D-DCAC71EEB441`.
Generate the Xcode project with XcodeGen in a temporary copy of this directory
(copy `Host`, `Tests`, and `project.yml`; omit the evidence directory).

Run the QuranUICheck scheme with `xcodebuild test`, the simulator destination,
a temporary derived-data path, a fresh result bundle path, and
`-parallel-testing-enabled NO`. Disabling parallel testing keeps Expo Go on the
same simulator instead of launching a separate clone without the reader open.

The test resets to page 1, checks the opening pages, left/right gestures,
focus-mode toggling, drawer bounds, Juz navigation, invalid page rejection,
page 604, memorization peeking, and settings. Page assertions use the chapter
button's accessible label because its child metadata is grouped by iOS.
Modal dismissal must complete before testing a control behind it.

Screenshots under `evidence-2026-10-21/` are test evidence, never application
assets. Earlier diagnostic logs record unsuccessful runs; consult the latest
checkpoint in HANDOFF.md for the actual verification status.

The current reader starts with chrome hidden. The test taps the page to reveal
controls, checks that showing/hiding them preserves the page frame, and uses
a quick press to reveal a visible memorization word. It also selects Night.
The new pager is native PagerView; only three neighboring pages render glyphs.
The control material is native Liquid Glass where available. Current colors and
interaction requirements are in DESIGN.md; earlier screenshots show superseded UI.
