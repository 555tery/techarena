#!/usr/bin/env python3
"""Продвижение победителя прогона в базовую задачу (для research_loop.sh).

Читает best_program_manifest.json завершённого прогона: если кандидат помечен
correct=true и его combined_score больше текущей базы (файл .baseline_score),
копирует исходники кандидата в tasks/pipes/program_0 (с полным бэкапом старой
версии), обновляет .baseline_score и пишет строку в .promotions.log.

Запуск:  promote_best.py --run-dir <каталог прогона> [--dry-run]
Коды выхода: 0 — ок (в т.ч. когда продвигать нечего); 1 — ошибка чтения/копии.
"""
import argparse
import datetime
import json
import shutil
import sys
from pathlib import Path


def log(msg: str) -> None:
    print(f"[promote] {msg}", flush=True)


def read_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def utc_stamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")


def main() -> int:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--task-dir", default=str(here / "tasks" / "pipes"))
    ap.add_argument("--score-file", default=str(here / ".baseline_score"))
    ap.add_argument("--backup-dir", default=str(here / ".baseline_backups"))
    ap.add_argument("--promotions-log", default=str(here / ".promotions.log"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    run = Path(a.run_dir)
    inv = run / "investigation"
    manifest_p = inv / "best_program_manifest.json"
    outer_p = inv / "outer_state.json"

    program_dir = score = correct = attempt = entry_rel = None
    if manifest_p.exists():
        m = read_json(manifest_p)
        program_dir = m.get("program_dir")
        score = m.get("combined_score")
        correct = m.get("correct")
        attempt = m.get("source_attempt_id")
        entry_rel = m.get("entrypoint_path")
    if (program_dir is None or score is None) and outer_p.exists():
        o = read_json(outer_p)
        program_dir = program_dir or o.get("best_program_dir")
        score = score if score is not None else o.get("best_combined_score")
        correct = correct if correct is not None else o.get("best_correct")
    entry_rel = entry_rel or "src/pipes.cpp"

    if program_dir is None or score is None:
        log(f"в прогоне нет записи о лучшей программе ({run}) — пропускаю")
        return 0

    sf = Path(a.score_file)
    if not sf.exists():
        log(f"нет файла базового скора {sf} — пропускаю (инициализируй явно)")
        return 1
    base = float(sf.read_text(encoding="utf-8").strip())
    try:
        score_f = float(score)
    except (TypeError, ValueError):
        log(f"некорректный скор в манифесте: {score!r} — пропускаю")
        return 1

    if not correct:
        log(f"кандидат помечен correct={correct!r} — не продвигаю")
        return 0
    if score_f <= base + 1e-9:
        log(f"улучшения нет: кандидат {score_f!r} <= база {base!r}")
        return 0

    cand = Path(program_dir)
    cand_src = cand / "src"
    entry_path = cand / entry_rel
    if not entry_path.is_file():
        log(f"у кандидата нет файла входа {entry_path} — не продвигаю")
        return 1

    task = Path(a.task_dir) / "program_0"
    tgt_src = task / "src"
    ts = utc_stamp()

    log(f"ПОБЕДИТЕЛЬ: {score_f!r} > база {base!r} (attempt {attempt})")
    log(f"  кандидат: {cand}")

    if a.dry_run:
        log("  dry-run: файлы не трогаю")
        return 0

    # 1) полный бэкап текущей базы
    bdir = Path(a.backup_dir)
    bdir.mkdir(parents=True, exist_ok=True)
    bpath = bdir / f"program_0_{ts}"
    shutil.copytree(task, bpath)
    log(f"  бэкап базы: {bpath}")

    # 2) копируем исходники кандидата (src/* и program_spec.toml, если есть)
    tgt_src.mkdir(parents=True, exist_ok=True)
    copied = []
    for f in sorted(cand_src.iterdir()):
        if f.is_file():
            shutil.copy2(f, tgt_src / f.name)
            copied.append(f"src/{f.name}")
        elif f.is_dir():
            dst = tgt_src / f.name
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(f, dst)
            copied.append(f"src/{f.name}/")
    spec = cand / "program_spec.toml"
    if spec.is_file():
        shutil.copy2(spec, task / "program_spec.toml")
        copied.append("program_spec.toml")
    log(f"  скопировано в {task}: {', '.join(copied)}")

    # 3) новый базовый скор + журнал продвижений
    sf.write_text(f"{score_f!r}\n", encoding="utf-8")
    with open(a.promotions_log, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "run_dir": str(run),
            "score_old": base,
            "score_new": score_f,
            "source_attempt_id": attempt,
            "program_dir": str(cand),
            "backup": str(bpath),
            "copied": copied,
        }, ensure_ascii=False) + "\n")
    log(f"новая база: {score_f!r} (записано в {sf})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
