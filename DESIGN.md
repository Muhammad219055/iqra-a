# Quran Tutor reader

The page is the primary surface. The supplied Ayah/Tarteel references define
its visual world: native QCF v2 glyphs, printed Madinah line breaks, quiet gold
ornaments, and no raster Mushaf pages.

## Full-screen reading

Start with the app controls hidden. The printed metadata row remains: surah at
left, page number centered, and juz at right. A deliberate tap reveals an edge-attached
Liquid Glass top navigation strip and bottom control shelf. Both sit above the page and
fade over 140 ms; they never change its dimensions or font size. The bottom shelf
contains memorization, page navigation/jump, and one microphone action. Session
messages appear only when needed. Keep the app controls distinct from printed
ayah markers.

Use native right-to-left page snapping. Commit selection from the native pager
event, never before starting a scroll. Long navigation jumps are immediate;
adjacent turns animate natively. Do not interrupt an active native drag with a
page-button command. Only current and adjacent pages render glyph content.

## Deliberate touch

Ordinary reading words have no individual tap action. Page taps fail after
8 points of movement. In memorization mode, a short press reveals a word;
movement beyond 8 points cancels it. The word recognizer takes precedence over
the page tap, so revealing a word does not also toggle the controls. Hidden
words render no glyph; positions and ayah markers remain intact. Accessibility
activation offers the same reveal action.

## Panels and appearance

The left drawer translates horizontally. Settings rise vertically. Their
backdrops fade independently and stay stationary. The panel heading can be
dragged to dismiss using velocity or distance. Transforms/opacity run on the UI
thread, with reduced-motion support. Modal safe-area providers keep titles
clear of the status bar.

Day uses paper #FFF9EF and ink #25251F. Night uses pure black #000000 and pure
white #FFFFFF for Quran text and ayah markers. The surah ornament gold is also the interaction accent in each appearance;
there is no unrelated teal accent. Apply the palette to panels,
inputs, feedback and the status bar. Save appearance locally.

## Verification and product limits

Component checks cover native pager selection, drag guards, constant page
geometry, touch thresholds, glyph omission and theme persistence. Native XCTest
and screenshots live in docs/ui-verification/. Earlier evidence describes the
superseded layout; consult HANDOFF.md for the current run.

A full 604-page visual comparison and release-build motion measurement on a
physical device have not been completed. Local ASR, live PCM inference and
spoken correction are unfinished; docs/ON_DEVICE_LISTENING.md defines the next
native implementation slice. The microphone must not suggest those are ready.
