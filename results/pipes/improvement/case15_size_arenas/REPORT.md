# Coarse size-class arenas

**Итог: no-go для текущего champion.** Новая структура заметно ухудшила case 15, хотя дала небольшой выигрыш на двух из шести свежих синтетических потоков. Полный Open15 не запускался: заданный порог для него — улучшение case 15 минимум на 1,000 м, а здесь получен регресс.

## Идея и отличие от прежней проверки

Свободные интервалы получают постоянную метку класса по длине трубы, при удалении или создании остатка: `1–10`, `11–20`, `21–40`. При разделении интервал сохраняет владельца; слияние разных классов переводит его в общий пул. При наблюдаемом спросе минимум на два класса allocator сначала ищет подходящий интервал своего класса, затем общий, а иначе возвращается к выбору champion. Активация основана на последних 2,048 размещённых трубах. Номер теста и будущие команды не используются.

Это архитектурно отличается от `adaptive_live_mean`: там после длинной серии одной точной длины выбирался sticky-остаток для этой длины; отдельного учёта владельцев всех промежутков, раздельных пулов и правил переноса метки при split/merge не было. Действующий parity-cohort режим champion имеет приоритет и выключает arena-предпочтение.

## Результаты

Сравнение с champion `43bfbdad…`:

| Поток | Champion: траншея, м | Candidate: траншея, м | Δ траншеи | Δ score |
|---|---:|---:|---:|---:|
| Open case 15 | 438,920 | 444,600 | +5,680 | −0.121886494 |
| fresh_01: короткие → длинные, LIFO | 1,800 | 1,800 | 0 | 0 |
| fresh_02: длинные → короткие, FIFO | 13,120 | 13,120 | 0 | 0 |
| fresh_03: средние → бимодальные, случайные удаления | 9,660 | 9,560 | −100 | +0.008158130 |
| fresh_04: чередование коротких/длинных фаз, FIFO/LIFO | 13,560 | 13,560 | 0 | 0 |
| fresh_05: бимодальный спрос со средней фазой, FIFO/LIFO/random | 8,420 | 8,020 | −400 | +0.035836774 |
| fresh_06: постепенный сдвиг длин, удаление около медианы | 8,720 | 8,760 | +40 | −0.004061413 |

На шести synthetic score сумма выросла `4.017348633521 → 4.057282123494`: два выигрыша, один проигрыш и три ничьи. Это ограниченный диагностический набор, не доказательство переноса. На case 15 candidate потребовал на 5,680 м больше траншеи. Его CPU/RSS: `1.252 с / 8.672 MiB`; champion: `1.109 с / 7.953 MiB`. Все прогоны завершились `ok`, лимиты 5 CPU-с / 256 MiB не нарушены.

## Воспроизведение и артефакты

Команды из корня репозитория:

```sh
python3 results/pipes/improvement/case15_size_arenas/generate_candidate.py
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror results/pipes/improvement/case15_size_arenas/source/coarse_size_class_arenas.cpp -o results/pipes/improvement/case15_size_arenas/bin/coarse_size_class_arenas
python3 results/pipes/improvement/case15_size_arenas/make_synthetic.py
python3 tools/pipes_harness.py --solver results/pipes/improvement/case9_causal_profiles/bin/champion_cohort_slabs --name champion_case15 --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/case15_size_arenas/tests --out results/pipes/improvement/case15_size_arenas/runs/champion_case15 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/case15_size_arenas/bin/coarse_size_class_arenas --name coarse_size_class_arenas_case15 --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/case15_size_arenas/tests --out results/pipes/improvement/case15_size_arenas/runs/candidate_case15 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/case9_causal_profiles/bin/champion_cohort_slabs --name champion_six_fresh_synthetics --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/case15_size_arenas/synthetic --out results/pipes/improvement/case15_size_arenas/runs/champion_synthetic --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/case15_size_arenas/bin/coarse_size_class_arenas --name coarse_size_class_arenas_six_fresh_synthetics --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/case15_size_arenas/synthetic --out results/pipes/improvement/case15_size_arenas/runs/candidate_synthetic --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
```

Ключевые SHA-256:

| Артефакт | SHA-256 |
|---|---|
| Candidate source | `568b24b5e7f0915cd48993c247e7c4d60dd2be3d91e07207dc332ef8ec6196cf` |
| Candidate binary | `74a3f3a731bac87774651329eb26184c26a082336efc0b1df3399a6a01ed1659` |
| Candidate generator | `e77c56fc13eb830630483eb25e92cbf7d5686f3079e1252d6b41cd247c40bd35` |
| Synthetic generator | `4e1f0d3ed5987a025f6516aa8aeeef8c641047a52c0c8ecd7255e518e6feee40` |
| Champion source | `43bfbdadbae18ac180d1e59b6631342cfe1bef99190a449838f0470d6f220200` |
| Champion binary | `e4b79d8eb55a1fdc03a8c62505142ee615304401e821895bf6ab7f3712e54049` |
| Open case 15 input | `0b37a067bbe01429414ba20096e0a30fc9c424f7f364d101f71c32b85fe3a353` |
| Official interactor | `47994e837450bc4b0b683736194c2dce8023dd30f257c316c1e8e69245d15b9a` |
| Frozen final (unchanged) | `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991` |
| Canonical source (unchanged) | `526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8` |

Входы fresh-сценариев, их генератор, сырые harness-отчёты и per-run outputs сохранены рядом: `synthetic/`, `make_synthetic.py`, `runs/`. Open15 и holdout не запускались; сайт и Docker не использовались.
