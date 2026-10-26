# Quran verbatim v3: exec(open('/content/qv3.py').read())
import json, os, random, re, io, glob, zlib, time, shutil, subprocess, requests, numpy as np, soundfile as sf, torch
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from tqdm.auto import tqdm

LOCAL_TEST = os.environ.get('QV_LOCAL_TEST') == '1'   # tiny smoke test on a laptop; ignore on Colab
OUT = Path(os.environ.get('QV_OUT', '/content/drive/MyDrive/quran-verbatim/v3')); OUT.mkdir(parents=True, exist_ok=True)
WORK = Path(os.environ.get('QV_WORK', '/content/work')); (WORK / 'clips').mkdir(parents=True, exist_ok=True)
WHISPER_CPP = Path(os.environ.get('QV_WHISPER_CPP', '/content/whisper.cpp'))
BASE, TINY = 'tarteel-ai/whisper-base-ar-quran', 'tarteel-ai/whisper-tiny-ar-quran'
V2 = OUT.parent / 'v2'   # previous round; v3 continues from it when present
V2_BASE = str(V2 / 'stage1' / 'model') if (V2 / 'stage1' / 'model' / 'config.json').exists() else None
V2_TINY = str(V2 / 'stage3_tiny' / 'model') if (V2 / 'stage3_tiny' / 'model' / 'config.json').exists() else None

TRAIN_RECITATIONS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 12]   # quran.com verse-by-verse recitations with word timings
EVAL_RECITATIONS = [10, 11]                           # Shuraym, Tablawi: voices absent from training
SURAHS = list(range(1, 115))
AYAHS_PER_SURAH = 30        # cap so Al-Baqarah doesn't dominate; short surahs are used whole
EVAL_CLIPS = 600
N_TLOG = 50000              # tlog clips streamed for Stage 2
MAX_SECONDS = 28
WORKERS = 32                # parallel downloads / ffmpeg decodes

device = 'cuda' if torch.cuda.is_available() else 'cpu'
VRAM = torch.cuda.get_device_properties(0).total_memory / 2**30 if device == 'cuda' else 0
BF16 = device == 'cuda' and torch.cuda.is_bf16_supported()
BATCH = 64 if VRAM >= 40 else 32 if VRAM >= 20 else 16
LOADERS = min(16, os.cpu_count() or 2)
if device == 'cuda': torch.backends.cuda.matmul.allow_tf32 = True; torch.backends.cudnn.allow_tf32 = True
if LOCAL_TEST:
    TRAIN_RECITATIONS, EVAL_RECITATIONS, SURAHS = [7], [11], [1, 112, 113]
    AYAHS_PER_SURAH, EVAL_CLIPS, N_TLOG, BATCH, LOADERS = 4, 10, 6, 2, 0
random.seed(0); np.random.seed(0)
print(f'device={device} VRAM={VRAM:.0f}GB bf16={BF16} batch={BATCH} loaders={LOADERS} cpus={os.cpu_count()}')

def normalize(text):
    # Same rules as on-device/Native/ArabicMatching.swift.
    for pattern, repl in [(r'[\u064B-\u065F\u0670\u06D6-\u06ED\u0640]', ''), (r'[\u0622\u0623\u0625\u0671]', 'ا'),
                          (r'\u0649', 'ي'), (r'\u0629', 'ه'), (r'\u0624', 'و'), (r'\u0626', 'ي'),
                          (r'[^\u0621-\u064A\s]', '')]:
        text = re.sub(pattern, repl, text)
    return text.split()

def sh(cmd):
    print('$', cmd); return subprocess.run(cmd, shell=True).returncode

REPORTS = OUT / 'reports.json'
def save_report(name, value):
    data = json.loads(REPORTS.read_text()) if REPORTS.exists() else {}
    data[name] = value; REPORTS.write_text(json.dumps(data, ensure_ascii=False, indent=1))

API = 'https://api.quran.com/api/v4'

def get(url, **params):
    for attempt in range(5):
        try:
            r = requests.get(url, params=params, timeout=60); r.raise_for_status(); return r
        except Exception:
            if attempt == 4: raise
            time.sleep(2 ** attempt)

TEXT = {}
def surah_words(surah):
    if surah not in TEXT:
        words, page = {}, 1
        while page:
            j = get(f'{API}/verses/by_chapter/{surah}', words='true', word_fields='text_imlaei', per_page=50, page=page).json()
            for v in j['verses']:
                words[v['verse_key']] = [w['text_imlaei'] for w in v['words'] if w['char_type_name'] == 'word']
            page = j['pagination']['next_page']
        TEXT[surah] = words
    return TEXT[surah]

def verse_audio(recitation, surah):
    # {verse_key: (mp3 url, [[word_position, from_ms, to_ms], ...])}, timings relative to the ayah file.
    files, page = {}, 1
    while page:
        j = get(f'{API}/recitations/{recitation}/by_chapter/{surah}', fields='segments', per_page=50, page=page).json()
        for f in j['audio_files']:
            url = f['url']
            url = 'https:' + url if url.startswith('//') else url if url.startswith('http') else 'https://verses.quran.com/' + url
            segs = []
            for seg in f.get('segments') or []:   # some ayahs send timings as strings ('2350')
                try: seg = [int(float(v)) for v in seg[-3:]]
                except (TypeError, ValueError): continue
                if len(seg) == 3 and seg[2] > seg[1]: segs.append(seg)
            files[f['verse_key']] = (url, segs)
        page = j['pagination']['next_page']
    return files

def decode(data):
    # ffmpeg runs as its own process, so parallel decodes use every CPU core.
    p = subprocess.run(['ffmpeg', '-v', 'error', '-i', 'pipe:0', '-ac', '1', '-ar', '16000', '-f', 'f32le', 'pipe:1'],
                       input=data, capture_output=True)
    if p.returncode or not p.stdout: raise ValueError(p.stderr.decode()[-200:])
    return np.frombuffer(p.stdout, np.float32).copy()

def piece(audio, seg):
    return audio[int(seg[1] * 16):int(seg[2] * 16)]

def splice(pieces):
    gap = np.zeros(int(16000 * random.uniform(0.03, 0.25)), np.float32)
    out = []
    for p in pieces: out += [p, gap]
    return np.concatenate(out)

def augment(x):
    # Toward a phone in a room: tempo, echo, narrow microphone band, noise, level.
    if len(x) < 1600: return x.astype(np.float32)
    if random.random() < 0.5:   # ±10% speed
        rate = random.uniform(0.9, 1.1)
        x = np.interp(np.arange(0, len(x), rate), np.arange(len(x)), x).astype(np.float32)
    if random.random() < 0.4:   # small-room reverb: decaying noise impulse response
        n = int(16000 * random.uniform(0.08, 0.4))
        ir = np.random.randn(n).astype(np.float32) * np.exp(-np.linspace(0, random.uniform(4, 9), n)).astype(np.float32)
        ir[0] = 1; ir = ir / np.abs(ir).sum() * 2
        size = 1 << int(np.ceil(np.log2(len(x) + n)))   # FFT convolution: fast on 28 s clips
        x = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[:len(x)].astype(np.float32)
    if random.random() < 0.4:   # phone microphone band
        spec = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / 16000)
        spec[(f < random.uniform(100, 300)) | (f > random.uniform(3400, 7000))] *= 0.05
        x = np.fft.irfft(spec, len(x)).astype(np.float32)
    x = x * random.uniform(0.3, 1.2) / max(1e-6, np.abs(x).max()) * 0.9
    if random.random() < 0.7:   # room / phone noise at 10-35 dB SNR
        snr = random.uniform(10, 35)
        x = x + np.random.randn(len(x)).astype(np.float32) * np.sqrt(np.mean(x ** 2) / 10 ** (snr / 10) + 1e-12)
    return np.clip(x, -1, 1).astype(np.float32)

def silence_clip():
    # Empty target: teaches the model to write nothing on breath, room tone or noise.
    n = int(16000 * random.uniform(0.5, 6))
    return (np.random.randn(n) * 10 ** random.uniform(-4.5, -1.5)).astype(np.float32)

import difflib
def similar_word(word, pool):
    # Substitutions that sound close (العالمين → العالمون) are the realistic, hard ones.
    target = ''.join(normalize(word))
    picks = [c for c in random.sample(pool, min(60, len(pool))) if len(c[0]) and ''.join(normalize(c[1])) != target]
    if not picks: return None
    return max(picks, key=lambda c: difflib.SequenceMatcher(None, target, ''.join(normalize(c[1]))).ratio())

MISTAKES = {'omission', 'repetition', 'substitution', 'unfinished'}

def examples_for_ayah(audio, segs, words, other_pool, following=None):
    # Returns (audio, said_words, kind); said_words is the verbatim target.
    segs = [s for s in segs if 1 <= s[0] <= len(words)]
    if len(segs) < 3: return []
    idx = [s[0] - 1 for s in segs]
    pieces = [piece(audio, s) for s in segs]
    if min(len(p) for p in pieces) == 0: return []
    out = [(splice(pieces), [words[i] for i in idx], 'clean')]
    k = random.randrange(1, len(segs) - 1)
    out.append((splice(pieces[:k] + pieces[k + 1:]), [words[i] for i in idx[:k] + idx[k + 1:]], 'omission'))
    k = random.randrange(0, len(segs) - 1)
    out.append((splice(pieces[:k + 1] + pieces[k:]), [words[i] for i in idx[:k + 1] + idx[k:]], 'repetition'))
    if other_pool:
        k = random.randrange(1, len(segs))
        pick = similar_word(words[idx[k]], other_pool)
        if pick:
            said = [words[i] for i in idx]; said[k] = pick[1]
            out.append((splice(pieces[:k] + [pick[0]] + pieces[k + 1:]), said, 'substitution'))
    k = random.randrange(1, len(segs) - 1)
    out.append((splice(pieces[:k]), [words[i] for i in idx[:k]], 'unfinished'))
    # The app decodes sliding windows: they often start mid-ayah or run into the next ayah.
    k = random.randrange(1, len(segs) - 1)
    out.append((splice(pieces[k:]), [words[i] for i in idx[k:]], 'midstart'))
    if following:
        f_audio, f_segs, f_words = following
        f_segs = [s for s in f_segs if 1 <= s[0] <= len(f_words)]
        f_pieces = [piece(f_audio, s) for s in f_segs]
        if f_pieces and min(len(p) for p in f_pieces):
            k, j = random.randrange(0, len(segs) - 1), random.randrange(1, len(f_segs) + 1)
            out.append((splice(pieces[k:] + f_pieces[:j]), [words[i] for i in idx[k:]] + [f_words[s[0] - 1] for s in f_segs[:j]], 'cross'))
    if random.random() < 0.3: out.append((silence_clip(), [], 'silence'))
    return [(augment(a), w, kind) for a, w, kind in out if len(a) <= MAX_SECONDS * 16000]

def build(recitations, name, ayah_cap, surahs=None):
    cache = WORK / f'{name}.json'
    if cache.exists(): print('reusing', cache); return json.loads(cache.read_text())
    surahs = surahs or SURAHS
    rows = []
    with ThreadPoolExecutor(WORKERS) as pool:
        list(tqdm(pool.map(surah_words, surahs), total=len(surahs), desc='surah text'))
        for rec in recitations:
            meta = dict(zip(surahs, tqdm(pool.map(lambda s: verse_audio(rec, s), surahs), total=len(surahs), desc=f'{name} {rec} timings')))
            tasks = []
            for s in surahs:
                keys = [k for k, (u, segs) in meta[s].items() if k in TEXT[s] and len(segs) >= 3]
                tasks += [(s, k) for k in random.Random(f'{rec}{s}').sample(keys, min(ayah_cap, len(keys)))]
            def fetch(task):
                try: return task, decode(get(meta[task[0]][task[1]][0]).content)
                except Exception as e: return task, None
            audio = dict(tqdm(pool.map(fetch, tasks), total=len(tasks), desc=f'{name} {rec} audio'))
            def make(s):
                # Generate and write one surah's clips; numpy FFT and file writes release the GIL.
                out = []
                keys = [k for (ss, k) in tasks if ss == s and audio.get((ss, k)) is not None]
                pool_words = [(piece(audio[(s, k)], seg), TEXT[s][k][seg[0] - 1]) for k in keys
                              for seg in meta[s][k][1] if 1 <= seg[0] <= len(TEXT[s][k])]
                for k in keys:
                    nk = f'{s}:{int(k.split(":")[1]) + 1}'
                    following = (audio[(s, nk)], meta[s][nk][1], TEXT[s][nk]) if audio.get((s, nk)) is not None else None
                    for n, (clip, said, kind) in enumerate(examples_for_ayah(audio[(s, k)], meta[s][k][1], TEXT[s][k], pool_words, following)):
                        path = WORK / 'clips' / f'{name}_{rec}_{k.replace(":", "_")}_{n}.wav'
                        sf.write(path, clip, 16000, subtype='PCM_16')
                        out.append({'path': str(path), 'text': ' '.join(said), 'kind': kind,
                                    'correct': ' '.join(TEXT[s][k]), 'reciter': rec})
                return out
            with ThreadPoolExecutor(os.cpu_count() or 4) as makers:
                for part in tqdm(makers.map(make, surahs), total=len(surahs), desc=f'{name} {rec} clips'):
                    rows += part
            del audio
            print(name, rec, len(rows), 'clips so far')
    cache.write_text(json.dumps(rows, ensure_ascii=False))
    return rows

from dataclasses import dataclass
from datasets import Dataset
from transformers import (WhisperProcessor, WhisperForConditionalGeneration, GenerationConfig,
                          Seq2SeqTrainer, Seq2SeqTrainingArguments)
import jiwer

PROCESSOR = {}
def processor_for(name):
    if name not in PROCESSOR: PROCESSOR[name] = WhisperProcessor.from_pretrained(name, language='arabic', task='transcribe')
    return PROCESSOR[name]

GEN = GenerationConfig.from_pretrained('openai/whisper-base')   # Tarteel checkpoints ship an outdated one
def load(name):
    model = WhisperForConditionalGeneration.from_pretrained(name)
    if not hasattr(model.generation_config, 'lang_to_id'):
        gen = GenerationConfig.from_dict(GEN.to_dict()); model.generation_config = gen
    model.generation_config.forced_decoder_ids = None; model.config.forced_decoder_ids = None
    return model

DTYPE = torch.bfloat16 if BF16 else torch.float16 if device == 'cuda' else torch.float32
def transcribe(model, processor, rows, batch=None):
    batch = batch or BATCH * 2
    model = model.to(device, DTYPE).eval(); outs = []
    with ThreadPoolExecutor(8) as pool:
        for i in tqdm(range(0, len(rows), batch), desc='transcribing', unit='batch'):
            audio = list(pool.map(lambda r: sf.read(r['path'], dtype='float32')[0], rows[i:i + batch]))
            feats = processor.feature_extractor(audio, sampling_rate=16000, return_tensors='pt').input_features
            with torch.no_grad():
                ids = model.generate(feats.to(device, DTYPE), language='ar', task='transcribe', max_new_tokens=200)
            outs += processor.batch_decode(ids, skip_special_tokens=True)
    return outs

def wer(refs, hyps):
    return jiwer.wer([' '.join(normalize(r)) or '-' for r in refs], [' '.join(normalize(h)) or '-' for h in hyps])

def spliced_report(model, processor, rows, title):
    preds = transcribe(model, processor, rows)
    stats = {}
    for r, p in zip(rows, preds):
        s = stats.setdefault(r['kind'], {'n': 0, 'verbatim': 0, 'repaired': 0})
        s['n'] += 1
        s['verbatim'] += normalize(p) == normalize(r['text'])
        s['repaired'] += r['kind'] in MISTAKES and normalize(p) == normalize(r['correct'])
    result = {'wer': round(wer([r['text'] for r in rows], preds), 4),
              **{k: {'n': s['n'], 'verbatim': round(s['verbatim'] / s['n'], 3), 'repaired': round(s['repaired'] / s['n'], 3)}
                 for k, s in sorted(stats.items())}}
    print(title, json.dumps(result, indent=1)); save_report(title, result)
    return result

@dataclass
class Collator:
    processor: WhisperProcessor
    start_token: int
    def __call__(self, rows):
        audio = [sf.read(r['path'], dtype='float32')[0] for r in rows]
        feats = self.processor.feature_extractor(audio, sampling_rate=16000, return_tensors='pt').input_features
        labels = self.processor.tokenizer([r['text'] for r in rows], return_tensors='pt', padding=True)
        ids = labels.input_ids.masked_fill(labels.attention_mask.ne(1), -100)
        if (ids[:, 0] == self.start_token).all(): ids = ids[:, 1:]
        return {'input_features': feats, 'labels': ids}

def train(start, rows, out_dir, steps, lr):
    out_dir = Path(out_dir)
    if (out_dir / 'model' / 'config.json').exists():
        print('already trained:', out_dir); return str(out_dir / 'model')
    ckpt = out_dir / 'ckpt'
    run = {'batch': BATCH, 'bf16': BF16, 'steps': steps, 'lr': lr, 'start': start, 'rows': len(rows)}
    if ckpt.exists() and (not (ckpt / 'run.json').exists() or json.loads((ckpt / 'run.json').read_text()) != run):
        print('checkpoints from different settings moved aside'); shutil.move(str(ckpt), f'{ckpt}_old_{int(time.time())}')
    ckpt.mkdir(parents=True, exist_ok=True); (ckpt / 'run.json').write_text(json.dumps(run))
    processor = processor_for(start)
    model = load(start)
    args = Seq2SeqTrainingArguments(
        output_dir=str(ckpt), per_device_train_batch_size=BATCH, learning_rate=lr, warmup_steps=min(300, steps // 10),
        max_steps=steps, lr_scheduler_type='linear', bf16=BF16, fp16=device == 'cuda' and not BF16,
        logging_steps=max(1, min(50, steps // 20)), logging_first_step=True, disable_tqdm=False,
        save_steps=max(1, steps // 10), save_total_limit=2, report_to='none', remove_unused_columns=False,
        dataloader_num_workers=LOADERS, dataloader_persistent_workers=False, dataloader_pin_memory=device == 'cuda',
        dataloader_prefetch_factor=4 if LOADERS else None, seed=0)
    trainer = Seq2SeqTrainer(model=model, args=args, train_dataset=Dataset.from_list(rows),
                             data_collator=Collator(processor, model.config.decoder_start_token_id))
    trainer.train(resume_from_checkpoint=any(ckpt.glob('checkpoint-*')))
    trainer.save_model(str(out_dir / 'model')); processor.save_pretrained(str(out_dir / 'model'))
    model.generation_config.save_pretrained(str(out_dir / 'model'))
    # Free loader processes and GPU memory before the next stage.
    import gc; del trainer, model; gc.collect()
    if device == 'cuda': torch.cuda.empty_cache()
    return str(out_dir / 'model')

def steps_for(n_rows, epochs, cap):
    return max(2 if LOCAL_TEST else 200, min(cap, int(n_rows * epochs / BATCH)))

def export(model_dir, out_dir):
    # whisper.cpp GGML F16 (same format as the app's model) plus q8_0 and q5_0 for older phones.
    out_dir = Path(out_dir); target = out_dir / 'ggml-model.bin'
    if not (WHISPER_CPP / 'models').exists():
        sh(f'git clone -q https://github.com/ggml-org/whisper.cpp {WHISPER_CPP} && cd {WHISPER_CPP} && git checkout -q d1be6fde11ac6e0407606b4e42fe72d34add8037')
    if not (WORK / 'openai-whisper').exists(): sh(f'git clone -q --depth 1 https://github.com/openai/whisper {WORK}/openai-whisper')
    quantize = WHISPER_CPP / 'build' / 'bin' / 'whisper-quantize'
    if not quantize.exists():
        sh(f'cd {WHISPER_CPP} && cmake -B build -DCMAKE_BUILD_TYPE=Release -DWHISPER_BUILD_TESTS=OFF -DWHISPER_BUILD_EXAMPLES=ON > /dev/null && cmake --build build --target whisper-quantize -j {os.cpu_count()} > /dev/null')
    # Newer transformers saves only tokenizer.json; the converter needs the original vocab files (unchanged by training).
    from huggingface_hub import hf_hub_download
    for name in ['vocab.json', 'added_tokens.json']:
        if not (Path(model_dir) / name).exists(): shutil.copy(hf_hub_download(BASE, name), Path(model_dir) / name)
    if target.exists(): target.unlink()
    sh(f'python {WHISPER_CPP}/models/convert-h5-to-ggml.py {model_dir} {WORK}/openai-whisper {out_dir}')
    if not target.exists(): raise RuntimeError(f'GGML conversion failed for {model_dir}')
    for kind in ['q8_0', 'q5_0']:
        sh(f'{quantize} {target} {out_dir}/ggml-model-{kind}.bin {kind} > /dev/null')
    for f in sorted(out_dir.glob('ggml-model*.bin')): print(f'EXPORTED {f}  {f.stat().st_size / 1e6:.0f} MB')

train_syn = build(TRAIN_RECITATIONS, 'train_v3', AYAHS_PER_SURAH)
eval_all = build(EVAL_RECITATIONS, 'eval_v3', 4 if not LOCAL_TEST else 2, surahs=random.Random(1).sample(SURAHS, min(40, len(SURAHS))))
eval_syn = random.Random(2).sample(eval_all, min(EVAL_CLIPS, len(eval_all)))
print(len(train_syn), 'training clips,', len(eval_syn), 'held-out clips')

done = json.loads(REPORTS.read_text()) if REPORTS.exists() else {}
if 'BASELINE base' not in done: spliced_report(load(BASE), processor_for(BASE), eval_syn, 'BASELINE base')
if V2_BASE and 'V2 stage1 base' not in done: spliced_report(load(V2_BASE), processor_for(V2_BASE), eval_syn, 'V2 stage1 base')
# Continue from v2 (already verbatim) at a lower rate; from scratch otherwise.
STAGE1 = train(V2_BASE or BASE, train_syn, OUT / 'stage1', steps_for(len(train_syn), 2 if V2_BASE else 2, 6000), 1e-5 if V2_BASE else 2e-5)
spliced_report(load(STAGE1), processor_for(STAGE1), eval_syn, 'STAGE 1 base')
export(STAGE1, OUT / 'stage1')
if device == 'cuda': torch.cuda.empty_cache()

from datasets import load_dataset, Audio

def save_clip(args):
    data, name = args
    try: x = decode(data)
    except Exception: return None
    if not 0.5 <= len(x) / 16000 <= MAX_SECONDS: return None
    path = WORK / 'clips' / f'{name}.wav'; sf.write(path, x, 16000, subtype='PCM_16')
    return str(path)

def real_data():
    cache = WORK / 'real.json'
    if cache.exists(): return json.loads(cache.read_text())
    real = []
    with ThreadPoolExecutor(WORKERS) as pool:
        # RetaSy learners: Quran only, usable labels only.
        NOT_QURAN = {'Adhan', 'Adhkar after prayer', 'Dua Qunoot', 'Dua from the Quran', 'At-Tahiyyat', 'Subhanaka',
                     'Salawat', 'Dua for Protection', 'Iqamah Prayer', 'Ayat Ramadan'}
        try:
            reta = load_dataset('RetaSy/quranic_audio_dataset', split='train', streaming=True).cast_column('audio', Audio(decode=False))
            meta, jobs = [], []
            for i, r in enumerate(tqdm(reta.take(40 if LOCAL_TEST else 10**9), desc='RetaSy')):
                if r['Surah'] in NOT_QURAN or r['final_label'] in ('not_related_quran', 'not_match_aya', 'multiple_aya', 'in_complete'): continue
                meta.append({'text': r['Aya'], 'source': 'retasy', 'label': r['final_label'] or 'unlabelled', 'speaker': r['reciter_id'] or f'r{i}'})
                jobs.append((r['audio']['bytes'], f'reta_{i}'))
            for m, p in zip(meta, tqdm(pool.map(save_clip, jobs), total=len(jobs), desc='RetaSy decode')):
                if p: real.append({**m, 'path': p})
        except Exception as e: print('RetaSy skipped:', str(e)[:200])
        print('retasy', len(real))

        # Kaggle Tarteel v1 Al-Fatihah: <surah>_<ayah>_<speaker>.wav
        if not LOCAL_TEST:
            sh('kaggle datasets download -q -d haithamalhaji/tarteeldatasetv1alfatiha -p /content/kaggle --unzip')
        fatiha = surah_words(1)
        files = [f for f in glob.glob('/content/kaggle/**/*.wav', recursive=True)
                 if Path(f).stem.split('_')[0] == '1' and f"1:{Path(f).stem.split('_')[1]}" in fatiha]
        jobs = [(Path(f).read_bytes(), f'kaggle_{Path(f).stem}') for f in files]
        for f, p in zip(files, tqdm(pool.map(save_clip, jobs), total=len(jobs), desc='Kaggle')):
            if p:
                _, a, uid = Path(f).stem.split('_')[:3]
                real.append({'path': p, 'text': ' '.join(fatiha[f'1:{a}']), 'source': 'kaggle', 'label': 'unlabelled', 'speaker': uid})
        print('+kaggle', len(real))

        # tlog by Tarteel AI (CC-BY-4.0, credit Tarteel), from the public mirror catsOfpeople/bin3jb
        # (all 744 data files match tarteel-ai/tlog in name and size). Plain HTTP: datasets can't open bucket URLs.
        try:
            import requests, pyarrow.parquet as pq
            tdir = WORK / 'tlog'; tdir.mkdir(exist_ok=True)
            mirror = 'https://huggingface.co/buckets/catsOfpeople/bin3jb/resolve/data/clean-{:05d}-of-00411.parquet'
            def fetch_shard(i):
                path = tdir / f'clean-{i:05d}.parquet'
                if not path.exists():
                    tmp = path.with_suffix('.part')
                    with requests.get(mirror.format(i), stream=True, timeout=300) as r:
                        r.raise_for_status()
                        with open(tmp, 'wb') as f:
                            for chunk in r.iter_content(1 << 20): f.write(chunk)
                    tmp.rename(path)
                return path
            n, bar = 0, tqdm(total=N_TLOG, desc='tlog clips')
            ids = random.Random(6).sample(range(411), 3 if LOCAL_TEST else 120)
            with ThreadPoolExecutor(16) as downloads:
                for path in tqdm(downloads.map(fetch_shard, ids), total=len(ids), desc='tlog shards'):
                    if n >= N_TLOG: continue
                    table = pq.read_table(path)
                    meta, jobs = [], []
                    for r in table.select([c for c in ('audio', 'label') if c in table.column_names]).to_pylist():
                        if n + len(jobs) >= N_TLOG: break
                        a = r.get('audio')
                        if not isinstance(r.get('label'), str) or not a or not a.get('bytes'): continue
                        meta.append({'text': r['label'], 'source': 'tlog', 'label': 'unlabelled', 'speaker': Path(a.get('path') or 'x').stem.split('_')[-1]})
                        jobs.append((a['bytes'], f'tlog_{n + len(jobs)}'))
                    for m, p in zip(meta, pool.map(save_clip, jobs)):
                        if p: real.append({**m, 'path': p})
                    n += len(jobs); bar.update(len(jobs)); path.unlink()
        except Exception as e: print('tlog skipped:', str(e)[:300])
    print('total real', len(real), {s: sum(r['source'] == s for r in real) for s in ('retasy', 'kaggle', 'tlog')})
    cache.write_text(json.dumps(real, ensure_ascii=False))
    return real

real = real_data()

def letters_ok(heard, said):
    h, s = normalize(heard), normalize(said)
    return len(h) == len(s) and jiwer.cer(' '.join(s) or '-', ' '.join(h) or '-') <= 0.10

held = lambda r: r['source'] == 'kaggle' and zlib.crc32(r['speaker'].encode()) % 5 == 0
eval_real = [r for r in real if held(r)]
eval_mistakes = [r for r in real if r['label'] == 'in_correct']
candidates = [r for r in real if not held(r) and r['label'] != 'in_correct']

def real_report(model, processor, title):
    result = {}
    if eval_real:
        result['kaggle_heldout_wer'] = round(wer([r['text'] for r in eval_real], transcribe(model, processor, eval_real)), 4)
    if eval_mistakes:
        p = transcribe(model, processor, eval_mistakes)
        result['retasy_mistakes_hidden'] = round(sum(normalize(x) == normalize(r['text']) for x, r in zip(p, eval_mistakes)) / len(eval_mistakes), 3)
    print(title, result); save_report(title, result)

keep_cache = WORK / 'train_real_v3.json'
if keep_cache.exists(): train_real = json.loads(keep_cache.read_text())
else:
    stage1 = load(STAGE1)
    heard = transcribe(stage1, processor_for(STAGE1), candidates)
    train_real = [r for r, h in zip(candidates, heard) if r['label'] == 'correct' or letters_ok(h, r['text'])]
    keep_cache.write_text(json.dumps(train_real, ensure_ascii=False))
print(f'kept {len(train_real)}/{len(candidates)} real clips', {s: sum(r['source'] == s for r in train_real) for s in ('retasy', 'kaggle', 'tlog')})

done = json.loads(REPORTS.read_text()) if REPORTS.exists() else {}
if 'REAL baseline' not in done: real_report(load(BASE), processor_for(BASE), 'REAL baseline')
if V2_BASE and 'REAL v2 stage1' not in done: real_report(load(V2_BASE), processor_for(V2_BASE), 'REAL v2 stage1')
real_report(load(STAGE1), processor_for(STAGE1), 'REAL stage1')
mix = random.Random(3).sample(train_syn, len(train_syn) // 2) + train_real
random.Random(4).shuffle(mix)
STAGE2 = train(STAGE1, mix, OUT / 'stage2', steps_for(len(mix), 2, 4000), 1e-5)
spliced_report(load(STAGE2), processor_for(STAGE2), eval_syn, 'STAGE 2 base')
real_report(load(STAGE2), processor_for(STAGE2), 'REAL stage2')
export(STAGE2, OUT / 'stage2')
if device == 'cuda': torch.cuda.empty_cache()

full_mix = train_syn + train_real
random.Random(5).shuffle(full_mix)
if 'BASELINE tiny' not in (json.loads(REPORTS.read_text()) if REPORTS.exists() else {}):
    spliced_report(load(TINY), processor_for(TINY), eval_syn, 'BASELINE tiny')
STAGE3 = train(V2_TINY or TINY, full_mix, OUT / 'stage3_tiny', steps_for(len(full_mix), 2, 6000), 1.5e-5 if V2_TINY else 3e-5)
spliced_report(load(STAGE3), processor_for(STAGE3), eval_syn, 'STAGE 3 tiny')
real_report(load(STAGE3), processor_for(STAGE3), 'REAL stage3 tiny')
export(STAGE3, OUT / 'stage3_tiny')

print(json.dumps(json.loads(REPORTS.read_text()), indent=1, ensure_ascii=False))
sh(f'ls -la {OUT}/stage1 {OUT}/stage2 {OUT}/stage3_tiny | grep ggml')