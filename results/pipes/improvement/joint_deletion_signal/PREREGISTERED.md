# Совместные удаления соседних труб: preregistration v3

## Вопрос и границы вывода

Проверяется, улучшает ли причинный прогноз «оба PID пары удалены в следующие 128 команд» relation-specific зависимость сверх общей индивидуальной hazard-модели концов пары. Это проверка сигнала, не allocator-эксперимент. Синтетика с конечным заданным log-OR — positive control процедуры, но не свидетельство закономерности реальных Pipes-потоков. Open15 и holdout-v2 — только описательные prequential-диагностики: Open15 использовался при разработке, holdout-v2 переиспользован. Никакой результат не разрешает менять solver или выбирать правило размещения.

Полный синтетический DGP, seeds и изоляция eval-файлов зафиксированы в [Synthetic-DGP.md](Synthetic-DGP.md). Hash-freeze и exact file-set для локальных Open15/holdout traces описаны в [Local-traces.md](Local-traces.md).

## Горизонт, пары и estimand

- `H=128`. Snapshot после первых `t` команд использует для outcome только команды `t+1,…,t+128`; окна соседних snapshots не пересекаются.
- Активные трубы сортируются по `(start,pid)`. Greedy matching идёт слева направо: взять `(i,i+1)`, только если `start[i]+length[i]==start[i+1]`, после пары перескочить оба PID; иначе перейти на следующую трубу. `relation=1` тогда и только тогда, когда длины пары равны. PIDs и relation фиксируются в момент snapshot; исходы отслеживаются для этих PID, даже если геометрия затем меняется.
- `PAIR_CAP=256`. При `M≤256` используются все пары. При `M>256` нумеровать пары `0,…,M−1` в matcher order и выбрать `floor(((2j+1)M)/(2·256))`, `j=0,…,255`; реализация — целочисленное `((2*j+1)*M)//512`. Повторов нет.
- Estimand — предсказательный loss на capped matched pairs. Inclusion weights не применяются: thinning детерминированный, а не вероятностная выборка. При `M>256` вывод не переносится автоматически на все пары; возможен selection bias по координате, геометрии и relation. Exposure weights не исправляют его.
- Outcome `Y=1`, если оба исходных PID удалены хотя бы раз в горизонте; сохраняются также `Y_A,Y_B`. В snapshot PID не более чем в одной паре; PID может появиться в следующих snapshots.

## Сравниваемые модели

Обе модели используют одинаковые индивидуальные `p_A,p_B`. Features конца: точная длина `1–40`; age band `(<128,128–511,512–2047,>=2048)` команд; newest-rank quartile `floor(4*newer/(active_count−1))`, clipped `0–3` (новейший `0`); parity порядкового размещения точной длины, включая уже удалённые трубы. Hierarchical Beta rate имеет global prior `Beta(1,9)` и уровни `(L)`, `(L,age)`, `(L,age,rank)`, `(L,age,rank,parity)` с shrinkage mass `8` к родителю. Вес endpoint `1/(1+c)`, где `c` — число его ранее созревших appearances среди capped matched pairs в этом stream.

- Marginal-only: `q0=p_A*p_B`.
- Joint: только relation-specific `theta_r∈[-3,3]` как log odds ratio; старт `mu=0, precision=1`. На созревших парах с сохранёнными snapshot `p_A,p_B` выполняется online Newton/Laplace update weighted composite likelihood с expected information. Вес пары `sqrt(w_A*w_B)`, без нормировки по snapshot. `q_theta=P(Y_A=1,Y_B=1)` задаётся odds-ratio уравнением.
- Маргинали одинаковы; меняется только зависимость исходов условно на маргинали и relation. Окна не пересекаются, пары внутри snapshot disjoint. Повторные PID получают exposure weights, неопределённость кластеризуется по целым streams.

## Прогрев, метрики и неопределённость

Для `N` snapshots фиксируется `W=floor(N/2)`. Индексы `0,…,W−1` — несчётный warmup: labels обновляют модели, прогнозы в метрики не входят. Индексы `W,…,N−1` — scoring. Перед прогнозом snapshot раскрывается только outcome предыдущего окна. Пустые scoring snapshots считаются, но не входят в среднее; отчёт указывает `N`, `W` и число непустых окон.

На каждом непустом snapshot pair scores усредняются с нормированными exposure weights, затем snapshots усредняются поровну внутри stream. Основные proper scores — Brier и log-loss; improvement=`loss(marginal-only)−loss(joint)`, положительное лучше. Вероятности ограничиваются `[1e−12,1−1e−12]`. Calibration — weighted observed rate минус weighted mean prediction по relation и фиксированным bins `[0,.01,.025,.05,.10,.20,.40,.60,1]`. Paired bootstrap 10,000 раз целыми streams, seed `202610171337`; режимы synthetic и каждый local dataset оцениваются отдельно. Pairs, snapshots и endpoints не считаются независимыми репликами.

Для synthetic `N=156`: warmup `0–77`, scoring `78–155`. В phase-прогнозе epoch 78 обучен только на independent outcomes; последующие прогнозы обновляются по созревшим grouped outcomes. Подробности и режимные semantics — в [Synthetic-DGP.md](Synthetic-DGP.md).

## Запреты и review gates

Порядок review и отдельные разрешения для smoke, synthetic generation/scoring и local hash-freeze/scoring заданы в [Synthetic-DGP.md](Synthetic-DGP.md) и [Local-traces.md](Local-traces.md). Review не запускает следующий шаг автоматически; evaluator валидирует names и SHA до первого trace parse/score.

Локальный solver не перезапускать. Не использовать test ID или будущие команды как признаки, не объединять datasets. Docker и сайт не используются; solver/canonical source не менять. Даже положительный predictive result лишь ставит вопрос о следующем отдельном review на solver-impact experiment.

Frozen final solver source SHA-256 `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`; binary SHA-256 `dabb6910bde7550dbf4ab03d6d7b450d0a91f53a90dc06e52d6b271c8602000c`.
