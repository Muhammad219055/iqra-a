"""Builds quran_harakat_colab.ipynb: phoneme recognizer for harakat / letter mistakes. Run: python3 make_harakat_notebook.py"""
import json
from pathlib import Path

CELLS = []
def md(s): CELLS.append(("markdown", s))
def code(s): CELLS.append(("code", s))

md("""# Quran harakat model — phoneme recognizer (Colab, A100 / L4)
**Runtime → Run all.** Trains a small CTC model that writes the *sounds actually recited* (consonants, short vowels,
shadda, long vowels). The app compares them with the ayah's expected sounds to flag harakat and letter mistakes,
only on words Whisper already matched.

Data (IqraEval, ArabicNLP 2025 shared task): `Iqra_train` (71k recitations with phoneme labels) and `Iqra_TTS`
(55k synthetic recitations whose labels contain the injected mistakes). Test: `QuranMB.v2`, real recitations
with human-annotated mistakes (`IqraEval_Test_GT` is gated: accept its terms on Hugging Face first).

Base model: `facebook/wav2vec2-base` (Apache-2.0, 95M). mHuBERT-147 scores higher in the paper but is
CC-BY-NC-SA (non-commercial). Outputs go to Drive `MyDrive/quran-harakat/`; Run all again resumes.""")

code("""!pip -q install -U "transformers>=4.44" "datasets>=2.20" jiwer accelerate onnx onnxruntime soundfile librosa
from google.colab import drive
drive.mount('/content/drive')
from huggingface_hub import notebook_login
notebook_login()   # needed for IqraEval_Test_GT (accept its terms on the dataset page first)""")

code("""import json, os, re, time, random, difflib, numpy as np, torch
from pathlib import Path
from tqdm.auto import tqdm
from datasets import load_dataset, Audio, concatenate_datasets

BASE_MODEL = 'facebook/wav2vec2-base'   # Apache-2.0; 'utter-project/mHuBERT-147' is stronger but non-commercial
OUT = Path('/content/drive/MyDrive/quran-harakat'); OUT.mkdir(parents=True, exist_ok=True)
MAX_SECONDS = 16
device = 'cuda' if torch.cuda.is_available() else 'cpu'
VRAM = torch.cuda.get_device_properties(0).total_memory / 2**30 if device == 'cuda' else 0
BF16 = device == 'cuda' and torch.cuda.is_bf16_supported()
BATCH = 64 if VRAM >= 40 else 32 if VRAM >= 20 else 16
LOADERS = min(12, os.cpu_count() or 2)
if device == 'cuda': torch.backends.cuda.matmul.allow_tf32 = True
print(f'device={device} VRAM={VRAM:.0f}GB bf16={BF16} batch={BATCH}')

def phones(text):
    return [p for p in (text or '').split() if p != '<sil>']

REPORTS = OUT / 'reports.json'
def save_report(name, value):
    data = json.loads(REPORTS.read_text()) if REPORTS.exists() else {}
    data[name] = value; REPORTS.write_text(json.dumps(data, indent=1)); print(name, value)""")

code("""# Training targets are what was actually said: Iqra_train phoneme_aug, Iqra_TTS phoneme_mis (mistakes included).
train_real = load_dataset('IqraEval/Iqra_train', split='train')
dev = load_dataset('IqraEval/Iqra_train', split='dev')
tts = load_dataset('IqraEval/Iqra_TTS', split='train')
train_real = train_real.map(lambda r: {'target': r['phoneme_aug'] or r['phoneme_ref']}, remove_columns=[c for c in train_real.column_names if c not in ('audio',)])
dev = dev.map(lambda r: {'target': r['phoneme_ref']}, remove_columns=[c for c in dev.column_names if c not in ('audio',)])
tts = tts.map(lambda r: {'target': (r['phoneme_mis'] or '').strip() or r['phoneme_ref']}, remove_columns=[c for c in tts.column_names if c not in ('audio',)])
train = concatenate_datasets([train_real, tts]).cast_column('audio', Audio(sampling_rate=16000)).shuffle(seed=0)
dev = dev.cast_column('audio', Audio(sampling_rate=16000))

vocab_file = OUT / 'vocab.json'
if vocab_file.exists(): VOCAB = json.loads(vocab_file.read_text())
else:
    symbols = sorted({p for t in tqdm(train['target'], desc='phoneme set') for p in phones(t)})
    VOCAB = {'<blank>': 0, **{s: i + 1 for i, s in enumerate(symbols)}}
    vocab_file.write_text(json.dumps(VOCAB, ensure_ascii=False, indent=1))
ID = {i: s for s, i in VOCAB.items()}
print(len(train), 'train,', len(dev), 'dev,', len(VOCAB), 'symbols:', ' '.join(list(VOCAB)[1:]))""")

code("""from dataclasses import dataclass
from transformers import Wav2Vec2ForCTC, Wav2Vec2FeatureExtractor, Trainer, TrainingArguments

extractor = Wav2Vec2FeatureExtractor(feature_size=1, sampling_rate=16000, padding_value=0.0, do_normalize=True, return_attention_mask=True)

@dataclass
class Collator:
    def __call__(self, rows):
        rows = [r for r in rows if 0.3 <= len(r['audio']['array']) / 16000 <= MAX_SECONDS and phones(r['target'])] or rows[:1]
        batch = extractor([r['audio']['array'] for r in rows], sampling_rate=16000, return_tensors='pt', padding=True)
        ids = [[VOCAB[p] for p in phones(r['target']) if p in VOCAB] for r in rows]
        width = max(len(x) for x in ids)
        batch['labels'] = torch.tensor([x + [-100] * (width - len(x)) for x in ids])
        batch.pop('attention_mask', None)   # wav2vec2-base (group norm) expects zero padding without a mask
        return batch

def greedy(logits):
    out = []
    for seq in logits.argmax(-1).tolist():
        prev, ph = None, []
        for t in seq:
            if t != prev and t != 0: ph.append(ID[t])
            prev = t
        out.append(ph)
    return out

def predict(model, rows, batch=64):
    model = model.to(device).eval(); outs = []
    for i in tqdm(range(0, len(rows), batch), desc='predicting'):
        audio = [r['audio']['array'] for r in rows[i:i + batch]]
        x = extractor(audio, sampling_rate=16000, return_tensors='pt', padding=True)
        with torch.no_grad(), torch.autocast(device, dtype=torch.bfloat16, enabled=BF16):
            logits = model(x.input_values.to(device)).logits.float()
        outs += greedy(logits)
    return outs

def per(refs, hyps):
    import jiwer
    return jiwer.wer([' '.join(r) or '-' for r in refs], [' '.join(h) or '-' for h in hyps])""")

code("""final = OUT / 'model'
if (final / 'config.json').exists():
    print('already trained'); model = Wav2Vec2ForCTC.from_pretrained(final)
else:
    model = Wav2Vec2ForCTC.from_pretrained(BASE_MODEL, vocab_size=len(VOCAB), pad_token_id=0, ctc_loss_reduction='mean',
                                           ctc_zero_infinity=True, layerdrop=0.05, mask_time_prob=0.05, ignore_mismatched_sizes=True)
    model.freeze_feature_encoder()
    steps = min(20000, int(len(train) * 3 / BATCH))   # about 3 passes
    args = TrainingArguments(output_dir=str(OUT / 'ckpt'), per_device_train_batch_size=BATCH, learning_rate=1e-4,
        warmup_steps=min(1000, steps // 10), max_steps=steps, bf16=BF16, fp16=device == 'cuda' and not BF16,
        logging_steps=50, logging_first_step=True, save_steps=max(1, steps // 10), save_total_limit=2, report_to='none',
        remove_unused_columns=False, dataloader_num_workers=LOADERS, disable_tqdm=False, seed=0)
    trainer = Trainer(model=model, args=args, train_dataset=train, data_collator=Collator())
    trainer.train(resume_from_checkpoint=any((OUT / 'ckpt').glob('checkpoint-*')))
    trainer.save_model(str(final)); extractor.save_pretrained(str(final))
    (final / 'vocab.json').write_text(json.dumps(VOCAB, ensure_ascii=False, indent=1))
    del trainer
dev_rows = dev.select(range(min(2000, len(dev))))
save_report('dev PER (phoneme error rate, lower is better)', round(per([phones(t) for t in dev_rows['target']], predict(model, list(dev_rows))), 4))""")

code("""# QuranMB.v2: real recitations with human-marked mistakes. Detection is judged per expected phoneme:
# flagged = recognizer disagrees with the reference there; truly wrong = annotators disagree with the reference.
def wrong_positions(ref, said):
    bad = set()
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ref, said, autojunk=False).get_opcodes():
        if op != 'equal': bad.update(range(i1, max(i2, i1 + 1)))
    return bad

test = load_dataset('IqraEval/QuranMB.v2', split='test').cast_column('audio', Audio(sampling_rate=16000))
refs = {r['ID']: phones(r['Reference_phn']) for r in load_dataset('IqraEval/test_references', split='test')}
try:
    gt = load_dataset('IqraEval/IqraEval_Test_GT', split='test')
    print('ground-truth columns:', gt.column_names)
    col = 'Annotation_phn' if 'Annotation_phn' in gt.column_names else next(c for c in gt.column_names if 'annot' in c.lower())   # what was actually said, not Reference_phn
    said = {r['ID']: phones(r[col]) for r in gt}
except Exception as e:
    said = None; print('ground truth unavailable (accept terms at huggingface.co/datasets/IqraEval/IqraEval_Test_GT):', str(e)[:200])

rows = list(test)
pred = dict(zip([r['ID'] for r in rows], predict(model, rows)))
result = {'clips': len(rows)}
if said:
    ids = [i for i in pred if i in refs and i in said]
    result['PER_vs_actual'] = round(per([said[i] for i in ids], [pred[i] for i in ids]), 4)
    tp = fp = fn = 0
    for i in ids:
        truth, flag = wrong_positions(refs[i], said[i]), wrong_positions(refs[i], pred[i])
        tp += len(truth & flag); fp += len(flag - truth); fn += len(truth - flag)
    p, r = tp / max(1, tp + fp), tp / max(1, tp + fn)
    result.update(precision=round(p, 3), recall=round(r, 3), f1=round(2 * p * r / max(1e-9, p + r), 3),
                  true_mistake_phonemes=tp + fn, flagged_phonemes=tp + fp)
save_report('QuranMB.v2', result)""")

code("""# Export for the phone: ONNX fp32 + int8 (dynamic quantization). Core ML conversion happens on the Mac.
import subprocess, sys
subprocess.run([sys.executable, '-m', 'pip', '-q', 'install', 'onnxscript'], check=True)
import onnx
from onnxruntime.quantization import quantize_dynamic, QuantType
export = OUT / 'export'; export.mkdir(exist_ok=True)
m = Wav2Vec2ForCTC.from_pretrained(final).eval().float()
dummy = torch.zeros(1, 16000 * 4)
kwargs = dict(input_names=['audio'], output_names=['logits'], opset_version=17,
              dynamic_axes={'audio': {0: 'batch', 1: 'samples'}, 'logits': {0: 'batch', 1: 'frames'}})
try:
    torch.onnx.export(m, (dummy,), str(export / 'harakat.onnx'), dynamo=False, **kwargs)   # classic exporter
except Exception as e:
    print('classic exporter failed, using dynamo:', str(e)[:200])
    torch.onnx.export(m, (dummy,), str(export / 'harakat.onnx'), dynamo=True, **kwargs)
onnx.checker.check_model(str(export / 'harakat.onnx'))
quantize_dynamic(str(export / 'harakat.onnx'), str(export / 'harakat-int8.onnx'), weight_type=QuantType.QInt8)
(export / 'vocab.json').write_text(json.dumps(VOCAB, ensure_ascii=False, indent=1))

# Same audio through PyTorch and the int8 ONNX model must give (nearly) the same phonemes.
import onnxruntime as ort
sample = dev_rows[0]['audio']['array']
x = extractor([sample], sampling_rate=16000, return_tensors='pt').input_values
torch_ph = greedy(m(x).logits.detach())[0]
onnx_ph = greedy(torch.from_numpy(ort.InferenceSession(str(export / 'harakat-int8.onnx')).run(None, {'audio': x.numpy()})[0]))[0]
print('pytorch :', ' '.join(torch_ph)); print('int8    :', ' '.join(onnx_ph))
print('int8 phoneme agreement:', round(difflib.SequenceMatcher(None, torch_ph, onnx_ph).ratio(), 3))
for f in sorted(export.glob('*')): print(f'EXPORTED {f}  {f.stat().st_size / 1e6:.0f} MB')
print(json.dumps(json.loads(REPORTS.read_text()), indent=1))
""")



if __name__ == "__main__":
    cells = [{"cell_type": t, "metadata": {}, "source": s, **({"execution_count": None, "outputs": []} if t == "code" else {})}
             for t, s in CELLS]
    nb = {"cells": cells, "metadata": {"accelerator": "GPU", "colab": {"gpuType": "A100", "machine_shape": "hm"},
          "kernelspec": {"name": "python3", "display_name": "Python 3"}}, "nbformat": 4, "nbformat_minor": 5}
    out = Path(__file__).with_name("quran_harakat_colab.ipynb")
    out.write_text(json.dumps(nb, ensure_ascii=False, indent=1))
    import ast
    for t, s in CELLS:
        if t == "code": ast.parse("\n".join(l for l in s.split("\n") if not l.lstrip().startswith(("!", "%"))))
    print("wrote", out)
