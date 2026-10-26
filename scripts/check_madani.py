"""Validate the shipped Mushaf's completeness and matching native glyph fonts."""
import json
from pathlib import Path

from fontTools.ttLib import TTFont

ASSETS = Path(__file__).resolve().parents[1] / 'mobile/assets'


def check():
    data = json.loads((ASSETS / 'data/madani.json').read_text())
    assert [p['page'] for p in data['pages']] == list(range(1, 605))
    expected_ayahs = {(chapter['id'], ayah) for chapter in data['chapters']
                      for ayah in range(1, chapter['verses_count'] + 1)}
    actual_ayahs = set()
    word_ids = set()
    headers = []
    positions = {}
    for page in data['pages']:
        numbers = [line['number'] for line in page['lines']]
        assert numbers == sorted(set(numbers)), (page['page'], 'overlapping lines')
        assert numbers[-1] == (8 if page['page'] <= 2 else 15), page['page']
        with TTFont(ASSETS / f'fonts/madani/p{page["page"]:03}.ttf') as font:
            cmap = font.getBestCmap()
            units = font['head'].unitsPerEm
            for line in page['lines']:
                if line['type'] == 'header':
                    headers.append(line['surah'])
                for word in line['words']:
                    key = (word['surah'], word['ayah'], word['word_index_in_ayah'])
                    assert key not in word_ids, ('duplicate word', key)
                    word_ids.add(key)
                    assert all(ord(c) in cmap for c in word['glyph']), ('missing glyph', page['page'], key)
                    advance = sum(font['hmtx'][cmap[ord(c)]][0] for c in word['glyph']) / units
                    assert abs(advance - word['advance']) < 0.000001, ('wrong advance', key)
                    verse = key[:2]
                    positions.setdefault(verse, []).append(key[2])
                    if word['end']:
                        assert verse not in actual_ayahs, ('duplicate ayah ending', verse)
                        actual_ayahs.add(verse)
    assert actual_ayahs == expected_ayahs, ('ayah mismatch', expected_ayahs - actual_ayahs)
    assert sorted(headers) == list(range(1, 115)), 'Missing or repeated surah header'
    for verse, word_positions in positions.items():
        assert word_positions == list(range(1, len(word_positions) + 1)), ('missing or reordered word', verse)
    print(f'PASS: 604 pages, {len(actual_ayahs):,} ayahs, 114 headers, {len(word_ids):,} word/marker glyphs; all fonts and advances match.')


if __name__ == '__main__':
    check()
