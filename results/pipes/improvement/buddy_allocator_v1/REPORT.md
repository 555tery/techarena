# Buddy allocator v1 — no-go

## Решение

Адресный buddy allocator — отдельная геометрическая схема: свободные области представлены выровненными блоками степеней двойки, при выдаче большой блок делится, при удалении соседние свободные buddies сливаются. Размерные пулы не закрепляются за классами и будущее не используется.

Эксперимент отклонён. На case 15 траншея выросла с **438 920 м** у текущего champion до **597 700 м** (**+158 780 м**). На шести новых синтетических потоках кандидат проиграл во всех шести. Поэтому Open15 и holdout не запускались.

## Результаты

| Поток | Champion, м | Buddy, м | Δ траншеи, м | Δ KPI |
|---|---:|---:|---:|---:|
| Open case 15 | 438 920 | 597 700 | +158 780 | −0.253448 |
| stationary uniform + random delete | 56 100 | 78 340 | +22 240 | −0.255815 |
| short → wide + random delete | 61 640 | 88 720 | +27 080 | −0.289840 |
| wide → short + FIFO delete | 81 780 | 121 540 | +39 760 | −0.044910 |
| bimodal + LIFO delete | 51 820 | 95 440 | +43 620 | −0.455983 |
| periodic sizes + same-size/old-first delete | 24 060 | 35 280 | +11 220 | −0.304994 |
| three-phase sizes + old-biased delete | 100 300 | 140 560 | +40 260 | −0.250433 |

На шести синтетических потоках сумма взвешенного KPI уменьшилась с **4.81900671927** до **3.21703206549**. Все 14 прогонов прошли официальный локальный interactor. Лимиты также соблюдены: case 15 — 1.056 с CPU и 4.08 MiB RSS у buddy; на синтетиках максимум buddy — 0.247 с CPU и 1.89 MiB RSS.

## Интерпретация

Схема отличалась от ранее проверенных sticky-сегментов, cohort slabs и suffix arenas: она не размечала области по размеру/когорте, а перестраивала геометрию через dyadic split/merge. Однако стандартное выделение `2^ceil(log2(L))` резервирует под каждую трубу округлённый блок. Неиспользованный остаток нельзя выдать соседней трубе, пока первая активна; выравнивание buddy-блоков дополнительно может не позволить использовать суммарно достаточную свободную длину. Освобождение и coalescing после удаления не компенсировали эти потери при смешанных длинах и churn.

Это достаточный отрицательный screen для данной версии. Числа не доказывают, что любая схема с иерархическими диапазонами хуже; они отвергают именно стандартный power-of-two buddy allocator с блоком, полностью занятым до удаления трубы. Новые варианты округления не подбирались.

## Артефакты и хеши

- [Исходник кандидата](source/buddy_allocator.cpp), SHA-256 `f2876d9457e448cb9c11f77fee16a050ea544675d57bf7eb8da2d59bfa2f41c0`.
- Бинарник кандидата SHA-256 `803f31d670eef1ab89166f5318072cb31c2bfb12791b64d822b8036eb149aebe`.
- Champion source/binary SHA-256: `43bfbdadbae18ac180d1e59b6631342cfe1bef99190a449838f0470d6f220200` / `e4b79d8eb55a1fdc03a8c62505142ee615304401e821895bf6ab7f3712e54049`.
- [Генератор синтетик](generate_synthetic.py), SHA-256 `e2b8fb1f4d616b03dc774664a63998c52016cae7f9fb074ff0f8e46c6020e02b`; [манифест потоков](synthetic/manifest.json), SHA-256 `9b3cb947649c7bfebc7622560dbf694b9fe0f2773b48d45f9f9039010658d3ce`.
- Case 15 input SHA-256 `0b37a067bbe01429414ba20096e0a30fc9c424f7f364d101f71c32b85fe3a353`; buddy/champion judge-output SHA-256 `5b0da61fb8db6b049cccffcc0caea43f63aa9a8c21bb36b5b3ee817cd0b7729a` / `0382b67c434136d5a015c37ccd4749d35624418ec61eece53af28fe74221bd0e`.
- Покейсовые результаты и полные протоколы: [`runs/`](runs/); SHA-256 сводок/CSV перечислены в [`SHA256SUMS`](SHA256SUMS).

## Команды воспроизведения

Из корня проекта; локальные тесты, без сайта и Docker:

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic results/pipes/improvement/buddy_allocator_v1/source/buddy_allocator.cpp -o results/pipes/improvement/buddy_allocator_v1/bin/buddy_allocator
python3 results/pipes/improvement/buddy_allocator_v1/generate_synthetic.py
python3 tools/pipes_harness.py --solver results/pipes/improvement/buddy_allocator_v1/bin/buddy_allocator --name buddy_v1_case15 --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/buddy_allocator_v1/tests/case15 --out results/pipes/improvement/buddy_allocator_v1/runs/case15/buddy_v1 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 180
python3 tools/pipes_harness.py --solver results/pipes/improvement/case9_causal_profiles/bin/champion_cohort_slabs --name champion_case15_control --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/buddy_allocator_v1/tests/case15 --out results/pipes/improvement/buddy_allocator_v1/runs/case15/champion --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 180
python3 tools/pipes_harness.py --solver results/pipes/improvement/buddy_allocator_v1/bin/buddy_allocator --name buddy_v1_synthetic --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/buddy_allocator_v1/synthetic --out results/pipes/improvement/buddy_allocator_v1/runs/synthetic/buddy_v1 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 180
python3 tools/pipes_harness.py --solver results/pipes/improvement/case9_causal_profiles/bin/champion_cohort_slabs --name champion_on_buddy_synthetic --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/buddy_allocator_v1/synthetic --out results/pipes/improvement/buddy_allocator_v1/runs/synthetic/champion --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 180
```

Canonical/frozen source и платформа не затрагивались.
