# Product

Quran Tutor is a free, phone-local Quran recitation and memorization tutor.

The reader is a 604-page, 15-line Madinah Mushaf rendered with native QCF v2
vector glyphs. Raster page images are not used. The default is full-screen:
printed surah, page number and juz remain visible; a tap reveals edge-attached native Liquid Glass
controls at the top and bottom without changing the page geometry.
Ordinary words have no individual tap actions. Memorization removes glyphs and
uses a short press with a movement threshold to reveal a word. Day and night appearances cover
both the reader and panels, with the user's choice saved locally.

Motion should explain the component: native right-to-left page snapping,
horizontal drawer movement and vertical settings-sheet movement. Backdrops fade
independently. Reduced motion removes translation.

Listening is unfinished. The current mobile experiment uses a development
WebSocket; Python runs the existing Quran Whisper model on the Mac. This is not
the intended product architecture. The next implementation milestone is offline
native inference, documented in docs/ON_DEVICE_LISTENING.md. Do not advertise
working on-device recognition or tajweed assessment until measured on a phone.

The supplied Ayah and Tarteel reader references define the visual direction:
quiet paper and ink, clear Arabic, restrained gold print accents, one gold-accent
microphone. User corrections override older handoff notes and prototype choices.
