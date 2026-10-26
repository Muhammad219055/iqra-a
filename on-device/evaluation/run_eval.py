"""Runs the native whisper.cpp CLI on every manifest clip and writes results.json. Silent: file inference only.
Run: .venv/bin/python on-device/evaluation/run_eval.py"""
import hashlib
import json
import platform
import subprocess
import time

from common import EVAL, ROOT, judge, words

CLI = ROOT / "on-device/build-mac/bin/whisper-cli"
MODEL = ROOT / "on-device/models/ggml-model.bin"
# Native engine: greedy, Arabic, temperature 0 with no fallback, no context, CPU. -ng keeps the Mac on CPU.
FLAGS = ["-l", "ar", "-t", "4", "-bs", "1", "-bo", "1", "-nf", "-nt", "-np", "-ng", "-oj"]


def summarize(clips, results):
    """Verdict counts, word errors and Mac CLI timing, split by category, speaker and synthetic/original."""
    by_id = {c["id"]: c for c in clips}
    groups = {}
    for r in results:
        if r["status"] != "ok": continue
        c = by_id[r["id"]]
        g = groups.setdefault(f"{c['category']} · {c['speaker']} · {'synthetic' if c['synthetic'] else 'original'}",
                              {"clips": 0, "verdicts": {}, "audible_words": 0, "word_errors": 0, "rtf": []})
        v = r["score"]; g["clips"] += 1
        g["verdicts"][v["verdict"]] = g["verdicts"].get(v["verdict"], 0) + 1
        g["audible_words"] += len(c["audible_words"])
        g["word_errors"] += v["vs_audible"]["sub"] + v["vs_audible"]["del"] + v["vs_audible"]["ins"]
        g["rtf"].append(r["real_time_factor"])
    for g in groups.values():
        g["wer_vs_audible"] = round(g["word_errors"] / max(1, g["audible_words"]), 3)
        g["mac_cli_rtf_median"] = sorted(g.pop("rtf"))[g["clips"] // 2]
    return dict(sorted(groups.items()))


def main():
    lock = json.loads((ROOT / "on-device/model-lock.json").read_text())
    model_sha = hashlib.sha256(MODEL.read_bytes()).hexdigest()
    assert model_sha == lock["sha256"], "model does not match model-lock.json"
    manifest = json.loads((EVAL / "manifest.json").read_text())
    out_dir = EVAL / "raw"; out_dir.mkdir(exist_ok=True)
    results = []
    for entry in manifest["clips"]:
        prefix = out_dir / entry["id"]
        cmd = [str(CLI), "-m", str(MODEL), "-f", str(ROOT / entry["path"]), *FLAGS, "-of", str(prefix)]
        started = time.perf_counter()
        run = subprocess.run(cmd, capture_output=True, text=True)
        wall = time.perf_counter() - started
        row = {"id": entry["id"], "exit_code": run.returncode, "wall_seconds": round(wall, 3),
               "real_time_factor": round(wall / max(entry["seconds"], 1e-6), 3)}
        try:
            assert run.returncode == 0, run.stderr[-400:]
            data = json.loads(prefix.with_suffix(".json").read_text())
            text = " ".join(seg["text"].strip() for seg in data.get("transcription", []))
            hyp = words(text)
            row.update(status="ok", text=text, normalized=hyp, score=judge(entry, hyp))
        except Exception as error:  # every manifest entry gets a row, failures included
            row.update(status="failed", error=str(error)[-400:])
        results.append(row)
        print(f"{row['id']:<32} {row['status']:<6} {row.get('score', {}).get('verdict', '-'):<18} {row['wall_seconds']:>6}s  {row.get('text', '')}")
    cpu = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip()
    report = {
        "run": {"command_template": [str(CLI.relative_to(ROOT)), "-m", str(MODEL.relative_to(ROOT)), "-f", "<clip>", *FLAGS, "-of", "<prefix>"],
                "model": lock, "model_sha256_verified": model_sha,
                "platform": f"Mac CLI: {platform.platform()} · {cpu}",
                "timing_note": "Wall-clock per CLI process, including model load. Mac CLI only, not iPhone performance.",
                "manifest_entries": len(manifest["clips"]), "completed": sum(r["status"] == "ok" for r in results),
                "failed": [r["id"] for r in results if r["status"] != "ok"]},
        "results": results,
    }
    report["summary"] = summarize(manifest["clips"], results)
    (EVAL / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
    print(f"completed {report['run']['completed']}/{len(manifest['clips'])}; failed: {report['run']['failed']}")


if __name__ == "__main__":
    main()
