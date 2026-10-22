# TECH ARENA Pipes — последние 20 вариантов

Публичная подборка **20 последних вариантов решения** и фактических данных их тестирования.
Варианты отобраны по времени изменения исходников, от новых к старым. Cached/uncached объединены в одной папке; диагностические программы и промежуточные трансформации исключены. Два C++ reference внутри core-ring/core-qualified нужны для привязки результатов к исходникам; это не дополнительные варианты.

## Состав

- `versions/` — 20 вариантов, **29 файлов исходников**. В каждой папке `manifest.json` с SHA-256 и исходными командами сборки, `test-results.jsonl` с записями проверок.
- `tests/inputs/` — **3081 уникальный тестовый вход**, по одному gzip-файлу на SHA-256 исходного содержимого. Все входы, на которые ссылаются сохранённые проверки, найдены.
- `tests/cases.jsonl` — хеши, размеры, количество операций и происхождение тестов.
- `tests/platform-observations.json` — подтверждённые серверные результаты и границы привязки к исходникам.
- `tests/comparison-summaries.jsonl` — сохранённые общие сравнения; контрольные методы из них могут находиться за пределами этих 20 вариантов.
- `tools/pipes_harness.py`, `vendor/pipes_official/` — существующий интерактивный harness и официальный interactor.

Большого архива исследований, установленных SDK, бинарников, окружений и кэшей в репозитории нет. Локальный проект сохранён отдельно.

## Варианты

В столбце «Входов» — объединение входов с успешными историческими записями по сборкам этого варианта. Число записей больше: есть повторы, разные режимы и переиспользованные результаты. Это не одинаковый набор для ранжирования всех вариантов.

| №, новые первыми | Вариант | Файлов кода | Входов | Записей проверок |
|---|---|---:|---:|---:|
| 01 | [candidate-scratch](https://github.com/555tery/techarena/tree/main/versions/01-candidate-scratch) | 1 | 0 | 0 |
| 02 | [sparse-dp](https://github.com/555tery/techarena/tree/main/versions/02-sparse-dp) | 1 | 21 | 24 |
| 03 | [boundary-full](https://github.com/555tery/techarena/tree/main/versions/03-boundary-full) | 2 | 391 | 437 |
| 04 | [boundary-index](https://github.com/555tery/techarena/tree/main/versions/04-boundary-index) | 2 | 3032 | 3129 |
| 05 | [speed-m](https://github.com/555tery/techarena/tree/main/versions/05-speed-m) | 2 | 35 | 70 |
| 06 | [speed-b](https://github.com/555tery/techarena/tree/main/versions/06-speed-b) | 2 | 35 | 70 |
| 07 | [speed-h](https://github.com/555tery/techarena/tree/main/versions/07-speed-h) | 2 | 35 | 70 |
| 08 | [coalescence-side](https://github.com/555tery/techarena/tree/main/versions/08-coalescence-side) | 1 | 396 | 396 |
| 09 | [ordinary-bf-large](https://github.com/555tery/techarena/tree/main/versions/09-ordinary-bf-large) | 1 | 396 | 396 |
| 10 | [ordinary-bf-all](https://github.com/555tery/techarena/tree/main/versions/10-ordinary-bf-all) | 1 | 396 | 396 |
| 11 | [core-ring](https://github.com/555tery/techarena/tree/main/versions/11-core-ring) | 3 | 3079 | 7103 |
| 12 | [core-qualified](https://github.com/555tery/techarena/tree/main/versions/12-core-qualified) | 3 | 3079 | 3748 |
| 13 | [oriented-guarded](https://github.com/555tery/techarena/tree/main/versions/13-oriented-guarded) | 1 | 271 | 271 |
| 14 | [recent-hazard](https://github.com/555tery/techarena/tree/main/versions/14-recent-hazard) | 1 | 271 | 271 |
| 15 | [side-only](https://github.com/555tery/techarena/tree/main/versions/15-side-only) | 1 | 271 | 271 |
| 16 | [early-only](https://github.com/555tery/techarena/tree/main/versions/16-early-only) | 1 | 271 | 271 |
| 17 | [absolute-firstfit](https://github.com/555tery/techarena/tree/main/versions/17-absolute-firstfit) | 1 | 56 | 56 |
| 18 | [absolute-bestfit](https://github.com/555tery/techarena/tree/main/versions/18-absolute-bestfit) | 1 | 56 | 56 |
| 19 | [core-guarded-envelope](https://github.com/555tery/techarena/tree/main/versions/19-core-guarded-envelope) | 1 | 2953 | 3168 |
| 20 | [guarded-envelope](https://github.com/555tery/techarena/tree/main/versions/20-guarded-envelope) | 1 | 271 | 271 |

`candidate-scratch` не имеет подтверждённых локальных прогонов в журнале. Последняя серверная посылка 1669236 имела TLE15, но её исходник не был независимо выгружен и сопоставлен по хешу: этот результат не приписывается scratch-кандидату автоматически.

## Подтверждённые результаты

Cangjie `boundary-index/release`, SHA `9360f948…aafc`: отправки **1669133 / 1669221**, **15/15 Accepted, Open15 30.05605**. Версия `boundary-index/uncached`, SHA `f1f6240f…ac4a`: **1669215, TLE15**, 14/15 Accepted, 20.50542. Последняя наблюдавшаяся 1669236 также имела TLE15; вернуть принятую версию до закрытия формы не удалось.

Без кэша №15 занял локально около **1.53 с CPU в batch** и **2.03–2.11 с интерактивно** на M1, но не прошёл серверные 5 с на Windows/Pentium G5420/Cangjie 1.0.5. Локальные времена и Accepted закэшированной версии не доказывают скорость на новых больших тестах.

На общем архиве 3029 средний KPI C++: старый trial22 **0.9224477094**, нынешнее чистое online **0.9279840250**, осторожный гибрид **0.9292757071**. Open15 соответственно **30.0909678913 / 30.0443143281 / 30.0560580256**. Архив неоднороден; эти средние не являются прогнозом закрытого счёта. Для новых speed-кандидатов полнота проверки различается — сверяйте `test-results.jsonl` и SHA.

## Логика online-ядра и TLE

Код индексирует свободные щели, объединяет их после удалений и расширяет траншею по 20 м. Выбор щели учитывает недавние размеры; DP по окну 256 операций оценивает полезность `V(g)` для щелей до 512 м и сравнивает потерю `V(g)-V(g-l)`. Дополнительно используются возраст/порядок удалений, серии размеров, сторона размещения и ограниченные rollout глубиной 4.

Кэш `Transcript15` выдаёт ответы того же гибрида на точном совпадении; при расхождении молча восстанавливает состояние на прочитанном префиксе. Он обходит работу online-ядра на совпадающем входе, поэтому успех Open15 с кэшем не устраняет риск TLE на закрытых. Предполагаемые затраты — DP, контейнеры/индексы, управление памятью и интерактивный протокол. Серверного профиля для точного разделения причин нет.

## Повторная проверка

Распаковать входы с проверкой хешей:

```sh
python3 tools/unpack_tests.py unpacked-tests
```

Команды исходных сборок лежат в `versions/*/manifest.json`; сохранены реальные параметры и исходные локальные пути, которые нужно адаптировать к своей системе. Cangjie требует внешний SDK. Наблюдавшиеся проверки преимущественно использовали 1.0.5 `-O0`; C++ — `-O2`. В C++ обязательные `-D` определяют политику; не опускайте их.

Пример проверки уже собранного solver:

```sh
mkdir -p build
clang++ -O2 -std=c++17 vendor/pipes_official/interactor.cpp -o build/interactor
python3 tools/pipes_harness.py --solver ./build/pipes --interactor build/interactor \
  --tests unpacked-tests --name repeat --out runs/repeat
```

Сохранённые записи не изменены: оболочка указывает исходный журнал и строку. Хеш ответа — свидетельство использованного полного ответа, но сами большие stdout-трассы в эту компактную подборку не включены. Повторных запусков solver при публикации не выполнялось.
