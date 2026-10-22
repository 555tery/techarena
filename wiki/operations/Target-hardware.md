# Целевая машина и измерение CPU

Уточнение пользователя от 20 октября 2026:

- Windows 10 64-bit 22H2;
- Intel Pentium Gold G5420, 3.80 GHz;
- 16 GB RAM;
- CPU time solver считается на одном ядре.

Contest limits по [условию](../task/Rules-and-protocol.md): 5 секунд CPU / 256 MiB на тест. RAM всей машины не является memory limit процесса.

## Следствия для реализации

Solver остаётся однопоточным. Для проверки закреплять его на одном разрешённом логическом CPU; CPU=user+kernel процесса, без деления на число физических ядер или SMT-потоков. Ожидание ввода не относится к CPU time.

Microsoft CRT `clock()` возвращает wall time, поэтому для Windows используется `GetProcessTimes`. POSIX-ветка — `getrusage(user+system)`. Источники: [clock](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/clock?view=msvc-170), [GetProcessTimes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes).

У G5420 4 MB общего кэша ([Intel](https://www.intel.com/content/www/us/en/products/sku/135456/intel-pentium-gold-g5420-processor-4m-cache-3-80-ghz/specifications.html)). Размер memo 128 MiB не означает ускорение на этом CPU. Подготовлено сравнение 32/128 MiB, без утверждения победителя до нативного замера.

## Артефакты

- [Отдельный аппаратный профиль и инструкции](../../prototypes/pipes_g5420_cpu_20261020/README.md).
- [Standalone source](../../prototypes/pipes_g5420_cpu_20261020/cache32/solution.cpp).
- [Windows runner на одном CPU](../../prototypes/pipes_g5420_cpu_20261020/windows_bench.py).

Бюджеты предварительные: process envelope 4.0 s, до 2.5 s дополнительного поиска; коэффициент 1.25 к резерву оставшейся работы. Это настройка запаса, не подтверждённое время на G5420.

Текущее окружение — macOS arm64. Его замеры нельзя пересчитывать в G5420 по частоте процессора или выдавать за Windows-run. Старые frozen результаты сохранены отдельно; качество изменённого аппаратного профиля не наследуется автоматически.
