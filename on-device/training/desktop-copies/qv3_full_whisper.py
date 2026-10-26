# Whisper "full" model: run AFTER qv3.py finishes, in the same runtime (reuses full_mix, eval_syn, train, export...).
#   exec(open('/content/qv3_full_whisper.py').read())
# whisper-large-v3-turbo (MIT, 809M) on the same verbatim data. Too big for older phones; fits a server or
# high-end phone (q5_0 about 550 MB). The base/tiny models stay the mobile ones.
FULL = 'openai/whisper-large-v3-turbo'
mobile_batch = BATCH
BATCH = 24 if VRAM >= 40 else 8          # 809M params: smaller batches than base
try:
    STAGE_FULL = train(FULL, full_mix, OUT / 'stage4_full', steps_for(len(full_mix), 1.5, 9000), 1e-5)
finally:
    BATCH = mobile_batch
done = json.loads(REPORTS.read_text()) if REPORTS.exists() else {}
if 'BASELINE full' not in done: spliced_report(load(FULL), processor_for(FULL), eval_syn, 'BASELINE full')
spliced_report(load(STAGE_FULL), processor_for(STAGE_FULL), eval_syn, 'STAGE 4 full')
real_report(load(STAGE_FULL), processor_for(STAGE_FULL), 'REAL stage4 full')
# The converter needs the original vocab files; copy them from the turbo repo, not Tarteel's base.
from huggingface_hub import hf_hub_download
for name in ['vocab.json', 'added_tokens.json']:
    if not (Path(STAGE_FULL) / name).exists(): shutil.copy(hf_hub_download(FULL, name), Path(STAGE_FULL) / name)
export(STAGE_FULL, OUT / 'stage4_full')
