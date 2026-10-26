# Madinah Mushaf asset sources

The reader uses native vector fonts, not raster page images or assets extracted
from the supplied Tarteel APK.

- Quran words and glyph mappings: Quran Foundation v4 public content API,
  `https://api.quran.com/api/v4/verses/by_page/{page}`.
- Page-specific QCF v2 font source:
  `https://static.qurancdn.com/fonts/quran/hafs/v2/woff2/p{page}.woff2`.
  Original Mushaf calligraphy/fonts: King Fahd Glorious Quran Printing Complex.
- `surah-names.woff2`: [open-quran-view surah-name-v4 font](https://github.com/adelpro/open-quran-view/blob/main/src/data/shared/surah-name-v4.woff2).
- `surah-frame.svg`: [open-quran-view ornamental frame](https://github.com/adelpro/open-quran-view/blob/main/src/data/assets/surah-frame-wikipedia.svg).

The open-quran-view repository declares MIT for its package. That declaration
alone does not establish the redistribution terms of each upstream font or
ornament; retain their attribution and confirm asset-specific terms before a
public release.

Preparation keeps the page-font outlines and font names, subsets to used glyphs,
and supplies a blank space glyph where needed to prevent platform fallback.
The ornamental SVG is converted to a native font outline by
`scripts/prepare_madani_headers.py`.

## Layout corrections

The app groups words by their own print-page/line metadata, rather than the
verse endpoint's page boundaries. This prevents 56 missing ayah endings found
in the reference library's bundled data.

Eighteen surah headers belong to the previous page's final line. For example,
An-Nisa's header is on page 76 and its basmalah is on page 77. The preparation
script preserves that layout. Reference scans used only for comparison:
[page 76](https://equran.me/page-img-76.html) and
[page 77](https://equran.me/page-img-77.html).

The API places 84:21's end marker before its final words. The downloader keeps
end markers after their last word; the shipped data includes this correction.

Run `.venv/bin/python scripts/check_madani.py` from the project root to verify
all 604 pages, 6,236 ayahs, 114 headers, word order, font coverage and advances.
These checks do not replace native visual comparison.
