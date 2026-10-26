# Harakat teacher -> student. Run in the harakat notebook (same runtime as the earlier cells):
#   exec(open('/content/harakat_teacher_student.py').read())
# Needs from earlier cells: train, dev, VOCAB, ID, phones, greedy, per, Collator, extractor, OUT, BATCH, BF16, device,
# LOADERS, MAX_SECONDS, save_report, rows/refs/said (QuranMB.v2 cell), wrong_positions, ctc_align (GOP cell).
#
# 1. Teacher: facebook/w2v-bert-2.0 (MIT, 580M) + CTC on the same phonemes. No adapter, so its 20 ms frames line up
#    with the student's. About 1-1.5 h on an A100.
# 2. Student: the trained wav2vec2-base model (95M) continues training on gold labels + the teacher's per-frame
#    phoneme probabilities (knowledge distillation). About 30-45 min.
# Both are scored on QuranMB.v2 like before (free decoding and GOP) and the student is exported to ONNX int8.
# Every stage saves to Drive and is skipped on rerun once finished.
import gc, torch.nn.functional as F
from dataclasses import dataclass
from transformers import (Wav2Vec2BertForCTC, SeamlessM4TFeatureExtractor, Wav2Vec2ForCTC,
                          Trainer, TrainingArguments)

T_BASE = 'facebook/w2v-bert-2.0'
t_extractor = SeamlessM4TFeatureExtractor.from_pretrained(T_BASE)
TEACHER_DIR, STUDENT_DIR = OUT / 'teacher', OUT / 'student'

def keep_row(r):
    return 0.3 <= len(r['audio']['array']) / 16000 <= MAX_SECONDS and phones(r['target'])

def label_tensor(rows):
    ids = [[VOCAB[p] for p in phones(r['target']) if p in VOCAB] for r in rows]
    width = max(len(x) for x in ids)
    return torch.tensor([x + [-100] * (width - len(x)) for x in ids])

def teacher_inputs(arrays):
    return t_extractor(arrays, sampling_rate=16000, return_tensors='pt', padding=True)

def student_inputs(arrays):
    x = extractor(arrays, sampling_rate=16000, return_tensors='pt', padding=True); x.pop('attention_mask', None)
    return x

@dataclass
class TeacherCollator:
    def __call__(self, rows):
        rows = [r for r in rows if keep_row(r)] or rows[:1]
        batch = teacher_inputs([r['audio']['array'] for r in rows])
        batch['labels'] = label_tensor(rows)
        return batch

def log_probs(m, kind, audio):
    # One clip -> (frames, vocab) log-probabilities as numpy.
    x = teacher_inputs([audio]) if kind == 'teacher' else student_inputs([audio])
    x = {k: v.to(device) for k, v in x.items()}
    with torch.no_grad(), torch.autocast(device, dtype=torch.bfloat16, enabled=BF16):
        logits = m(**x).logits.float()[0]
    return F.log_softmax(logits, -1).cpu().numpy()

def decode(lp):
    out, prev = [], None
    for t in lp.argmax(-1):
        if t != prev and t != 0: out.append(ID[int(t)])
        prev = t
    return out

def score_quranmb(m, kind, name):
    # Free decoding P/R/F1 + GOP sweep on QuranMB.v2, same rules as the earlier cells.
    m = m.to(device).eval()
    preds, gops, truths = {}, [], []
    for r in tqdm(rows, desc=f'{name} QuranMB.v2'):
        i = r['ID']
        if i not in refs or i not in said: continue
        lp = log_probs(m, kind, r['audio']['array'])
        preds[i] = decode(lp)
        keep = [j for j, p in enumerate(refs[i]) if p in VOCAB]
        tgt = np.array([VOCAB[refs[i][j]] for j in keep])
        path = ctc_align(lp, tgt) if len(tgt) else None
        if path is None: continue
        sc = np.full(len(refs[i]), np.nan)
        for k, j in enumerate(keep):
            frames = np.where(path == 2 * k + 1)[0]
            if len(frames): sc[j] = float(np.mean(lp[frames, tgt[k]] - lp[frames].max(1)))
        gops.append(sc); truths.append(wrong_positions(refs[i], said[i]))
    ids = list(preds)
    tp = fp = fn = 0
    for i in ids:
        truth, flag = wrong_positions(refs[i], said[i]), wrong_positions(refs[i], preds[i])
        tp += len(truth & flag); fp += len(flag - truth); fn += len(truth - flag)
    p, rc = tp / max(1, tp + fp), tp / max(1, tp + fn)
    result = {'PER_vs_actual': round(per([said[i] for i in ids], [preds[i] for i in ids]), 4),
              'free': {'precision': round(p, 3), 'recall': round(rc, 3), 'f1': round(2 * p * rc / max(1e-9, p + rc), 3)}}
    total = sum(len(t) for t in truths); best = None
    for th in [0.5, 1, 1.5, 2, 3, 4, 6, 8]:
        tp = fp = 0
        for sc, truth in zip(gops, truths):
            flags = {j for j, v in enumerate(sc) if not np.isnan(v) and v < -th}
            tp += len(flags & truth); fp += len(flags - truth)
        p, rc = tp / max(1, tp + fp), tp / max(1, total)
        f1 = 2 * p * rc / max(1e-9, p + rc)
        print(f'  {name} GOP {th:>4}: precision {p:.2f} recall {rc:.2f} F1 {f1:.2f}')
        if best is None or f1 > best['f1']: best = {'threshold': th, 'precision': round(p, 3), 'recall': round(rc, 3), 'f1': round(f1, 3)}
    result['gop_best'] = best
    save_report(f'QuranMB.v2 {name}', result)
    return result

# ---------------- 1. Teacher ----------------
gc.collect(); torch.cuda.empty_cache()   # release memory left by earlier cells
import shutil
for ck in (TEACHER_DIR / 'ckpt').glob('checkpoint-*/trainer_state.json'):
    if json.loads(ck.read_text()).get('train_batch_size') != (16 if VRAM >= 40 else 4):
        print('old-settings teacher checkpoints moved aside'); shutil.move(str(TEACHER_DIR / 'ckpt'), str(TEACHER_DIR / 'ckpt_old')); break
if (TEACHER_DIR / 'model' / 'config.json').exists():
    print('teacher already trained'); teacher = Wav2Vec2BertForCTC.from_pretrained(TEACHER_DIR / 'model')
else:
    teacher = Wav2Vec2BertForCTC.from_pretrained(
        T_BASE, vocab_size=len(VOCAB), pad_token_id=0, ctc_loss_reduction='mean', ctc_zero_infinity=True,
        add_adapter=False, layerdrop=0.0, mask_time_prob=0.05, ignore_mismatched_sizes=True)
    # Attention memory grows with clip length squared: 16 per step x 2 accumulated = effective 32, no checkpointing.
    t_batch, t_accum = (16, 2) if VRAM >= 40 else (4, 8)
    steps = min(12000, int(len(train) * 2 / (t_batch * t_accum)))
    args = TrainingArguments(output_dir=str(TEACHER_DIR / 'ckpt'), per_device_train_batch_size=t_batch, gradient_accumulation_steps=t_accum,
        learning_rate=5e-5, warmup_steps=min(800, steps // 10), max_steps=steps, bf16=BF16,
        fp16=device == 'cuda' and not BF16, gradient_checkpointing=False, logging_steps=50, logging_first_step=True,
        save_steps=max(1, steps // 10), save_total_limit=2, report_to='none', remove_unused_columns=False,
        dataloader_num_workers=LOADERS, dataloader_prefetch_factor=4, dataloader_persistent_workers=True,
        dataloader_pin_memory=True, disable_tqdm=False, seed=0)
    trainer = Trainer(model=teacher, args=args, train_dataset=train, data_collator=TeacherCollator())
    trainer.train(resume_from_checkpoint=any((TEACHER_DIR / 'ckpt').glob('checkpoint-*')))
    trainer.save_model(str(TEACHER_DIR / 'model')); t_extractor.save_pretrained(str(TEACHER_DIR / 'model'))
    del trainer; gc.collect(); torch.cuda.empty_cache()
done = json.loads(REPORTS.read_text()) if REPORTS.exists() else {}
if 'QuranMB.v2 teacher' not in done: score_quranmb(teacher, 'teacher', 'teacher')

# ---------------- 2. Student (distillation) ----------------
@dataclass
class DistillCollator:
    def __call__(self, rows):
        rows = [r for r in rows if keep_row(r)] or rows[:1]
        arrays = [r['audio']['array'] for r in rows]
        batch = student_inputs(arrays)
        t = teacher_inputs(arrays)
        batch['t_features'], batch['t_mask'] = t['input_features'], t['attention_mask']
        batch['labels'] = label_tensor(rows)
        return batch

class DistillTrainer(Trainer):
    # loss = CTC on gold labels + KL to the teacher's per-frame phoneme distribution (temperature 2).
    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        t_features, t_mask = inputs.pop('t_features'), inputs.pop('t_mask')
        out = model(**inputs)
        with torch.no_grad():
            t_logits = teacher(input_features=t_features, attention_mask=t_mask).logits.float()
        s_logits = out.logits.float()
        n = min(t_logits.shape[1], s_logits.shape[1])
        temp = 2.0
        kd = F.kl_div(F.log_softmax(s_logits[:, :n] / temp, -1), F.log_softmax(t_logits[:, :n] / temp, -1),
                      log_target=True, reduction='batchmean') * temp ** 2 / n
        loss = out.loss + 0.5 * kd
        return (loss, out) if return_outputs else loss

if (STUDENT_DIR / 'model' / 'config.json').exists():
    print('student already trained'); student = Wav2Vec2ForCTC.from_pretrained(STUDENT_DIR / 'model')
else:
    teacher = teacher.to(device, torch.bfloat16 if BF16 else torch.float32).eval()
    student = Wav2Vec2ForCTC.from_pretrained(OUT / 'model')          # start from the first phoneme model
    student.freeze_feature_encoder()
    steps = min(8000, int(len(train) * 1.5 / BATCH))
    args = TrainingArguments(output_dir=str(STUDENT_DIR / 'ckpt'), per_device_train_batch_size=BATCH,
        learning_rate=5e-5, warmup_steps=min(500, steps // 10), max_steps=steps, bf16=BF16,
        fp16=device == 'cuda' and not BF16, logging_steps=50, logging_first_step=True,
        save_steps=max(1, steps // 10), save_total_limit=2, report_to='none', remove_unused_columns=False,
        dataloader_num_workers=LOADERS, dataloader_prefetch_factor=4, dataloader_persistent_workers=True,
        dataloader_pin_memory=True, disable_tqdm=False, seed=0)
    trainer = DistillTrainer(model=student, args=args, train_dataset=train, data_collator=DistillCollator())
    trainer.train(resume_from_checkpoint=any((STUDENT_DIR / 'ckpt').glob('checkpoint-*')))
    trainer.save_model(str(STUDENT_DIR / 'model')); extractor.save_pretrained(str(STUDENT_DIR / 'model'))
    (STUDENT_DIR / 'model' / 'vocab.json').write_text(json.dumps(VOCAB, ensure_ascii=False, indent=1))
    del trainer; gc.collect(); torch.cuda.empty_cache()
done = json.loads(REPORTS.read_text()) if REPORTS.exists() else {}
if 'QuranMB.v2 student' not in done: score_quranmb(student, 'student', 'student')

# ---------------- 3. Export the student for the phone ----------------
import subprocess, sys
subprocess.run([sys.executable, '-m', 'pip', '-q', 'install', 'onnxscript'], check=True)
import onnx
from onnxruntime.quantization import quantize_dynamic, QuantType
export = STUDENT_DIR / 'export'; export.mkdir(exist_ok=True)
sm = Wav2Vec2ForCTC.from_pretrained(STUDENT_DIR / 'model').eval().float()
torch.onnx.export(sm, (torch.zeros(1, 16000 * 4),), str(export / 'harakat.onnx'), dynamo=False, input_names=['audio'],
                  output_names=['logits'], opset_version=17,
                  dynamic_axes={'audio': {0: 'batch', 1: 'samples'}, 'logits': {0: 'batch', 1: 'frames'}})
onnx.checker.check_model(str(export / 'harakat.onnx'))
quantize_dynamic(str(export / 'harakat.onnx'), str(export / 'harakat-int8.onnx'), weight_type=QuantType.QInt8)
(export / 'vocab.json').write_text(json.dumps(VOCAB, ensure_ascii=False, indent=1))
for f in sorted(export.glob('*')): print(f'EXPORTED {f}  {f.stat().st_size / 1e6:.0f} MB')
r = json.loads(REPORTS.read_text())
for k in ['QuranMB.v2', 'QuranMB.v2 GOP (forced alignment)', 'QuranMB.v2 teacher', 'QuranMB.v2 student']:
    print(k, r.get(k))
