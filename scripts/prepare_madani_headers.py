"""Keep the surah lettering and ornamental frame as native vector font outlines."""
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.svgLib.path import SVGPath
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'mobile/assets/fonts/madani'

font = TTFont(ROOT / 'data/madani-sources/surah-names.woff2')
font.flavor = None
font.save(OUTPUT / 'SurahNames.ttf')

builder = FontBuilder(1000, isTTF=True)
builder.setupGlyphOrder(['.notdef', 'frame'])
pen = TTGlyphPen(None)
scale = 1000 / 16320
SVGPath(ROOT / 'data/madani-sources/surah-frame.svg', transform=(scale, 0, 0, -scale, 0, 1491 * scale)).draw(Cu2QuPen(pen, 0.5, reverse_direction=False))
builder.setupGlyf({'.notdef': TTGlyphPen(None).glyph(), 'frame': pen.glyph()})
builder.setupHorizontalMetrics({'.notdef': (0, 0), 'frame': (1000, 0)})
builder.setupHorizontalHeader(ascent=124, descent=0)
builder.setupCharacterMap({0xE000: 'frame'})
builder.setupNameTable({'familyName': 'MadaniFrame', 'styleName': 'Regular', 'uniqueFontIdentifier': 'MadaniFrame-Regular', 'fullName': 'MadaniFrame Regular', 'psName': 'MadaniFrame-Regular'})
builder.setupOS2(sTypoAscender=124, sTypoDescender=0, usWinAscent=124, usWinDescent=0)
builder.setupPost()
builder.save(OUTPUT / 'SurahFrame.ttf')
print('Prepared vector surah names and ornamental frame.')
