# Bayesian latent-regime MPC — preregistration

## Проверяемое отличие

Frozen MC и policy-conditioned rollout продолжают действия отрезками прошлых событий, выбранными по совпавшему suffix context. Markov/transition, flow-predictor и regime-gate эксперименты меняют эмпирический прогноз или правило по локальным частотам, но не строят posterior по скрытой точке смены и не генерируют будущий suffix из этого posterior. Здесь проверяется именно другой forecast kernel: Bayesian online changepoint detection (BOCPD) с categorical Dirichlet-multinomial predictive model, подключённый к существующему bounded gap-rollout.

## Алгоритм и фиксированные ограничения

- Наблюдаемое событие `x∈{0,…,47}`: вставка длины `L` кодируется `L−1`; удаление кодируется квантилем ранга PID от newest в 8 bins. PID/rank вычисляется только из уже известного активного набора.
- BOCPD поддерживает posterior `P(run_length | prefix)` с максимумом run-length 128 и постоянным hazard `h`, выбранным только на synthetic training streams. Для каждой гипотезы run-length predictive `P(x)` — Dirichlet-multinomial с prior `κ·p0`; `p0` — pooled empirical frequencies train streams с Laplace `+1` по каждой из 48 категорий. Выбираются только `h∈{1/128,1/512,1/2048}` и `κ∈{8,32}` по среднему prequential log-loss с leave-one-stream-out `p0`; равенство разрешается меньшим hazard, затем большим κ. После выбора `p0` финально пересчитывается на всех train streams. Никаких official/holdout потоков для обучения.
- На каждой вставке модель сначала получает текущую известную длину, затем rollout прогнозирует следующие 4 команды. Для каждой из существующих top-3 feasible gap candidates используются 12 общих детерминированных trajectories; начальный run-length семплируется из posterior, новые события — из Dirichlet posterior predictive, смена latent regime — с hazard `h`. При пустом active set прогноз условно ограничен категориями вставки.
- Сохраняются существующие frozen candidate filter, gap ranking, `kMcDecisionBudget=32`, rollout depth 4, trial count 12 и правило принятия. Меняется только источник будущих event sequences внутри изолированной копии. Не читаются номер теста, полный вход или будущие команды. Frozen final и canonical не меняются.

## Данные

Сценарии создаются тем же ранее проверенным причинным synthetic generator `results/pipes/improvement/run48_synthetic_independent/generate_streams.py`; точные сценарии и SHA входов будут в `input_manifest.json`. Seeds проверяются на совпадение во всех прежних JSON manifests и SHA входов — среди `data/pipes` и сохранённых `results/pipes`.

**Train/tune:** 8 независимых потоков по 16,384 операции — uniform/random, short-heavy/oldest, long-heavy/newest, bimodal/shortest, short→long с изменением удаления, long→short с изменением удаления, uniform с oldest→newest deletion shift, short-heavy/random. Seed формула: `9801600000 + profile_index*1000 + replicate`, `profile_index=0..7`, `replicate=0`.

**Fresh validation:** 7 семейств × 2 размера (16,384 и 200,000) × 2 независимых seed = 28 потоков. Семейства: uniform/random; short-heavy/FIFO; long-heavy/newest; bimodal/shortest; short→long с random→oldest; long→short с newest→longest; uniform/FIFO→newest. Seed формула: `9802700000 + family_index*1000000 + size_index*1000 + replicate`, `size_index=0` для 16,384 и `1` для 200,000; `replicate=0,1`.

## Gate до holdout/Open15

Сравнение paired с байт-в-байт frozen final, единица — поток. Primary metric: среднее `candidate KPI − frozen KPI` с равным весом 28 потоков. CI — 20,000 paired percentile bootstrap повторов, stratified по `family × size`, seed `9801702026`; в каждой из 14 страт повторно выбираются два потока с возвращением. Gate проходит только если средний прирост положителен, нижняя 95% CI выше нуля, mean Δ KPI на 200k неотрицателен, не менее 5 из 7 family mean Δ неотрицательны, все 28 paired harness cases валидны и ресурсы не превышают 5 CPU-с / 256 MiB. При fail — остановка; holdout-v2 и Open15 не запускать.

После обучения/выбора параметров фиксируются candidate source SHA и все validation input SHA до первого validation run. Параметры после этого не меняются.
