# Команды воспроизведения

Все бинарники собраны с Apple clang 17.0.0, C++20 и флагами -O2 -pipe -Wall -Wextra -Wpedantic -Werror. Точная команда сборки, макросы политики, source и бинарный SHA-256 указаны для каждого варианта в build_manifest.csv.

build_manifest.csv содержит полную точную команду официального harness для каждого открытого варианта. Использовались tools/interactor, data/pipes/open и лимиты --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120.

Точные команды вторичной синтетической проверки записаны в synthetic_manifest.csv. Проверены ранее использованные holdout-v1 и development; stdout сохранён в соответствующих .console.log файлах.
