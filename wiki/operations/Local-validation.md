# Локальная сборка и проверка

## Текущие Make targets

Из корня:

```sh
make all
make test
make test-holdout
```

Targets определены в [`Makefile`](../../Makefile). Важно: `make test` собирает и запускает canonical [`src/pipes.cpp`](../../src/pipes.cpp), а не frozen final из `results/pipes/final/solution.cpp`.

## Замороженный артефакт

Команды точной сборки и воспроизведения записаны в [`results/pipes/final/README.md`](../../results/pipes/final/README.md). Там же указаны пути к manifest, CSV и ограничениям измерений. На этой странице команды только задокументированы; новые тестовые прогоны не выполнялись.

## Как трактовать результаты

- Предпочитай `manifest.json`, `summary.json` и покейсовые CSV отчёту по агрегату.
- `score.txt` создаётся interactor-ом внутри рабочего каталога теста и может быть округлённым или устаревшим.
- Не принимай root `score.txt` за текущую сумму; в нём историческое `0.5`.
- Holdout-v2 и синтетические сценарии — локальные проверки переноса, не официальный скрытый набор.
