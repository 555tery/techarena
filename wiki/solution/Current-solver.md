# Замороженный алгоритм

## Что зафиксировано

Основной воспроизводимый артефакт — [`results/pipes/final/solution.cpp`](../../results/pipes/final/solution.cpp), SHA-256 начинается `c4b737b9` и заканчивается `32a991`. Его Open15 результат — `29.789717928594 / 32.1`, 15/15. Подробные хеши, compiler flags, ресурсы и результаты holdout-v2 записаны в [`final/README.md`](../../results/pipes/final/README.md) и [`manifest.json`](../../results/pipes/final/manifest.json).

В этом варианте используется corrected Monte Carlo и причинное переключение стороны размещения по уже наблюдавшейся серии труб одной длины; будущее не читается. Точное поведение и ограничения метода описаны в final README и исходнике.

## Чего не следует смешивать

- [`src/pipes.cpp`](../../src/pipes.cpp) — canonical source проекта, отдельная копия и другой SHA.
- [`results/pipes/final/solution.cpp`](../../results/pipes/final/solution.cpp) — закреплённая frozen-final версия.
- Run-48 — отдельная версия с порогом серии `46→48`, score `29.790219562101` на локальном Open15. Она отправлялась на платформу до просьбы остановить отправки.
- PID-parity preprobe — незавершённая квалификация. Результат не установлен и в frozen final он не включён.

## Версия описаний

[`docs/ALGORITHM.md`](../../docs/ALGORITHM.md) описывает старый T46, не этот замороженный алгоритм. Сверяй версию по SHA, а не по одному слову «финальный» в старых заметках.
