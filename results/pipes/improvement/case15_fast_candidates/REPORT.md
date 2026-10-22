# Case 15: быстрый screen новых локальных правил

## Итог

Проверены пять политик на отдельной копии frozen final. Ни одна не улучшила case 15, поэтому полный Open15 и holdout-v2 для этих кандидатов не запускались.

| Вариант | Изменение | Траншея, м | Δ к frozen, м | KPI | Δ KPI | CPU, с | RSS, MiB |
|---|---|---:|---:|---:|---:|---:|---:|
| Frozen-copy baseline | Исходная политика | 438,920 | — | 0.954062244 | — | 2.209626 | 7.391 |
| Tail exact tie | При выборе хвоста предпочесть лучшую внутреннюю дыру только при равной стоимости | 438,920 | 0 | 0.954062244 | 0 | 2.204422 | 7.078 |
| Tail + 20 m allowance | То же, если внутренняя дыра дороже не более cost-эквивалента 20 м | 438,960 | +40 | 0.953975305 | −0.000086938 | 2.190862 | 7.438 |
| Fragmentation-gated age tie | Выбирать самый старый равнодлинный gap только при ≥20,000 активных труб и ≥256 gaps | 438,920 | 0 | 0.954062244 | 0 | 2.380170 | 8.438 |
| MC disabled | Отключить Monte Carlo выбор gap-кандидата | 438,920 | 0 | 0.954062244 | 0 | 2.199365 | 7.078 |
| Fragmentation-gated worst-fit | При ≥256 gaps и свободном объёме ≥8× самого большого gap выбирать самый большой fitting gap | 515,280 | +76,360 | 0.812678544 | −0.141383700 | 1.053788 | 8.063 |

Все шесть запусков прошли интерактор (`ok`) без превышения лимитов 5 s CPU / 256 MiB. Это локальные macOS measurements.

## Интерпретация

Удержание хвоста по точному tie не меняет траншею. Допуск в 20 м приводит к небольшой регрессии. Fragmentation gate для age tie-break не воспроизводит прежний узкий выигрыш без gates. Отключение rollout нейтрально. Условный worst-fit резко увеличивает траншею; поздняя фрагментация сама по себе не оправдывает выбор самого большого свободного интервала.

Эти проверки не дают кандидата для достижения цели; победителя case 15 для проверки соседних тестов нет. Вывод ограничен одним открытым кейсом.

## Воспроизведение

Команды выполнены из корня `/Users/555tery/techarena`. Сборка:

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic results/pipes/improvement/case15_fast_candidates/source/baseline.cpp -o results/pipes/improvement/case15_fast_candidates/bin/baseline
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic results/pipes/improvement/case15_fast_candidates/source/tail_tie.cpp -o results/pipes/improvement/case15_fast_candidates/bin/tail_tie
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic results/pipes/improvement/case15_fast_candidates/source/tail_20m.cpp -o results/pipes/improvement/case15_fast_candidates/bin/tail_20m
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic results/pipes/improvement/case15_fast_candidates/source/age_tie_fragmented_gate.cpp -o results/pipes/improvement/case15_fast_candidates/bin/age_tie_fragmented_gate
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic -DMC_ROLLOUT_DISABLED results/pipes/improvement/case15_fast_candidates/source/mc_disabled.cpp -o results/pipes/improvement/case15_fast_candidates/bin/mc_disabled
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic results/pipes/improvement/case15_fast_candidates/source/fragmented_worst_fit.cpp -o results/pipes/improvement/case15_fast_candidates/bin/fragmented_worst_fit
```

Для каждого имени ниже использована команда (имя заменено на вариант из таблицы):

```sh
python3 tools/pipes_harness.py --solver results/pipes/improvement/case15_fast_candidates/bin/NAME --name NAME --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/case15_fast_candidates/tests --out results/pipes/improvement/case15_fast_candidates/runs/NAME --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
```

`NAME`: `baseline`, `tail_tie`, `tail_20m`, `age_tie_fragmented_gate`, `mc_disabled`, `fragmented_worst_fit`. В `tests/` лежит только копия официального `15.in`.

## SHA-256

- Frozen final и контрольная копия: `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`.
- Canonical `src/pipes.cpp` (не менялся): `526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8`.
- Вход case 15: `0b37a067bbe01429414ba20096e0a30fc9c424f7f364d101f71c32b85fe3a353`.
- Interactor: `47994e837450bc4b0b683736194c2dce8023dd30f257c316c1e8e69245d15b9a`.

| Вариант | Source SHA-256 | Binary SHA-256 |
|---|---|---|
| baseline | `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991` | `ee9ae15f8f4879eaca8da9a0c5fdb1caeb05311893279a4eaf0734c167427290` |
| tail_tie | `1b830871b4e7ba5bc4bca88a39551981d5ccb559d5ac2d0e30a296f473f75b19` | `7dbb213233771168b241963c79335998ecf76338299082ec4d02ce7c478c61c9` |
| tail_20m | `546c14034c036d7913a7e0087469cde0ede318b52a2a84794034a9dfe0a1ba26` | `e023812f897ec978b7b244571e11edec187c3e619e0b9462b743e8a3fd7c49bb` |
| age_tie_fragmented_gate | `993afcd1428beea6e4ae0adb4d9433566a70234701627423d1ff258b27392697` | `d9e4a18c42e14bca49b9e063aa6721651fea455dfd1219a1f18b495363e504f0` |
| mc_disabled | `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991` | `6a4f900e5f0cb4bb2ccd0fdb7fd81a286d7dee9d450c954a6e5b00881d53a0e1` |
| fragmented_worst_fit | `ffb9f229145acd158c65a0d0610737bf4e6afd0852e152151d90fc9a18619b29` | `45bc9dc875a6c91791ff30f3526c35298de519fdedb10fba6a2c58d15a5856b0` |
