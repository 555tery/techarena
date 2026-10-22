# Windows 10 / Pentium G5420 / одно ядро

Цель, указанная пользователем: Windows 10 64-bit 22H2, Pentium Gold G5420 3.80 GHz, 16 GB RAM. Contest limits остаются 5 секунд CPU и 256 MiB на solver; объём RAM всей машины их не меняет.

## Что исправлено

- Windows CPU timer: `GetProcessTimes`, сумма user + kernel. Ожидание interactor не считается CPU; деления на число ядер/потоков нет. Solver однопоточный.
- На POSIX используется `getrusage` с той же суммой user + system.
- Консервативный предварительный профиль: до 2.5 секунды дополнительного поиска, stop поиска при 3.8 секунды CPU процесса, envelope 4.0 секунды с резервом на ещё возможные команды и коэффициентом запаса 1.25.
- Memo доступен в двух размерах: 32 и 128 MiB. Default — 32 MiB; это кандидат для сравнения, не измеренный победитель на G5420. Arena до 80 MiB и до 8 снимков сохранены.
- Публичные планы Open15 не менялись. Старые frozen source, результаты и их hashes сохранены в прежнем эксперименте.

G5420 имеет 2 физических ядра / 4 потока и 4 MB общего кэша. В данном режиме используем один worker и одно разрешённое логическое CPU. Нельзя пересчитывать старые секунды по GHz или делить CPU time на 2/4. Кэш memo на 128 MiB намного больше аппаратного кэша; влияние на скорость нужно измерять.

## Сборка на Windows x64

Использовать уже установленный MSVC в **x64 Native Tools Command Prompt**, либо MinGW-w64 x64. `solution.cpp` — standalone source, это копия `cache32/solution.cpp`; обе версии отличаются define при компиляции.

MSVC:

```
cl /nologo /O2 /std:c++20 /EHsc /DPIPES_MEMO_BUCKET_LOG2=19 solution.cpp /Fe:solver32.exe kernel32.lib
cl /nologo /O2 /std:c++20 /EHsc /DPIPES_MEMO_BUCKET_LOG2=21 solution.cpp /Fe:solver128.exe kernel32.lib
```

MinGW-w64:

```
g++ -O2 -std=c++20 -march=x86-64 -mtune=generic -DPIPES_MEMO_BUCKET_LOG2=19 solution.cpp -o solver32.exe
g++ -O2 -std=c++20 -march=x86-64 -mtune=generic -DPIPES_MEMO_BUCKET_LOG2=21 solution.cpp -o solver128.exe
```

AVX/AVX2 не требуются. Не переносить `-march=native` с другого компьютера.

## Нативный замер

Если Python 3 уже установлен:

```
py windows_bench.py --solver solver32.exe --tests tests/stress --repeat 3 --out result32.json
py windows_bench.py --solver solver128.exe --tests tests/stress --repeat 3 --out result128.json
py windows_bench.py --solver solver32.exe --tests tests/open --repeat 1 --out open32.json
```

Runner привязывает только дочерний solver к одному разрешённому логическому CPU, подаёт по одной команде, проверяет интервалы и считает CPU процесса через WinAPI. Его Python-потоки относятся к runner, а не solver. Системные настройки и affinity остальных программ не меняются.

JSON содержит `CPU_user_plus_kernel_s`, отдельное `wall_s`, peak working set и peak private commit, KPI, input/binary hashes, affinity mask. Повторное использование существующего имени JSON запрещено, чтобы сохранить замеры. Это самостоятельная проверка протокола, **не официальный C++ interactor**.

## Статус доказательств

Нативного запуска на Windows/G5420 и Windows-компиляции в текущем окружении **нет**. Локальный host — macOS arm64. `local-validation.json` фиксирует только native-host smoke: все 15 Open15 и три стресс-потока для каждого размера memo. Таймер отдельно проверен на исключение сна; WinAPI-конверсия проверена stub unit, который не заменяет Windows SDK/runtime.

Прежние 4.20 секунды и результаты обобщения относятся к другому frozen source/host. Их нельзя объявлять результатами этого профиля на G5420. До получения `result32.json`/`result128.json` размер memo и бюджеты предварительные; 4.0 секунды — целевая envelope, не доказанная верхняя граница на всех входах.

Источники:

- [Intel G5420 specifications](https://www.intel.com/content/www/us/en/products/sku/135456/intel-pentium-gold-g5420-processor-4m-cache-3-80-ghz/specifications.html).
- [Microsoft CRT clock](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/clock?view=msvc-170).
- [GetProcessTimes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes).
- [Windows memory counters](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-process_memory_counters_ex).
