# Shadow expert portfolio — preregistration

Дата: 2026-10-17. Проверяется только локально на macOS native / Apple Clang и официальном `tools/pipes_harness.py`; Docker, сайт и отправки исключены.

## Архитектурная проверка и эксперты

Macro-policy search вмешивался в заранее выбранные интервалы одного прогона и сравнивал простые правила; это не continuous expert feedback по параллельным полным shadow-state. Кандидат `run-48` меняет только `kSameLengthRightRun:46→48`; он слишком близок к frozen final для второго эксперта. Выбран **PID/46** (`1a643a2b…f55f59`): в длинной серии одинакового размера он выбирает край по PID parity вместо size-local occurrence parity, причём меняется live allocator и его rollout copy. Источники: `results/pipes/final/solution.cpp` SHA `c4b737b9…32a991`; PID/46 из `results/pipes/improvement/case9_next/preliminary_pid_lane_excluded/source/proactive_pid_lanes_preprobe.cpp` SHA `1a643a2b…f55f59`. Его прежний перенос на 6 новых потоков был нейтральным; это challenger, не прогноз победы.

Три состояния: frozen shadow, PID/46 shadow и реальное размещение. Все получают текущие команды/точные PID удаления. На вставке до обработки команды выбирается эксперт по текущим весам; его lane rule заново вычисляется на **реальных** gaps, shadow-координаты не копируются. Каждый shadow независимо исполняет свою политику и оценивает цену `ΔT/40` по дополнительному копанию. Для selector заранее фиксируются `η=0.05`, `α=1/1024`, начальные веса `(0.5,0.5)`, fixed-share update и sampling PRNG xorshift32 seed `0x51A0D00D`. Цена измеряется на каждой команде, у удаления `ΔT=0`; feedback этой команды влияет лишь на следующий выбор.

## Синтетический matrix

36 потоков: 6 семейств × 3 размера (`5k`, `50k`, `200k` команд) × 2 независимых seed. Семейства: uniform/random; short-heavy/FIFO; long-heavy/newest; sticky bimodal/oldest; short→long со сменой удаления; long→short со сменой удаления. Для каждого family-size-replicate seed задаётся формулой `8710230000 + family*1000000 + size*1000 + replicate`. Генератор — ранее использованный причинный Python generator из `run48_synthetic_independent`; до solver runs проверить непересечение seed с input-manifests и SHA-256 входов со всеми сохранёнными `data/pipes` и `results/pipes` `.in`.

## Заранее заданный gate

Единица анализа — поток с весом 1; `Δ = portfolio KPI − frozen KPI`. Primary metric — среднее Δ с равным весом шести семейств. Stratified paired percentile bootstrap: 20,000 resamples, фиксированный seed `87102317`, внутри каждого семейства выбирать с возвращением 6 парных потоков из 6. Gate проходит, только если средний Δ положителен и нижняя граница 95% интервала строго выше 0. Дополнительно: сравнить по каждому размеру и семейству; отдельно проверить точное совпадение shadow trench каждого эксперта с его official-harness результатом на тех же потоках. Любой shadow mismatch делает screen недействительным. Ограничения 5 CPU-с / 256 MiB записать по всем case rows; resource failure означает провал, но не является ранним фильтром. До gate не запускать Open15/holdout-v2.
