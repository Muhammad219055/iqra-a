"""Prepare native QCF v2 vector fonts and exact Madani line data.

Sources: Quran Foundation's public QCF v2 fonts; adelpro/open-quran-view
page metadata. Downloads happen at build time, never in the reader.
Requires fonttools and brotli in the project's Python environment.
"""
import concurrent.futures
import json
from pathlib import Path
import time
import urllib.request

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path('/private/tmp/quran-tutor-qcf2')
ASSETS = ROOT / 'mobile/assets'
BASE = 'https://raw.githubusercontent.com/adelpro/open-quran-view/main/src/data'


def download(url, path):
    if path.exists():
        return
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=60) as response:
                content = response.read()
            path.write_bytes(content)
            return
        except Exception:
            if attempt == 3:
                raise
            time.sleep(attempt + 1)


def prepare_page(page):
    number = page['pageNumber']
    source = CACHE / f'p{number}.woff2'
    download(f'https://static.qurancdn.com/fonts/quran/hafs/v2/woff2/p{number}.woff2', source)
    font = TTFont(source)
    cmap = font.getBestCmap()
    units = font['head'].unitsPerEm
    if 32 not in cmap:
        order = list(font.getGlyphOrder())
        font['glyf']['space'] = TTGlyphPen(None).glyph()
        font['hmtx'].metrics['space'] = (round(units / 4), 0)
        font.setGlyphOrder(order + ['space'])
        for table in font['cmap'].tables:
            if table.isUnicode():
                table.cmap[32] = 'space'
        cmap = font.getBestCmap()
    chars = {32}
    for line in page['lines']:
        for word in line['words']:
            glyphs = word['code_v2']
            chars.update(map(ord, glyphs))
            assert all(ord(c) in cmap for c in glyphs), (number, glyphs)
            word['advance'] = round(sum(font['hmtx'].metrics[cmap[ord(c)]][0] for c in glyphs) / units, 6)
    page['spaceAdvance'] = font['hmtx'].metrics[cmap[32]][0] / units if 32 in cmap else 0
    options = subset.Options()
    options.drop_tables += ['hdmx', 'LTSH', 'VDMX']
    options.name_IDs = ['*']
    options.name_legacy = True
    sub = subset.Subsetter(options=options)
    sub.populate(unicodes=chars)
    sub.subset(font)
    font.flavor = None
    font.save(ASSETS / f'fonts/madani/p{number:03}.ttf')
    return page


def main():
    CACHE.mkdir(exist_ok=True)
    (ASSETS / 'fonts/madani').mkdir(exist_ok=True)
    unicode_data = json.loads((ASSETS / 'data/mushaf.json').read_text())
    layouts = []
    for source_page in unicode_data['pages']:
        lines = {line['number']: {'lineNumber': line['number'], 'lineType': 'text',
                 'isCentered': source_page['page'] <= 2,
                 'words': [{'surah': w['surah'], 'verse': w['ayah'],
                            'position': w['word_index_in_ayah'], 'code_v2': w['glyph']}
                           for w in line['words']]} for line in source_page['lines']}
        for start, surah in source_page['starts'].items():
            start = int(start)
            header = start - (1 if surah in (1, 9) else 2)
            assert header >= 0 and header not in lines, (source_page['page'], header)
            header_line = {'lineNumber': header, 'lineType': 'header', 'isCentered': True,
                           'surahNumber': surah, 'words': []}
            if header == 0:
                # This edition prints these titles on the preceding page's last line.
                previous = layouts[-1]['lines']
                assert previous[-1]['lineNumber'] == 14
                previous.append({**header_line, 'lineNumber': 15})
            else:
                lines[header] = header_line
            if surah not in (1, 9):
                assert start - 1 not in lines
                lines[start - 1] = {'lineNumber': start - 1, 'lineType': 'bismillah',
                                    'isCentered': True, 'words': []}
        layouts.append({'pageNumber': source_page['page'],
                        'isVerticallyCentered': source_page['page'] <= 2,
                        'lines': [line for _, line in sorted(lines.items())]})
    words = {f'{w["surah"]}:{w["ayah"]}:{w["word_index_in_ayah"]}': w
             for p in unicode_data['pages'] for line in p['lines'] for w in line['words']}
    chapters = unicode_data['chapters']
    pages = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        for index, page in enumerate(pool.map(prepare_page, layouts), 1):
            page_words = []
            lines = []
            for line in page['lines']:
                compact_words = []
                for word in line['words']:
                    key = f'{word["surah"]}:{word["verse"]}:{word["position"]}'
                    original = words[key]
                    compact_words.append({**original, 'glyph': word['code_v2'], 'advance': word['advance']})
                page_words.extend(compact_words)
                lines.append({'number': line['lineNumber'], 'type': line['lineType'],
                              'centered': line['isCentered'] or index in (1, 2),
                              'surah': line.get('surahNumber') or line.get('metadata', {}).get('chapterId'),
                              'words': compact_words})
            first = page_words[0]
            pages.append({'page': index, 'surah': first['surah'],
                          'juz': next(p['juz'] for p in unicode_data['pages']
                                      if any(w['surah'] == first['surah'] and w['ayah'] == first['ayah']
                                             for l in p['lines'] for w in l['words'])),
                          'centered': page.get('isVerticallyCentered', False),
                          'spaceAdvance': page['spaceAdvance'], 'lines': lines})
            if index % 50 == 0:
                print(f'{index}/604 vector pages', flush=True)
    assert len(pages) == 604
    assert sum(w['end'] for p in pages for l in p['lines'] for w in l['words']) == 6236
    output = ASSETS / 'data/madani.json'
    output.write_text(json.dumps({'chapters': chapters, 'pages': pages}, ensure_ascii=False, separators=(',', ':')))
    font_map = '\n'.join(f"  {p}: require('./assets/fonts/madani/p{p:03}.ttf')," for p in range(1, 605))
    (ROOT / 'mobile/madaniFonts.js').write_text(f'// Generated by scripts/prepare_madani.py.\nexport default {{\n{font_map}\n}};\n')
    print(f'Prepared {len(pages)} pages and matching native fonts.', flush=True)


if __name__ == '__main__':
    main()
