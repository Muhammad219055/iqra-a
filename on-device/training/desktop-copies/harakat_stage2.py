# Harakat stage 2: does Muaalem (obadx/muaalem-model-v3_2) actually catch learners' mistakes?
# Run in the harakat notebook after the export cell:  exec(open('/content/harakat_stage2.py').read())
#
# Test: RetaSy Al-Fatihah recitations from non-Arab learners, labelled by annotators as `correct` or `in_correct`.
# Muaalem writes the sounds it hears; we compare them with the expected sounds of that ayah (quran-transcript).
# A useful detector flags far more `in_correct` clips than `correct` ones. No training here: about 10-15 min.
#
# License: quran-muaalem is QML-1.0 (Apache-2.0 + an AI-advisory notice in the app, no ads, Sharia adherence,
# a free-access path). Read github.com/obadx/quran-muaalem/blob/main/LICENSE before shipping anything built on it.
import subprocess, sys, io, inspect
subprocess.run([sys.executable, '-m', 'pip', '-q', 'install', 'quran-muaalem', 'quran-transcript'], check=True)
import librosa, soundfile as sf
from quran_transcript import Aya, quran_phonetizer, MoshafAttributes
# quran-muaalem targets transformers 4.x; 5.x dropped this module constant (it was 2 in 4.x). Restore it.
import transformers.models.wav2vec2_bert.modeling_wav2vec2_bert as _w2vb
if not hasattr(_w2vb, '_HIDDEN_STATES_START_POSITION'): _w2vb._HIDDEN_STATES_START_POSITION = 2
for _name in [n for n in sys.modules if n.startswith('quran_muaalem')]: del sys.modules[_name]   # drop the failed import
from quran_muaalem import Muaalem

def strip_marks(text):
    return re.sub(r'[^ء-ي]', '', re.sub(r'[آأإٱ]', 'ا', text))

def fatiha_uthmani():
    # Aya's argument order isn't documented clearly; pick the order whose first ayah is the basmala.
    for make in (lambda i: Aya(1, i), lambda i: Aya(i, 1)):
        try:
            texts = []
            for i in range(1, 8):
                a = make(i); a = a.get() if hasattr(a, 'get') and not hasattr(a, 'uthmani') else a
                texts.append(a.uthmani)
            if strip_marks(texts[0]).startswith('بسم') and 'الحمد' in strip_marks(texts[1]): return texts
        except Exception as e: print('Aya order failed:', str(e)[:120])
    raise RuntimeError('Could not read Al-Fatihah from quran_transcript; paste this error to Claude.')

FATIHA = fatiha_uthmani()
print('Ayah 1 uthmani:', FATIHA[0])
moshaf = MoshafAttributes(rewaya='hafs', madd_monfasel_len=2, madd_mottasel_len=4, madd_mottasel_waqf=4, madd_aared_len=2)
REF = [quran_phonetizer(t, moshaf, remove_spaces=True) for t in FATIHA]
KEYS = [strip_marks(t) for t in FATIHA]

def ayah_of(text):
    k = strip_marks(text)
    scores = [difflib.SequenceMatcher(None, k, key).ratio() for key in KEYS]
    best = int(np.argmax(scores))
    return best if scores[best] > 0.85 else None

# RetaSy Al-Fatihah clips with a final annotation.
reta = load_dataset('RetaSy/quranic_audio_dataset', split='train').cast_column('audio', Audio(decode=False))
clips = []
for r in tqdm(reta, desc='RetaSy Al-Fatihah'):
    if r['Surah'] != 'Al-Faatihah' or r['final_label'] not in ('correct', 'in_correct'): continue
    i = ayah_of(r['Aya'])
    if i is None: continue
    try: wave, _ = librosa.load(io.BytesIO(r['audio']['bytes']), sr=16000, mono=True)
    except Exception: continue
    if 0.5 <= len(wave) / 16000 <= 30: clips.append((wave, i, r['final_label']))
print(len(clips), 'clips:', {l: sum(c[2] == l for c in clips) for l in ('correct', 'in_correct')})

muaalem = Muaalem(device=device)
results = {'correct': [], 'in_correct': []}
crashed = {'correct': 0, 'in_correct': 0}
examples = []
# One clip per call: Muaalem's decoder raises IndexError when a recitation is far from the expected ayah
# (e.g. only part of it recited); count those per label instead of stopping.
for wave, i, label in tqdm(clips, desc='Muaalem'):
    try: out = muaalem([wave], [REF[i]], sampling_rate=16000)[0]
    except (IndexError, RuntimeError, ValueError): crashed[label] += 1; continue
    heard, expected = out.phonemes.text, REF[i].phonemes
    sm = difflib.SequenceMatcher(None, expected, heard, autojunk=False)
    errors = sum(max(i2 - i1, j2 - j1) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != 'equal')
    results[label].append(errors / max(1, len(expected)))
    if len(examples) < 6 and errors: examples.append((label, i + 1, expected, heard))

summary = {}
for label, rates in results.items():
    if rates:
        summary[label] = {'clips': len(rates), 'mean_phoneme_error': round(float(np.mean(rates)), 3),
                          'flagged_any': round(float(np.mean([r > 0 for r in rates])), 3),
                          'flagged_over_5pct': round(float(np.mean([r > 0.05 for r in rates])), 3),
                          'decoder_crashed': crashed[label]}
save_report('MUAALEM on RetaSy Al-Fatihah (no training)', summary)
print('A useful detector: in_correct clips flagged much more often than correct clips.')
for label, ayah, expected, heard in examples:
    print(f'\n[{label}] ayah {ayah}\n expected: {expected}\n heard:    {heard}')
