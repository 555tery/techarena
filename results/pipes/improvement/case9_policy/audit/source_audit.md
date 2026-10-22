# Независимый аудит исходника

Аудит выполнен отдельным агентом по замороженному исходнику `alternating_delete_parity_edges.cpp`, SHA-256 `57338ca2dd0d81e2c553edefb5c2c40fdb1b3aec88873709a21da6574c85560f`. Файл не изменялся.

## Сборка и replay

Строгая сборка прошла на Apple Clang 17.0.0:

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic \
  results/pipes/improvement/case9_policy/alternating_delete_parity_edges.cpp \
  -o results/pipes/improvement/case9_policy/audit/alternating_delete_parity_edges
```

SHA-256 бинарника аудитора: `ed3bf40f0199f755ae053dd8fb411633da072d379cb29e99c6d614ba607ee3fd`.

Official replay case 9 прошёл: score `0.504484304932735`, trench `62,440 м`, CPU `0.068971 s`, RSS `3.015625 MiB`. Это отдельный replay одного open case; все 15 open и 12 holdout кейсов проверены в основном harness прогоне и повторе, описанных в `../REPORT.md`.

## Причинность и согласованность

Основной цикл читает команды последовательно из stdin и отвечает после каждой команды. Аудитор не обнаружил чтения файлов, `score.txt`, `argv`, environment, test ID, будущих команд, часов или внешнего RNG. Monte Carlo rollout использует только `observedHistory`.

Детектор требует восемь последовательных удалений труб одной длины с PID, увеличивающимся каждый раз на 2. Любое несовпадение сбрасывает счётчик и режим. После активации allocator направляет размещение на high edge, когда parity нового PID не равна предсказанной удаляемой parity. Детектор, состояние и формула выбора края совпадают в live allocator и `RolloutState`; состояние копируется в rollout. PID live (`pipes.size()`) соответствует `nextPid` симуляции.

## Ограничение fidelity rollout

Monte Carlo хранит удаление как квантованный `rank-permille`, затем применяет этот ранг к counterfactual active list. В rollout это может восстановить другой PID, чем исходно удалённый PID в live истории, и повлиять на последующее срабатывание детектора. Это ограничение симуляции и не даёт доступа к будущим командам. Поэтому результаты rollout при включении новой политики требуют осторожной трактовки.

## Прочее

Оговорка по malformed input: выражение `-command` переполнится для `INT64_MIN`; официальные входы используют допустимые отрицательные PID, поэтому этот крайний случай вне конкурсного протокола. Аудитор подтвердил, что финальный и canonical исходники не менялись: SHA `e95ed98e…c178df41` и `526ba58e…a1dfec8` соответственно.
