#!/usr/bin/env python3
"""Package all frozen inputs and sources; no Windows execution is claimed."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    data = json.loads((HERE / "analysis.json").read_text())
    assert data["complete"] and data["hybrid_cpp_cj_parity"]["identical"] == 2637
    frozen = json.loads((HERE / "freeze.json").read_text())
    target = HERE / "windows-package"
    target.mkdir()
    for source, name in [
        (HERE / "methods/online_cj/solution.cj", "online.cj"),
        (HERE / "methods/hybrid_cj/solution.cj", "hybrid.cj"),
        (HERE / "methods/hybrid_cpp/solution.cpp", "hybrid.cpp"),
        (ROOT / "prototypes/pipes_cangjie_port_20261020/release/windows_bench.py", "windows_bench.py"),
        (HERE / "windows_compare.py", "windows_compare.py"),
        (HERE / "build_windows.bat", "build_windows.bat"),
    ]:
        shutil.copy2(source, target / name)
    (target / "tests").mkdir()
    cases = []
    for c in frozen["cases"]:
        name = f"tests/{c['id']}.in"
        shutil.copy2(HERE / c["input"], target / name)
        assert sha(target / name) == c["input_sha256"]
        cases.append(dict(id=c["id"], path=name, input_sha256=c["input_sha256"],
                          cohort=c["cohort"], selected=c["selected"], public_number=c["public_number"],
                          weight=c["meta"]["weight"], operations=c["meta"]["operation_count"],
                          name=c["name"], family=c["family"]))
    manifest = dict(freeze_sha256=sha(HERE / "freeze.json"), count=len(cases), cases=cases)
    (target / "tests_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    expected = {
        c["id"]: {m: {"response_sha256": r["normalized_response_sha256"], "T": r["trench_length_m"],
                       "KPI": r["raw_kpi"]}
                  for m, r in c["methods"].items()}
        for c in data["per_case"]
    }
    (target / "expected_results.json").write_text(json.dumps(expected, indent=2) + "\n")
    readme = """Осторожный гибрид на нынешнем online и чистый online: Windows-проверка

Содержимое: hybrid.cj, online.cj, эталон hybrid.cpp; все 2637 потоков
(2537 архивных + 4 дополнительных Open15 + 96 новых).
На macOS официальный интерактор проверил все варианты; ожидаемые хеши полных
ответов, T и KPI приведены в expected_results.json. Windows здесь не запускался.

Нужны уже установленные Python 3 и Cangjie SDK. Локальная сборка использовала
Cangjie 1.2.0 -O2; версия SDK организаторов неизвестна. Нужен C++ компилятор
для эталона. build_windows.bat ничего не устанавливает.

1. Открыть shell с настроенным Cangjie SDK и C++ компилятором.
2. Выполнить build_windows.bat.
3. py -3 windows_compare.py --out windows-results.json
   Продолжение: добавить --resume. Для выбора CPU: --cpu 0.

Runner запускает по одному процессу, закрепляет его на одном разрешённом
логическом CPU до старта. cjProcessorNum=1. Считает весь CPU user+kernel
включая GC и завершение, без деления на число ядер. Проверяет физику каждого
ответа независимым checker, сравнивает hybrid C++/CJ и Mac эталон.
Лимиты: CPU <5 s, память <256 MiB. Измеряет peak working set и private
commit; если полные счётчики недоступны, пишет unconfirmed, а не pass.
Времена ожидания не являются CPU time. Жёсткие лимиты не навязываются;
превышения получают ноль в adjusted KPI. Неподтверждённые ресурсы также
отмечены отдельно и не считаются доказанным попаданием в лимиты.

Сначала дождаться полного результата на Pentium G5420/Windows 10.
Результаты Mac нельзя пересчитывать по частоте процессора.
Этот пакет не отправляет решения и не взаимодействует с платформой.
"""
    (target / "README.txt").write_text(readme)
    inventory = {str(p.relative_to(target)): sha(p) for p in sorted(target.rglob("*")) if p.is_file()}
    (target / "package_sha256.json").write_text(json.dumps(inventory, indent=2) + "\n")
    archive = HERE / "current-hybrid-cangjie-windows.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=3) as z:
        for p in sorted(target.rglob("*")):
            if p.is_file():
                z.write(p, str(Path("current-hybrid") / p.relative_to(target)))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
    print(json.dumps({"files": len(inventory) + 1, "tests": len(cases), "zip_bytes": archive.stat().st_size,
                      "zip_sha256": sha(archive)}))

if __name__ == "__main__":
    main()
