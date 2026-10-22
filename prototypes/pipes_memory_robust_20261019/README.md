# Pipes: memory-backed search with delayed causal validation

Эксперимент 19–20 октября 2026. Результаты: [report.html](report.html), [report.json](report.json), [metrics.csv](metrics.csv).

Локальный кандидат: `causal-final/solution.cpp`. Canonical source и платформа не менялись.

На новой confirmation после freeze: 3 wins / 20 ties / 1 loss, средняя ΔKPI+0.000182056. 95% описательный bootstrap включает ноль. Это ограниченный сигнал, не доказанный рост на неизвестных закрытых тестах. Open15 сохраняет 30.75747404826914.

Точный финальный бинарник прошёл 44 официальных локальных проверки: максимум 4.196851s CPU и 212.765625MiB RSS. Отдельно 81 знакомый regression input проверен полным replay и независимым occupancy-validator;2/78/1, худшая ΔKPI−0.006292595.

## Сборка и воспроизведение

Standalone: `clang++ -std=c++20 -O2 causal-final/solution.cpp -o solver`.

Из корня repository:

```
python3 prototypes/pipes_memory_robust_20261019/evaluate.py confirmation --candidate causal-final --mode official --names baseline,candidate,bestfit --freeze-manifest freeze-causal.json
python3 prototypes/pipes_memory_robust_20261019/evaluate.py open15 --candidate causal-final --mode official --names candidate
python3 prototypes/pipes_memory_robust_20261019/report.py
```

Evaluator проверяет хеши при повторном использовании записей. Для нового замера можно сделать отдельную копию эксперимента внутри `prototypes/` без каталога `measurements/` и запустить evaluator из неё. Существующие записи и архивы не удалять. `build.py` воспроизводит source в `candidate/`, frozen `causal-final/` остаётся неизменным.

## История и ограничения

Первый `final/` отклонён: средняя ΔKPI−0.000720999 на своих24 final и CPU5.853554s на F05. `resource-fixed/` исправляет только CPU reserve. `causal-final/` добавляет отложенную проверку по уже пришедшим128 командам и оценён на отдельном `evaluation/confirmation/`.

Размеры памяти — полезные структуры поиска:80MiB arena,128MiB memo, до8 снимков физического allocator. Workspace освобождается при масштабе/исчерпании бюджета. Короткий поток может завершиться раньше исчерпания CPU: его длина не раскрывается заранее.

Исторические сценарии и отложенные128-командные проверки могут ошибаться на дальнем будущем; их окна перекрываются. Ранние ловушки на общем Open15-префиксе остаются, поскольку траншея не уменьшается.
