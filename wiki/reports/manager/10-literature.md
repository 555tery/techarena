# Литературная проверка

Материал перенесён из старого отчёта руководителю. Дата исходного среза указана в самом разделе.

## Литературная проверка

Pipes относится к online dynamic storage allocation: блоки непрерывны, перемещение запрещено, а время освобождения заранее неизвестно. В теории First Fit и другие online-алгоритмы имеют худшие случаи, зависящие от числа одновременно активных запросов; эти результаты дают контекст, но не предсказывают score конкретных тестов. [Luby, Naor & Orda, *Tight Bounds for Dynamic Storage Allocation*](https://epubs.siam.org/doi/abs/10.1137/S089548019325647X).

Lifetime-aware размещение в Microsoft Azure показало практическую пользу при наличии предсказаний времени жизни и механизмов, устойчивых к ошибкам. В Pipes наблюдаемый causal-сигнал оказался недостаточно полезным: лучшая проверенная hazard-эвристика ухудшила полный open-score и увеличила память. Это не опровержение метода в целом, а результат именно для доступного потока и текущих признаков. [Barbalho et al., *Virtual Machine Allocation with Lifetime Predictions*, MLSys 2023](https://proceedings.mlsys.org/paper_files/paper/2023/file/48eb2c79643df5cb7d125945238bd7d0-Paper-mlsys2023.pdf).

В сравнении Sum-of-Squares и Best Fit авторы сообщают, что в online memory allocation ни один метод не выигрывает последовательно; результат зависит от характеристик потока. Локальные SS-inspired варианты Pipes также проиграли. [Bender et al., *Sum-of-Squares Heuristics for Bin Packing and Memory Allocation*](https://www3.cs.stonybrook.edu/~bender/pub/JEA07-sumsquares.pdf).
