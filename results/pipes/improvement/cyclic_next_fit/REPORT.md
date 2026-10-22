# Cyclic next-fit: локальный screen и no-go

## Решение

**No-go.** Циклический next-fit проиграл замороженному baseline на каждом из трёх локальных Open cases. Сумма взвешенных баллов по этим случаям упала с `10.859085056537` до `10.063415346682` (`−0.795669709855`). Дальше этот кандидат не квалифицировался: полный Open15 и holdout не запускались.

Тестировались только локальные cases 5, 9 и 15. На платформу не заходили; решений туда не отправляли. Финальный и canonical исходники не менялись.

## Кандидат

Политика реализована без переключателей по тесту, истории размеров, удалений или результатов других эвристик:

1. Искать первый по адресу свободный интервал длины `L`, начиная с `lower_bound(cursor)`.
2. Если справа от курсора подходящего интервала нет, продолжить поиск от начала траншеи до курсора.
3. Укладывать трубу у левого края найденного интервала.
4. После укладки установить `cursor = start + L`; удаления курсор не меняют.
5. Если свободного интервала нет, продолжить обычное расширение от свободного хвоста секциями по 20 м.

Сборка строгая: `clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic`; компилятор — Apple Clang 17.0.0. Кандидат и baseline собраны локально из снимков исходников внутри этой папки. Baseline совпадает с frozen-final source побайтно.

## Парные результаты

Все три прогона завершились `ok`; одинаковые SHA входов подтверждают, что сравнивались одни и те же cases. В колонке «вклад» учтён официальный вес случая (1, 1 и 10).

| Case | Baseline: trench, KPI, вклад | Next-fit: trench, KPI, вклад | Δ trench | Δ вклада | CPU baseline → next-fit | RSS baseline → next-fit |
|---:|---:|---:|---:|---:|---:|---:|
| 5 | 62 760 м; 0.810070108349; 0.810070108349 | 101 720 м; 0.499803381832; 0.499803381832 | +38 960 м | −0.310266726517 | 0.104352 → 0.126456 с | 2.750000 → 2.687500 MiB |
| 9 | 61 960 м; 0.508392511298; 0.508392511298 | 63 000 м; 0.500000000000; 0.500000000000 | +1 040 м | −0.008392511298 | 0.170189 → 0.127236 с | 2.734375 → 3.078125 MiB |
| 15 | 438 920 м; 0.954062243689; 9.540622436891 | 462 020 м; 0.906361196485; 9.063611964850 | +23 100 м | −0.477010472041 | 2.589786 → 4.246247 с | 5.562500 → 6.500000 MiB |
| **Сумма** | **10.859085056537** | **10.063415346682** | — | **−0.795669709855** | — | — |

Candidate case 15 остался ниже лимитов `5 s CPU / 256 MiB RSS`, но потребовал `4.246247 s` CPU. Уже имеющаяся сильная просадка результата делает дальнейшую проверку бессмысленной для этой политики.

## Provenance и воспроизведение

- Frozen-final source и локальная копия baseline: `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`.
- Cyclic next-fit source (`candidate.cpp`): `5696dcdc1b691730239fb8e6d7eb2cf04cec66905e96532a5346ed77ca97ddfc`.
- Baseline binary: `ee9ae15f8f4879eaca8da9a0c5fdb1caeb05311893279a4eaf0734c167427290`.
- Candidate binary: `03642a2c6e6d4343fa1c1b120451d923d5787c35b31b0d0eff70ad12e78819db`.
- Official interactor binary, использованный read-only: `47994e837450bc4b0b683736194c2dce8023dd30f257c316c1e8e69245d15b9a`.
- SHA входов: case 5 `bae469c3ed43bba21ab4a9cd9ecef4c53bb2f99fbd9f6cc246f9c3e082f1b32b`; case 9 `cfb711efa3a9ccccc17e7170fc7c2ea19c12ed45b789da3a4b2c80750d7ca128`; case 15 `0b37a067bbe01429414ba20096e0a30fc9c424f7f364d101f71c32b85fe3a353`.
- Машинные записи: `baseline-run/{summary.json,cases.csv}` и `candidate-run/{summary.json,cases.csv}`.

Команды для воспроизведения (из корня проекта):

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic results/pipes/improvement/cyclic_next_fit/baseline.cpp -o results/pipes/improvement/cyclic_next_fit/baseline
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic results/pipes/improvement/cyclic_next_fit/candidate.cpp -o results/pipes/improvement/cyclic_next_fit/candidate
python3 tools/pipes_harness.py --solver results/pipes/improvement/cyclic_next_fit/baseline --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/cyclic_next_fit/cases --out results/pipes/improvement/cyclic_next_fit/baseline-run --name frozen-baseline-screen --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/cyclic_next_fit/candidate --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/cyclic_next_fit/cases --out results/pipes/improvement/cyclic_next_fit/candidate-run --name cyclic-next-fit --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
```
