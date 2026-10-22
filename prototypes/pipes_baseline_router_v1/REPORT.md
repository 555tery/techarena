# Маршрутизатор поверх baseline: no-go

17 октября 2026. Работа завершена локально. **Маршрутизатор обучен и отклонён; улучшения до 30.5 нет.** Сохранённый lab baseline остаётся основным вариантом. Платформа, рейтинг и отправки не использовались.

## Результат полного алгоритма

| Вариант | Локальный Open15 / 32.1 | Case 15, м |
|---|---:|---:|
| Исходный baseline | 30.074287976406 | 438,640 |
| Тот же baseline с отключённым router | 30.074287976406 | 438,640 |
| Активный обученный router | 29.995671715360 | 438,740 |

Активный кандидат проиграл baseline **0.078616261046 score**, в case 15 — **+100 м**. Open15: 0 побед, 5 поражений, 10 равенств. Ухудшились cases 8/11/12/13/15. Это единственный post-freeze Open15 diagnostic; после него модель, gates, routes и margin не менялись.

Сильные правила сохранены в коде, но ранние fallback решения меняют последующую геометрию. Поэтому само сохранение веток не гарантирует исходный score активного router. Отключённый router точно сохранил baseline.

## Почему архитектура отличается от прошлого прототипа

В learned-v1 одновременно появились общее best-fit ядро и сеть. Абляция позволила оценить сеть отдельно, однако замена ядра убрала сильные правила lab baseline и плохо подходила для улучшения именно его. Здесь fork механически построен из **точного c1994511…bb736c**, а не из нового allocator.

Hook стоит после штатного выбора gap/side и Monte Carlo, перед потреблением свободного промежутка. Ветки cohort slab, additive alignment, geometric/rearmed lanes, counterfactual capacity, parity ownership, alternating deletion, LIFO и расширение траншеи обходят router. Короткие трубы и наблюдавшиеся длинные same-size runs сохраняют endpoint. Индексы, история, Fenwick, MC budget и reservations остаются baseline.

Каждый 16-й placement в обычной existing-gap ветке может выбрать до четырёх маршрутов: baseline; противоположный endpoint того же gap (L>4 вне long same-size run); tightest fit; следующий distinct fitting size. Последние два сохраняют сторону и owner baseline gap. Физические дубликаты удаляются. Это ограниченный локальный shortlist, не перебор всех возможных изменений baseline.

## Сначала измерение возможного выигрыша

Pilot: 8 train inputs, 159 состояний / 390 действий, 44 состояния с экономией ≥20 м; mean hindsight gain 27.421 м, median 0. Затем полный train: **64 входа, 1882 состояния, 4466 действий**, 444 состояний с gain≥20 м. Средний доступный выигрыш **16.142 м/state**, median 0; средний regret случайного выбора 19.850 м.

В каждом состоянии полностью клонировался исходный allocator до команды. Клоны одинаково проходили штатный baseline chooser/MC до hook; затем менялся один route. Весь оставшийся реальный suffix исполнял **тот же полный baseline**, включая свои истории и budgets. Для каждого исходного sampled state forced-baseline trench совпала с отдельным полным baseline replay. RolloutState короткого MC вместо реального allocator не использовался.

Это реальный эффект одной интервенции при известном suffix и заданном продолжении, **не достижимый online gain и не аддитивная величина**. Медиана ноль. Новые сильные правила или идеальный router за пределами четырёх routes этим не оценены. Будущее входит только в offline target.

## Обучение и его ограниченность

- Одна MLP **128→16 ReLU→1, 2 081 обучаемый параметр**. Features: наблюдавшиеся размеры/удаления, геометрия, возраст соседей и semantic route one-hot. Test/input/seed/PID identifiers и будущий suffix не входят в признаки.
- Train: 64 fresh inputs / 448k команд (4k и 16k); calibration: 16 fresh inputs / 128k команд (8k). Seeds и SHA не пересекаются между splits и с прежним learned-v1. Normalization только на train.
- Фиксированные Adam/loss/seed/margins из [PROTOCOL.md](PROTOCOL.md). Первый fit и один заранее разрешённый aggregate-data round. Реальный learned roll-in: 1 289 обращений / 118 переключений; 443 sampled states, из них 196 точных supervision duplicates исключены, 247 добавлены.
- Итог: **5103 действий / 2129 состояний / 64 input groups**. DAgger states остаются в той же train input group с отдельным state namespace, а не выдаются за независимые входы.
- Второй и последний fit: выбран epoch 13, margin 0.5. Calibration labeled saving **+0.195312 м/state**, hindsight ceiling 13.751 м/state, coverage 7.833%, pairwise accuracy 0.5155, MAE 18.730 м.

Эти labeled numbers выбирались на calibration и оптимистичны. Они не заменяют full rollout. Поле `deployable` из trainer JSON означает только положительный выбранный one-action criterion; окончательный допуск хранится в отдельном calibration gate.

## Full calibration gate и свежие проверочные потоки

До final/Open15 выполнен **один** paired full calibration rollout. 5 побед, 3 поражения, 8 равенств; среднее family-macro ΔKPI **-0.18332 п.п.** По заранее заданному nonnegative-mean rule gate отклонил кандидата и выбрал **baseline abstention**. Веса/порог не перенастраивались под результат; `bin/router_candidate` остался только исследовательским diagnostic.

После этого зафиксированы source, model, threshold, binaries и решение gate; только затем созданы 24 final inputs (8 отложенных относительно текущего train семейств × 12k/30k/200k; 1 936 000 команд). Их механизмы уже использовались в прежнем эксперименте. Это свежие входы/seed, а не совершенно неизвестные всему проекту family definitions и не официальный hidden set.

| Отложенное семейство | Активный router − baseline, п.п. KPI |
|---|---:|
| `abrupt_size_and_policy_regimes` | -0.0590 |
| `alternating_fifo_lifo_epochs` | -0.0005 |
| `cohort_lifetimes_survivor_stranding` | +0.1990 |
| `cyclic_demand_delayed_cohort_deletes` | +0.0095 |
| `heavy_tailed_age_mixture_lifetimes` | +0.3714 |
| `permuted_narrow_alphabet_longest_first` | -0.1789 |
| `sawtooth_bursts_persistent_anchors` | -0.3109 |
| `stationary_geometric_bursts_random_removal` | -0.1852 |

Среднее на final: **-0.01932 п.п.**; exploratory family-cluster bootstrap 95% interval **[-0.15407; +0.12972]**, пересекает ноль. 7 побед, 12 поражений, 5 равенств. На 200k mean ΔKPI -0.05681 п.п. Надёжного улучшения нет. Восемь вручную заданных семейств — ограниченный pilot; synthetic score sum не является Open15.

## Проверки, ресурсы, сохранность

- Exact old/instrumented baseline stdout совпал на **80 train/calibration inputs / 576 000 команд**. Abstaining `router_deploy` отдельно совпал с теми же baseline transcripts; основной вариант остаётся исходным baseline.
- Независимая клеточная модель: **32 000 команд, 1 179 forced branches**, включая **195 protected forced no-ops**. Проверены отсутствие наложений, clone independence, gap/owner/Fenwick indices и reserved volume.
- Полный Python/C++ O2 parity: 1 212 actions / 509 calibration states, max score difference 6.11e−7, **0 выбранных action mismatches**. Prefix independence и disabled equivalence проверены на восьми family; offline future reader исключён из production.
- Все **165 evaluation runs** (16×3 calibration +24×3 final +15×3 Open15) корректны и в лимитах. Максимум активного router CPU 1.217209 с, RSS 15.828 MiB; лимиты 5 с /256 MiB. Неактивный instrumented control совпал с baseline objective на всех оценочных входах.
- Исходный baseline, canonical `src/pipes.cpp`, frozen final и все 58 артефактов прежнего learned-v1 не изменены. Все 34 freeze hashes нового router перепроверены после оценки.

## Исправления и границы вывода

Read-only audit заметил, что default endpoint long same-size run тоже нужно защищать. Guard дополнен до full calibration/final. Полная повторная разметка всех 64+16 входов дала **побайтово те же CSV**, поэтому labels и первый fit остались валидными. Source/measurement hashes и guard-check сохранены. Эта поправка не основана на Open15.

DAgger loader теперь отказывается использовать model roll-in в бинарнике без USE_ROUTER; real changes и model/binary hashes записаны. Исходники guarded collection сохранены с проверенным исходным SHA в `reports/guarded_collector_source/`. Согласованный suffix и глубокие клоны проверены независимо.

Результат отвергает данную модель с данным shortlist/features/cadence как улучшение baseline. Он не доказывает бесполезность маршрутизаторов или обучения вообще. В частности, обучение до 16k и проверка на 200k дают сильный length shift, а hindsight labels одной интервенции не гарантируют качество повторяемой policy. Новые fit, подбор gates и повторные Open15 searches после freeze не запускались.

Freeze ID: `32c00cdffa91042b4d8da566efe1e1ed5b4e6bb7b6245051150ee79b65c7fd6c`. Model SHA: `9a0604dba3aee263b1dbbc888a7d3660aecc06effa2962acae8d9d5afa3b707f`.

Полные paired tables: `reports/evaluation_*/comparison.csv`; веса, команды и пути — в [README.md](README.md) и [manifest.json](manifest.json). Safety decision: [calibration_gate.json](reports/calibration_gate.json).
