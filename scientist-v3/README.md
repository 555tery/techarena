# Agentic Scientist v3 для Pipes

> Справочник зафиксирован при настройке Scientist v3 и использует старый baseline `29.4471645435 / 32.1`. Он не описывает текущую frozen-final версию; см. [статус проекта](../wiki/project/Current-state.md).

Это отдельная интеграция [SakanaAI/AI-Scientist-v3](https://github.com/SakanaAI/AI-Scientist-v3) с текущим проектом Pipes. Upstream закреплён на commit `2b8aa39285c35aaca3b0e06dd121061ef8a2d854`; его исходники находятся в `upstream/`, а задача и evaluator — в `tasks/pipes/`.

## Что именно исследует Scientist

V3 здесь используется как цикл генерации гипотез и редактирования C++-эвристики. Он не обучает нейросеть автоматически. Кандидаты компилируются в C++20 и проверяются официальным интерактором на 15 открытых тестах. Целевая метрика — официальный взвешенный score открытого набора (максимум 32.1). Synthetic holdout, закрытые тесты и остальные результаты проекта в task snapshot не копируются.

Базовый кандидат — копия `src/pipes.cpp` на момент настройки; его зарегистрированный открытый score в проекте — `29.4471645435 / 32.1`. Это baseline, уже подобранный на открытых тестах, а не независимая оценка качества.

## Подготовка

Из корня проекта:

```sh
uv sync --project scientist-v3/upstream --python 3.12 --locked
./scientist-v3/build_images.sh
```

Первый скрипт создаёт отдельную `.venv` внутри `upstream/`. Второй собирает официальный агентский образ и производный образ с `g++`, нужным evaluator для компиляции редактируемых C++-кандидатов. Сборка требует запущенный Docker Desktop и доступ к Docker registry/package mirrors.

На macOS host-side скрипты upstream (`idea.sh`, `run.sh`, `task.sh`) требуют bash ≥ 4 (`mapfile -d`), а системный `/bin/bash` — 3.2. Установите bash 5 через Homebrew (`brew install bash`); `run_pipes.sh` сама добавляет `/opt/homebrew/bin` в PATH.

## Проверка и запуск

Сначала посмотреть конфигурацию без запуска агента:

```sh
./scientist-v3/run_pipes.sh --dry-run
```

Для реального цикла:

```sh
./scientist-v3/run_pipes.sh --run
```

Скрипт задаёт отдельный реальный temp-каталог в `scientist-v3/.tmp`, выбирает OpenCode CLI с моделью `zenpacer/glm-5.3-flash-free`, один worker, 3 idea cycles и не более 2 оценок на попытку; результаты сохраняются под `scientist-v3/runs/`. Авторизация — через `scientist-v3/opencode-auth/.config/opencode/opencode.json` с ключом OpenCode Zen (`OPENCODE_API_KEY`); этот каталог указывается как `container.auth_root` и целиком копируется в home агентского контейнера, env-ключи в контейнер не пробрасываются. Реальный запуск намеренно требует явного `--run`: upstream запускает coding agent с полными правами внутри контейнера и будет расходовать лимиты вашего OpenCode-ключа.

Любой запрос к LLM идёт через локальный пейсер `zen-pacer` (см. «Отклонения №3» в «Составе»): между двумя обращениями к реле Zen проходит не меньше минуты, а ответы 429/5xx автоматически перезапрашиваются в окне ~4 минут. Основная модель — самостоятельный провайдер `zenpacer` (`baseURL http://127.0.0.1:8787/v1`) в конфиге auth_root, избегающий фирменного special-casing провайдера `opencode`; провайдер `opencode` остаётся в конфиге только для вспомогательной nano-модели опенкода.

Для запуска сначала должны быть доступны Docker daemon и образ `agentic-scientist/pipes-cpp:2b8aa392`. В контейнере агент редактирует только snapshot задачи; evaluator запускается без сети. Не переносить в эту задачу `data/pipes/synthetic/final-holdout-v2` или закрытые тесты.

## Состав

- `upstream/` — базовый checkout SakanaAI AI-Scientist-v3 (rev `2b8aa392…`), Apache-2.0, с локальными отклонениями:
  - tmpfs `/tmp` в evaluator-контейнерах монтируется с `exec`: в `src/investigation/task_runtime.py` (baseline validation) и в `src/variants_pipeline/host_eval.py` (оценка кандидатов в песочнице). Без этого Docker tmpfs остаётся `noexec`, и evaluator не может запустить скомпилированный C++-бинарь Pipes: baseline падал с `[Errno 13] Permission denied`, а кандидаты — с `protocol_error` на всех 15 кейсах (`correct=false`, `combined_score=0.0`) при фактически корректных программах (проверено сквозным тестом: тот же кандидат с `exec` даёт `correct=true` и baseline-скор). Тот же `noexec` в `src/final_evaluation/runner.py` не патчился: фаза final_evaluation в `run_pipes.sh` не используется (`execution.phases=investigation`).
  - пауза между агентскими LLM-сессиями в `src/investigation/campaign_loop.py` (env `AGENTIC_REQUEST_PACING_SECONDS`, по умолчанию 0). Релей OpenCode Zen на бесплатном тарифе отбивает частые подряд запросы; `run_pipes.sh` выставляет 90 с.
  - in-container старт пейсера `src/scripts/lib/container_agent.sh`: перед первым exec в агентский контейнер запускается `python3 /home/agent-home/.config/opencode/zen_pacer.py` (docker exec -d, идемполементно, нефатально при отсутствии файла). Пейсер — HTTP-прокси на `127.0.0.1:8787` внутри контейнера: минимальный интервал между любыми запросами к `https://opencode.ai/inference/openai/v1` 30 с (`PACER_MIN_INTERVAL`), деадлайн на запрос 240 с (`PACER_DEADLINE_SECONDS`), 429/5xx ретраятся по тем же слотам. Провайдер `zenpacer` в `opencode-auth/.config/opencode/opencode.json` (`npm @ai-sdk/openai-compatible`, `options.baseURL` на пейсер, спецификация модели из каталога models.dev) — единственный способ завести поток запросов через прокси: каталожное поле `api` и `options.baseURL` у фигуранта `opencode` opencode игнорирует (провайдер намертво шьётся на `opencode.ai`).
  - обязательный prior-art скан в скилле генерации идей `src/agents/skills/create-idea/SKILL.md` (новый шаг 3): перед фиксацией идеи агент делает 2–4 быстрых веб-запроса (`webfetch` или `curl -s` к Semantic Scholar / arXiv) по алгоритмическому семейству предлагаемого механизма и фиксирует находки строкой «техника — источник — как влияет» в `notes_for_agent`. Причина: в upstream investigation-фазе нет шага работы с литературой (скилл `retrieve-references` принадлежит выключенной paper-фазе), идеи рождались только из своих же результатов. При недоступности сети скан помечается `prior_art: unavailable` и прогон не валится.
- `Dockerfile`, `build_images.sh` — слой образа с C++ compiler и воспроизводимая сборка.
- `run_pipes.sh` — dry-run и ограниченный investigation run (модель `zenpacer/glm-5.3-flash-free`, idea-таймаут 2700 с под пейсерную длительность).
- `tasks/pipes/` — snapshot стартового solver, открытые входы, официальный interactor, проектный harness и evaluator для v3.
- `.autorun.sh` — обёртка боевого запуска (до 3 попыток с кулдауном 300 с), журналы `.autorun.log` и `.pipeline_last.out`. Health-гейт с Probe-запросами больше не нужен: пейсер сам обеспечивает зазор между запросами и перезапрос на 429/5xx (проверено живым 429 в ретрай-режиме).
- `zen_pacer.py` (в `opencode-auth/.config/opencode/`, целиком валидированный на host 1.19.3 и в контейнере 1.18.29) — HTTP-пейсер; пишет журнал `zen_pacer.log` (в контейнере — /home/agent-home/zen_pacer.log) со строкой на каждый форвард.
