# Независимый аудит corrected-MC + scoped-run overlay

Дата: 2026-10-16. Аудирован исходник `results/pipes/improvement/beam_diagnosis/source/cohort_owner_mc_corrected_scoped_run.cpp` без изменений.

## Идентичность и сборка

- Source SHA-256: `e95ed98e038aad6f46ccf62f4f167a45b2f1cc695772484d53001936c178df41` — совпадает с SHA из `beam_diagnosis/corrected_mc_overlay.json`.
- Свежая строгая сборка прошла на Apple clang 17.0.0 (`arm64-apple-darwin25.6.0`):
  `clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic results/pipes/improvement/beam_diagnosis/source/cohort_owner_mc_corrected_scoped_run.cpp -o results/pipes/improvement/cohort_owner_mc_scoped_audit/bin/cohort_owner_mc_corrected_scoped_run`
- Свежий бинарный SHA-256: `0d65f0e248359c70af0792ad19b2b93dc46db281158cdc2c322a1b290f0223fc`; он совпал с ранее сохранённым beam-бинарником.
- Official interactor SHA-256: `47994e837450bc4b0b683736194c2dce8023dd30f257c316c1e8e69245d15b9a`; harness SHA-256: `65aaa7043ffad3f0894dbdd5990b31bd713328d8546511b143ef57dca31dd20d`.

## Независимый прогон

Свеже-собранный бинарник повторно прошёл официальный harness на open15: `15/15`, weighted score `29.781127111082185 / 32.1`. Сравнение с независимым corrected-MC прогоном `29.77315080574852 / 32.1` показало ровно одно изменение: case 9, траншея `63,980 → 62,960 м`, KPI `0.492341356673961 → 0.500317662007624`, Δ score `+0.007976305333663447`. Остальные 14 исходов совпали. Максимальные ресурсы кандидата: CPU `1.540298 s`, RSS `6.9375 MiB`, wall `11.242609 s`; нарушений лимитов `5 s / 256 MiB` нет.

На holdout-v2 свежий прогон дал `12/12`, `5.13526432428047 / 12`. В паре с corrected MC score и все 12 траншей совпали; изменений нет. Максимум: CPU `0.322548 s`, RSS `4.140625 MiB`, wall `2.402388 s`; лимиты не превышены.

Сводки и покейсовые данные сохранены в `open/summary.json`, `open/cases.csv`, `holdout-v2/summary.json`, `holdout-v2/cases.csv`.

## Причинность и доступ к данным

Изменение относительно corrected MC добавляет только состояние `runLeftDisabledBySmoothTrend` и проверку трёх последних различных длин размещения. Override действует при наблюдаемом текущем запросе, когда последние 46 размещений имели ту же длину; он сбрасывается на смене длины и отключается, если шаг между тремя последними различными длинами равен. Та же проверка включена в модель rollout. Потоковый `main` читает по одной команде из `stdin`, отвечает и flush-ит; `argc/argv` не используется. Поиск и просмотр исходника не выявили файлового I/O, `score.txt`, номера теста/case ID, environment, часов, внешнего RNG или доступа к будущим командам. MC использует только текущую копию allocator state и сохранённые наблюдения; будущие события не доступны ему.

## Риск переобучения

Прирост open целиком сосредоточен в одном кейсе и получен правилом с точным порогом 46, подобранным в контексте видимого шаблона case 9. Это остаётся существенным риском подгонки к open-набору. Holdout-v2 не показывает ухудшения, но и не подтверждает перенос прироста: результат там идентичен corrected MC. Числа подтверждены; обобщение по ним не доказано.

`results/pipes/final/solution.cpp` и `src/pipes.cpp` на момент данного аудита не менялись.
