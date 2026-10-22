# Pipes hindsight v3: joint suffix teacher and causal linear student

Локальная реализация, без платформы, старого Shinka и старого validation.
Default `model.hpp` имеет `ModelTrained=false`: solver точно повторяет BF из
скопированного `allocator.hpp`. Это отдельный kernel, не замороженный конкурсный
solver. До обучения и независимых paired rollouts улучшения не заявляются.

## Фиксированный рецепт до запуска

- Teacher читает только короткие официальные файлы `weight N command... 0`,
  `1 <= N <= 96`. Ноль не входит в N. Удаления должны ссылаться на live PID.
- Roll-in: causal BF. Eligible: `live <= 12`, `trench <= 160`, минимум два
  различных действия. Берутся первые 8 таких состояний, между выбранными не
  менее трёх placement events. Выбор зависит только от префикса; одинаковые
  префиксы разных продолжений дают одинаковые выбранные состояния.
- Domain <=8: BF первым; left/right endpoints первых трёх fitting gaps в
  порядке `(gap length, address)`; minimal-tail left/right. Точные дубликаты
  `(start,digs)` удаляются. Всегда сохраняется BF, endpoints входят без потерь:
  до добавления tail имеется не более шести уникальных fitting действий, так
  как BF уже совпадает с первым left endpoint.
- Для КАЖДОГО root action teacher выполняет beam search до конца файла.
  На КАЖДОЙ последующей укладке ветвятся те же <=8 действий; удаления заданы.
  Beam width=12, sorting: `(trench, 1000*gap_count + tiny_gap_penalty, physical_key)`;
  `tiny_gap_penalty = sum(max(0,8-gap_length))`. Dedup включает trench и все
  live `(PID,start,length)`. История команд/возрастов во всех ветках одинакова.
- Для каждого root отдельно сохраняется полный BF suffix вне beam. Label cost
  — минимум его final trench и beam final trench. Монотонная trench позволяет
  отсечь ветвь с trench > BF upper bound. Beam pruning не доказывает optimality.
- Train: все пары в одном состоянии с разницей final trench >=20; feature
  difference = better-minus-worse, fixed shared `scoringFeatures[128]`
  (`causal_cross128_v1`), без fitted scaling. State-only исходные гистограммы
  заменены interactions, чтобы они не сокращались в pair differences:
  0..39 = observed arrival frequency_n × integer lost packing capacity
  `[floor(h/n)-floor(left/n)-floor(right/n)]`; 40..79 = frequency_n × indicator
  `[max(left,right)<n<=h]`; 80..95 = contexts `(arrival_fraction, deletion_age<=32,
  same_run, occupancy)` × action `(digs, relative_address, left_fraction, gap_length)`;
  96..119 = исходная action geometry; 120..123 = deletion-age histogram ×
  relative_address, 124..127 = deletion-length histogram × tail_indicator.
  `h,left,right` считаются в метрах без clipping. Только прошлое из State.
  Logistic loss `mean_weighted(log(1+exp(-w·difference))) + .05/2*||w||²`,
  no intercept. Каждое информативное состояние получает одинаковый total weight.
  Fixed Newton: max40 steps, gradient infinity norm <1e-8; Armijo1e-4,
  max20 fixed halvings. Без подбора параметров и без dev/final input при fit.
- Нет информативных labels: emits zero weights, `ModelTrained=false`,
  `fit.status=fail_no_informative_labels`, exit3. Поведение BF-identical.
- Runtime: higher linear score, first candidate wins ties. Only eligible
  states; иначе BF. Default untrained и `HINDSIGHT_ENABLED=0` тоже используют BF.

## Интерфейсы

```sh
make -C prototypes/pipes_hindsight_v3_20261019/implementation
implementation/teacher --input stream.in --output labels.jsonl --stats stats.json
python3 implementation/train.py --labels-dir labels/train --out model
c++ -O2 -std=c++17 -DMODEL_HEADER='"/absolute/path/model/model.hpp"' implementation/solver.cpp -o candidate
c++ -O2 -std=c++17 -DHINDSIGHT_ENABLED=0 implementation/solver.cpp -o bf
```

Пути выше `implementation/...` относительны каталогу `pipes_hindsight_v3_20261019`.
Teacher принимает один файл за вызов; batch и квотный guard принадлежат вызывающему
коду. Выходные каталоги teacher должны уже существовать.

JSONL: одна строка на state, `command_index` zero-based, `placement_index`
one-based, `state_key/hash` physical, `observable_key/hash` prefix+physical+current length.
Hashes — FNV-1a64 для сопоставления; ключи тоже сохранены, collisions проверяются
по полному ключу. Текущая длина дана отдельно. `actions` содержит координаты,
`features[128]`, `cost`, `bf_suffix_cost`, `beam_best_cost` (-1 если beam пуст),
`used_reference`, counters и полный placement `witness` от root до конца.
`joint_improvement` означает, что хотя бы один root лучше своего BF suffix;
это не означает, что небазовый root лучше root BF или что student научился.
`alternative_root_better_states` сравнивает лучшие joint costs с joint cost BF root.
Counters `expanded/generated` учитывают future beam placement expansions,
не reference path и не forced root. `placement_layers/deletion_layers` —
число обработанных suffix layers, `completed` — сохранившиеся complete nodes.

`train.py` требует numpy. Он рекурсивно читает только `.jsonl` из указанного
labels-dir. Выход: `model.hpp`, `fit.json` с weights/recipe/training diagnostics,
`manifest.json` с SHA256 источников, label-файлов, модели и fit. Training pair
accuracy не является оценкой качества rollout. `feature_schema` проверяется
при fit, чтобы не смешать labels разных карт. Runtime не читает model files:
веса включаются compile-time, модель score — простой dot product.

Интерактивный solver получает одну команду без weight/N, отвечает и flush после
каждой команды. В stderr: placements, eligible, decisions, changed, fallback,
финальные T/F, trained/enabled. Сам solver не знает горизонт или future input.

Полноразмерный performance, official checker, independent transfer и promotion
gate должен проверить координатор. Teacher ограничен короткими потоками;
student намеренно возвращается к BF за пределами small-state domain.
