# Case 15: lost-feasible-demand cost — no-go

## Короткий вывод

Текущий champion набирает Open15 `29.932085817214`; case 15 — `438 920 м`, lower bound `418 780 м`. Проверенная новая оценка стоимости выброшена: case 15 вырос до `441 740 м` (**+2 820 м**, case weighted score `−0.060906`). На четырёх свежих synthetic аналогах результат разнонаправленный: один выигрыш на 940 м и три регрессии на 100–1 000 м; сумма KPI изменилась на `−0.003192`. Полный Open15 не запускался.

## Трассировка расширений и причина no-go

В case 15 было `17 645` расширений; в `13 677` из них суммарный свободный объём до размещения был не меньше входящей трубы. Однако перед **каждым** расширением физически подходящего интервала не было. Значит, на самом событии расширения проблема не в генерации/ранжировании кандидатов: допустимое действие отсутствовало. Экономия возможна только из-за более ранней геометрии размещений. В позднем фрагментированном состоянии MC уже отключён лимитами состояния (`>64` gaps, `>4 096` активных труб), но его повторное включение само по себе не создаёт физически подходящего интервала.

Дополнительный однопоточный offline-аудит измерил долю recent-history спроса, для которой в текущих gaps не было ни одного физического места (`missing_share`). В состояниях, где последние 256 placement-размеров были как минимум наполовину длиной `8+`, верхний дециль `missing_share` сопровождался расширением в следующих 8 placement-событиях в `90.4%` состояний; нижний дециль — в `24.5%`. На горизонте 32 это `99.0%` против `65.6%`. Это сигнал **дефицита пригодных gap-ов** в одной трассе, а не новый механизм размещения: его действие сводится к резервированию крупных gap-ов, которое уже проверялось и не улучшило case 15. Он не оправдывает новую policy без независимого подтверждения. По exact candidate/lineage-аудиту у будущих расширений нет выжившего подходящего gap-а, а у preceding decisions отбор зависит от будущей судьбы gap-ов. Поэтому причинное неочевидное правило из этих данных не следует. Вторая policy-гипотеза не создавалась.

## Проверенная policy-гипотеза

Кандидат заменяет recent-unfit penalty на локальную `lost-feasible-demand`: для gap длиной `G`, трубы `q`, остатка `s=G-q` штрафуются только наблюдавшиеся длины `L`, где `s < L <= min(G,40)`. То есть учитывается спрос, который помещался именно в этот gap до placement и перестанет помещаться после. Линейная цена остатка сохранена; каждый такой recent observation получает существующий множитель `60`. Все признаки доступны из текущего состояния и предшествующей истории.

На одном официальном кейсе правило проиграло на `2 820 м`. Это указывает, что локальное сохранение возможных размеров без моделирования последующего удаления текущей трубы охраняет ненужную геометрию; точная причина каждого проигранного расширения отдельно не доказывалась. Настройка веса и повторный перебор не выполнялись.

## Свежие synthetic-трассы

Четыре потока по 40 000 операций с фиксированным seed `913733`: короткие размеры `1–7` со сменой на широкие `8–40`; смена на bimodal `8/40` с удалением старейших; стационарные `1–40` с удалением более новых; и обратная смена `8–40` на `1–7`. Сравнение проводилось попарно на официальном локальном interactor; все восемь candidate/baseline прогонов `ok`.

| Сценарий | Champion, м | Candidate, м | Δ м | Δ KPI |
|---|---:|---:|---:|---:|
| short → wide, random deletes | 113 080 | 114 080 | +1 000 | −0.008569 |
| short → bimodal, older deletes | 119 980 | 119 040 | −940 | +0.007743 |
| stationary wide, newer deletes | 97 820 | 97 920 | +100 | −0.001009 |
| wide → short, random deletes | 58 720 | 58 920 | +200 | −0.001357 |

Эта небольшая исследовательская выборка показывает нестабильность правила, но не оценивает все распределения.

## Команды воспроизведения

Из корня проекта:

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic results/pipes/improvement/case15_opportunity_loss/source/opportunity_loss.cpp -o results/pipes/improvement/case15_opportunity_loss/bin/opportunity_loss
python3 tools/pipes_harness.py --solver results/pipes/improvement/case15_opportunity_loss/bin/opportunity_loss --name opportunity_loss_case15 --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/case15_opportunity_loss/tests --out results/pipes/improvement/case15_opportunity_loss/runs/case15 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 results/pipes/improvement/case15_opportunity_loss/generate_synthetic.py
python3 tools/pipes_harness.py --solver results/pipes/improvement/case9_causal_profiles/bin/champion_cohort_slabs --name champion_fresh_synthetic --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/case15_opportunity_loss/synthetic --out results/pipes/improvement/case15_opportunity_loss/runs/champion_synthetic --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/case15_opportunity_loss/bin/opportunity_loss --name opportunity_loss_fresh_synthetic --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/case15_opportunity_loss/synthetic --out results/pipes/improvement/case15_opportunity_loss/runs/candidate_synthetic --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
```

Экспансия telemetry строится из exact saved champion transcript. Команды:

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic results/pipes/improvement/case15_opportunity_loss/trace_features.cpp -o results/pipes/improvement/case15_opportunity_loss/bin/trace_features
results/pipes/improvement/case15_opportunity_loss/bin/trace_features data/pipes/open/15.in results/pipes/improvement/case9_causal_profiles/runs/champion-cohort-slabs-open15/runs/15/judge_output.txt results/pipes/improvement/case15_opportunity_loss/runs/baseline_features.csv
python3 results/pipes/improvement/case15_opportunity_loss/analyze_liquidity.py
```

Покейсовые результаты: [`per_case_comparison.csv`](per_case_comparison.csv). Подробные harness CSV/summary находятся в [`runs/`](runs/).

## SHA-256

- Champion source: `43bfbdadbae18ac180d1e59b6631342cfe1bef99190a449838f0470d6f220200`.
- Candidate source: `e327ada2e7463206235dcd9b0934b298629618e02dc86d634be6ac8be38e0059`.
- Candidate binary: `fe449fcc30456362fb8cfa37de07a861d1004122a42433e89c38f536765dcc78`.
- Trace tool source/binary: `79de0ecd8eab783f64ad8ec03ec26e0ae03daab6fa30648f74d1e1d8b3cbe186` / `c73dafd8e2d13acd71ae9ec11f92e829528c4f29ca8b00943d86772bc259d595`.
- Fresh synthetic generator: `5846ba10867faaef0b033886f1f458b63d6e0466cec7b0bcce07b6478f501a63`; test input hashes are recorded in adjacent `manifest.json`.
- Baseline champion binary: `e4b79d8eb55a1fdc03a8c62505142ee615304401e821895bf6ab7f3712e54049`.
- Case 15 input: `0b37a067bbe01429414ba20096e0a30fc9c424f7f364d101f71c32b85fe3a353`.
- Interactor: `47994e837450bc4b0b683736194c2dce8023dd30f257c316c1e8e69245d15b9a`.
- Baseline judge output: `0382b67c434136d5a015c37ccd4749d35624418ec61eece53af28fe74221bd0e`.
- Candidate case-15 output: `8bd15f0911ec47a54f89febcb5738643b4137fd8587ee42adb625bfee1aaa895`.
- Frozen final source, checked unchanged: `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`.
- Canonical source, checked unchanged: `526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8`.
