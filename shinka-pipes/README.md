# ShinkaEvolve для Pipes: локально через Codex

Настройка подготовлена 17 октября 2026 г. Эксперименты, оценка baseline и запросы
к модели при настройке не выполнялись. Docker не используется.

После настройки выполнен отдельный baseline-only прогон на search: **32/32**,
fitness **0.914983819101**, максимум solver CPU **1.189802 s**, RSS **6.96875 MiB**.
Эволюция и запросы к модели не запускались; validation и Open15 не использовались.
Доказательства: [отчёт baseline](baseline-runs/20261017T231804+0700/REPORT.md).

По следующему прямому запросу пользователя запущен search-only поиск с лимитом
20 поколений (включая initial gen 0): [манифест](runs/20261017T232542+0700-833000/run-manifest.json).
Текущий запуск: `active-run.json`. Его preflight проверяет только search; validation
и Open15 не читаются и не оцениваются. Это статус запуска, не итоговый результат.

## Что установлено

- Python 3.12, отдельная `.venv`; зависимости закреплены в `uv.lock`.
- ShinkaEvolve commit `8adc053a2ce4511ad2ac310e004c530a73fb974a`.
- Headless commit `93cd9b06b85f848af1308c41e018991b33907c5e`, локально в `runtime/`.
  Используется Git-версия: опубликованный npm `0.6.1` при настройке ещё не имел
  режима billing из текущей документации. Зависимость закреплена в `package-lock.json`.
- Используется существующий Codex CLI и его вход через ChatGPT; секреты не копируются.
- `upstream/` и `headless-upstream/` — справочные checkout сторонних исходников;
  установленный runtime от них не зависит.

## Авторизация и модель

`headless.sh` допускает только Codex с `read-only` и принудительно добавляет
`--billing subscription`. Ключи API и пользовательский `OPENAI_BASE_URL` удаляются
из окружения дочернего процесса; загрузка `.env` отключена. Переход на платный API
запрещён. API embeddings, meta-рекомендации и W&B отключены.

По запросу пользователя в `task-synthetic/shinka.yaml` явно закреплена модель текущего чата:
`headless/codex@gpt-6.1-sol?effort=xhigh`. Название модели и reasoning проверены
по метаданным текущего turn. Defaults CLI и переменная `CODEX_MODEL` не влияют
на этот выбор. `--check` показывает модель и reasoning без запроса к ней.

## Безопасная проверка

Из любой папки:

```sh
/Users/555tery/techarena/shinka-pipes/run.sh --check
```

Без аргументов и с `--dry-run` выполняется та же проверка. Она проверяет импорты,
конфигурацию, хеши snapshot, ChatGPT login status, маршрут Shinka → Headless и
предпросмотр команды Codex. Она не создаёт runner, не запускает evaluator, не
обращается к модели и не проверяет Docker. Последняя сводка — `setup-check.json`.
Полная проверка без запуска включает контрольные суммы отложенных наборов;
реальный `--run` использует search-only preflight и пропускает их.

Проверки ограничения billing и явного запуска, также без экспериментов:

```sh
cd /Users/555tery/techarena/shinka-pipes
.venv/bin/python -m unittest discover -s tests -v
```

## Подготовленная задача

`task-synthetic/initial.cpp` — копия local leader `c1994511…bb736c`; добавлены только
комментарии EVOLVE-BLOCK. Источник и хеш записаны в `task-synthetic/snapshot.json`.
Includes и внешний цикл `main` находятся вне изменяемой области.

Search содержит **32 синтетических потока из 16 семейств**. Отдельный validation —
**24 потока из 20 семейств**, в том числе четыре механизма вне search. Open15
исключён из активной задачи и evaluator. Прежний `task/` сохранён без изменений.
Validation запускается отдельно для заранее выбранного кандидата; feedback модели
содержит только search. Подробности — [CORPUS_PROTOCOL.md](CORPUS_PROTOCOL.md).

Конфигурация `task-synthetic/shinka.yaml`: два islands и по одному worker генерации,
оценки и базы. Fitness — среднее `B/T` с равным весом семейств, где `B` — объёмная
нижняя граница длины траншеи. Baseline-only оценка search проверена сквозным
прогоном; генерация изменений через модель ещё не запускалась. Нативный evaluator запускает C++
обычным локальным процессом; отдельная папка и `.venv` не являются sandbox.

## Будущий запуск — только по отдельному запросу

Настройка сама ничего не запускает. После разрешения на эксперименты команда
имеет вид:

```sh
/Users/555tery/techarena/shinka-pipes/run.sh --run --generations 20
```

Без `--run` поиск не стартует; без положительного `--generations` запуск отклоняется.
Один generation может включать несколько обращений к CLI, поэтому это не точный
лимит запросов или расхода подписки. Запуск сначала оценивает initial baseline.
Результаты сохраняются в новой папке `runs/`. Платформа не используется.

## Восстановление зависимостей

```sh
cd /Users/555tery/techarena/shinka-pipes
uv sync --locked
npm ci --prefix runtime --no-audit --no-fund
```

Node должен быть версии 22 или новее. Git-зависимость Headless при установке
собирает свой CLI; эта сборка не вызывает Codex и не запускает эксперименты.

Первичные источники: [ShinkaEvolve](https://github.com/SakanaAI/ShinkaEvolve),
[Headless](https://github.com/RobertTLange/headless-cli),
[Codex authentication](https://learn.chatgpt.com/docs/auth).
