"""Bundle Unicode Quran words and Madani line metadata for offline reading."""

import concurrent.futures
import json
from pathlib import Path
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path('/private/tmp/quran-tutor-pages-v2')
API = 'https://api.quran.com/api/v4'


def request(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=45)


def fetch(page):
    path = CACHE / f'{page}.json'
    if path.exists():
        return json.loads(path.read_text())
    for attempt in range(4):
        try:
            url = f'{API}/verses/by_page/{page}?words=true&word_fields=text_uthmani,line_number,code_v2&per_page=50'
            with request(url) as response:
                result = json.load(response)
            assert result['pagination']['total_pages'] == 1, page
            path.write_text(json.dumps(result, ensure_ascii=False))
            return result
        except Exception:
            if attempt == 3:
                raise
            time.sleep(attempt + 1)


def main():
    CACHE.mkdir(exist_ok=True)
    with request(f'{API}/chapters') as response:
        chapters = json.load(response)['chapters']
    pages = [{'page': n, 'juz': None, 'surah': None, 'starts': {}, 'lines': {}} for n in range(1, 605)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        for page, result in enumerate(pool.map(fetch, range(1, 605)), 1):
            verses = result['verses']
            for verse in verses:
                surah, ayah = map(int, verse['verse_key'].split(':'))
                last_word_location = None
                for word in verse['words']:
                    # Verse endpoint boundaries differ from the word-level print layout.
                    location = (word['page_number'], word['line_number'])
                    if word['char_type_name'] == 'end' and last_word_location:
                        # The API places 84:21's marker before its final words.
                        location = max(location, last_word_location)
                    else:
                        last_word_location = location
                    word_page, line = location
                    target = pages[word_page - 1]
                    if target['juz'] is None:
                        target['juz'] = verse['juz_number']
                        target['surah'] = surah
                    target['lines'].setdefault(line, []).append({
                        'surah': surah, 'ayah': ayah,
                        'word_index_in_ayah': word['position'],
                        'text_uthmani': word['text_uthmani'],
                        'glyph': word['code_v2'],
                        'end': word['char_type_name'] == 'end',
                    })
                    if ayah == 1 and word['position'] == 1:
                        target['starts'][line] = surah
            if page % 50 == 0:
                print(f'{page}/604 pages', flush=True)
    assert len(pages) == 604
    for page in pages:
        page['lines'] = [{'number': line, 'words': words} for line, words in sorted(page['lines'].items())]
    endings = [w for p in pages for line in p['lines'] for w in line['words'] if w['end']]
    assert len(endings) == 6236, len(endings)
    output = ROOT / 'mobile/assets/data/mushaf.json'
    output.write_text(json.dumps({'chapters': chapters, 'pages': pages}, ensure_ascii=False, separators=(',', ':')))
    print(f'Saved {output} ({output.stat().st_size:,} bytes)', flush=True)


if __name__ == '__main__':
    main()
