# Финальный независимый аудит `src/pipes.cpp`

## Исходник и соответствие frozen candidate

- `src/pipes.cpp` SHA-256: `7738c2d4089eff31257536515c80043b856da9e69b1a7b395e8ac8d013cbb85b`; совпал с хешем, записанным в integrated-final verification.
- Frozen source `adaptive_allocator.cpp`: SHA-256 `002f5bb77c131f829fc5ccfb0a310204113b6d8164d09d8dc7ed001e96833095`.
- Frozen `recent_unfit_s50` binary: SHA-256 `5c9efebc85b11d7b176ffe77a9ac002d58a78debfd045d535249a65ff2bd2e93`.
- Интегрированный optimized binary из integrated-final отчёта: SHA-256 `02afda1259200b6a692c1c7a9232289979aba7a288c3a4f4fb1eb96eb9893acf`; совпадает с сохранённой сборкой из текущего source SHA.
- В исходнике параметры `window=128`, `scale=50`; penalty формула учитывает `previous_pipe_length > slack`, tie-break — размер затем низкий адрес; хвост участвует как обычная свободная дыра. Семантика соответствует frozen `PIPES_STRATEGY=2`, `PIPES_HISTORY_WINDOW=128`, `PIPES_PENALTY_SCALE=50`.
- Поиск по исходнику не обнаружил `argv`, путей тестов, test ID, номера кейса, seed или ветвления по позиции команды. Аллокатор обрабатывает только текущую команду и историю последних 128 вставок.

## Сборка и онлайн-проверка

- UBSan + строгие предупреждения: сборка прошла с `-Werror`, предупреждений и runtime sanitizer ошибок не было.
- Independent oracle работает интерактивно: передаёт одну команду, ждёт ровно одну newline-terminated flushed строку; проверяет формат/границы координат, отсутствие пересечений, удаление активного PID по ожидаемому адресу, окончание по sentinel `0`, отсутствие stdout после sentinel и нормальный exit.
- Официальные открытые тесты: 15/15; `280156` команд и `280156` ответов.
- Frozen robustness suite: 10/10; `460000` команд и столько же ответов.
- Всего по двум oracle-прогонам: 36 streams, `1015350` команд и `1015350` ответов.
- Дополнительные независимые oracle streams: 10; вместе с opens и отдельным max stream всего `555350` интерактивных команд.
- Максимальный поток seed `0xF1A1`: 200000 команд, 200000 ответов, OK; траншея `253360 м`, занято `249686 м`, KPI `0.985498894853`.

## Сверка с сохранёнными official результатами

Independent oracle совпал по KPI, занятым метрам и H (длине траншеи) с integrated-final отчётом на всех 15 opens. Взвешенный score: `28.939458940265/32.1`. Также integrated-final записывает идентичность результатов integrated source и frozen s50 binary; наши измерения согласуются с этими per-case отчетами.
Все 10 robustness KPI/H совпали с уже сохранённым official-harness отчётом frozen `recent_unfit_s50`; каждый вход подтверждён manifest SHA-256.
Построчные сверки KPI/H/занятых метров: [`per_case_open_comparison.csv`](./per_case_open_comparison.csv) и [`per_case_robustness_comparison.csv`](./per_case_robustness_comparison.csv).

## Ресурсы и ограничения вывода

Максимумы CPU `0.900922 s` и RSS `4.8750 MiB` взяты из предыдущего official-harness integrated-final отчёта для бинарника, чьи source/binary hashes совпадают. Для UBSan oracle отдельное измерение CPU/RSS не собиралось.
Оценка ограничена перечисленными тестами и синтетическими потоками; она не доказывает корректность для любых возможных входов и не оценивает скрытое распределение. Максимальный поток F1A1 воспроизводится скриптом по seed, а не хранится как отдельный `.in`.
