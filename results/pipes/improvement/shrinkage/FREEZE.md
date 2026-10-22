# Зафиксированный adaptive-кандидат

По заранее зарегистрированному max-min критерию среди adaptive-кандидатов заморожен `s50_shrink_tau128`.

- Исходник: `source/adaptive_allocator.cpp`
- SHA-256 исходника: `5b0067000157e1e3d464b66ae5e91c207e04a1663b0953d58aa2500e417efb20`
- Бинарник: `binaries/s50_shrink_tau128`
- SHA-256 бинарника: `5454221dbecdc53a7347583df991cc6c788752810b6f82a4f55b98b10f225608`
- Compile defines: `PIPES_STRATEGY=4`, `PIPES_HISTORY_WINDOW=128`, `PIPES_PENALTY_SCALE=50`, `PIPES_SHRINK_TAU=128`
- Score: `slack * (history_size + 128) + 50 * prior_requests_larger_than_slack`

Показатели: открытые `28.354366985731556/32.1`, development `1.866240842895806/4`; отношения к P4 — `0.9992433487` и `0.9976997452`, поэтому max-min равен `0.9976997452`. Это лучший adaptive tradeoff среди зафиксированного списка, но P4 выше на обоих наборах. Значит, улучшения P4 на обоих наборах не обнаружено.

Подбор использовал только официальные открытые тесты и четыре исходных development synthetic-потока. Frozen suite не запускался для выбора. Параметр больше не подстраивался после фиксации результата.
