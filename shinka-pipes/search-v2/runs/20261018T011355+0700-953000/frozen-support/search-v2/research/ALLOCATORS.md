# malloc jemalloc и mimalloc в задаче Pipes

Практические аллокаторы дают три пригодных направления для следующего поиска: сохранять расширяемый хвост, учитывать возраст равноценных свободных дыр и проверять повторное заполнение текущих регионов. Разбиение, слияние, поиск по размеру и группировка размещений уже есть в нашем коде. Для переноса важны конкретные отличия политик, а не названия библиотек. Задания и абляции — в [ALLOCATOR_IDEAS.md](ALLOCATOR_IDEAS.md).

## Область сравнения

`malloc` — интерфейс, его реализации различаются. Здесь разобраны GNU libc malloc на commit `04e750e75b73957cf1c791535a3f4319534a52fc`, jemalloc на `7a34f18502e7b222724097cdcd499b437d189acc` и mimalloc на `d4881d338125e1cb7c47ba4cfb398d6f7c0c8d45`. Это не разбор системного malloc macOS. Историческое описание dlmalloc используется с его оговоркой об устаревших деталях; текущие glibc-правила сверены по коду.

Для Pipes труба соответствует неперемещаемому блоку, установка и удаление — allocate/free. Поток онлайн, длины точные 1–40, будущее неизвестно. Вместо heap/RSS оценивается итоговая необратимая длина единой траншеи, растущей секциями по 20. В SEARCH используется среднее B/T с равным весом семей, B=20 ceil(peak live volume / 20). CPU и RSS — ограничения, а не самостоятельная награда за скорость.

Сравниваются исходный [baseline](../../task-synthetic/initial.cpp) и [gen2 SEARCH-v1](../../runs/20261017T232542+0700-833000/gen_2/main.cpp). Во время начала разбора gen2 был лучшим сохранённым корректным кандидатом по read-only снимку базы. Дальнейшие поколения этим сравнением не охвачены. Исходником подготовленного v2 остаётся baseline; версии и SHA — в [reviewed-code.json](reviewed-code.json).

## GNU libc malloc

GNU malloc управляет chunks внутри arenas, а крупные запросы может обслуживать отдельными mappings. Соседние свободные chunks могут объединяться независимо от их размеров. Это следует из [официального руководства](https://sourceware.org/glibc/manual/latest/html_node/The-GNU-Allocator.html); alignment и метаданные всё равно создают накладные расходы.

В обычных bins используются порядок размеров и FIFO для равных размеров. `_int_malloc` также содержит ограниченное повторное использование `last_remainder`; путь `use_top` оставляет расширяемый верхний chunk после обычного поиска. Объединение с соседями выполняют `_int_free_merge_chunk` и `_int_free_create_chunk`. Cache-пути имеют собственные правила, поэтому весь современный malloc нельзя назвать одним чистым best-fit. См. [bins](https://github.com/bminor/glibc/blob/04e750e75b73957cf1c791535a3f4319534a52fc/malloc/malloc.c#L1482), [last remainder](https://github.com/bminor/glibc/blob/04e750e75b73957cf1c791535a3f4319534a52fc/malloc/malloc.c#L3968), [top](https://github.com/bminor/glibc/blob/04e750e75b73957cf1c791535a3f4319534a52fc/malloc/malloc.c#L4310), [merge](https://github.com/bminor/glibc/blob/04e750e75b73957cf1c791535a3f4319534a52fc/malloc/malloc.c#L4420).

У [Doug Lea](https://gee.cs.oswego.edu/dl/html/malloc.html) отдельно объяснены wilderness preservation и oldest-first: хвост сохраняют ради будущего расширения, недавно освобождённым блокам оставляют шанс объединиться. Это мотивирует H4/H5. Возврат mappings, trimming, минимальный размер chunk и отложенное объединение ради скорости непосредственно в Pipes не нужны: его координаты не являются адресами процесса, а слияние дыр уже выполняется.

## jemalloc

Малые объекты распределяются по size classes, внутри slab свободные позиции учитываются bitmap. `tcache` сокращает обращения к общим структурам, но удержание объектов в нём может увеличивать память и фрагментацию. Для Pipes таблица байтовых классов и округление занятой длины не переносятся. См. [Implementation Notes](https://jemalloc.net/jemalloc.3.html#IMPLEMENTATION_NOTES).

`bin_malloc_no_fresh_slab` сначала использует `slabcur`; при исчерпании `bin_refill_slabcur_no_fresh_slab` берёт slab из `slabs_nonfull`, и лишь после отсутствия такого slab требуется новый. Порядок — serial number, затем address; это **не выбор самого заполненного slab**. У `bin_lower_slab` есть переход к более старому/низкому доступному slab, поэтому текущий slab не обязательно сохраняется до заполнения при любых frees. См. [bin.c](https://github.com/jemalloc/jemalloc/blob/7a34f18502e7b222724097cdcd499b437d189acc/src/bin.c#L155), [переключение](https://github.com/jemalloc/jemalloc/blob/7a34f18502e7b222724097cdcd499b437d189acc/src/bin.c#L212), [allocation](https://github.com/jemalloc/jemalloc/blob/7a34f18502e7b222724097cdcd499b437d189acc/src/bin.c#L289), [comparator](https://github.com/jemalloc/jemalloc/blob/7a34f18502e7b222724097cdcd499b437d189acc/include/jemalloc/internal/edata.h#L777).

У extent-пула есть дополнительное ограничение отношения размера повторно используемого extent к запросу. В просмотренном `extent_recycle_extract` оно действует для cache с delayed coalescing, кроме pinned pool; в остальных случаях ограничение снимается. См. [код условия](https://github.com/jemalloc/jemalloc/blob/7a34f18502e7b222724097cdcd499b437d189acc/src/extent.c#L441), [eset_first_fit](https://github.com/jemalloc/jemalloc/blob/7a34f18502e7b222724097cdcd499b437d189acc/src/eset.c#L277), [manual](https://jemalloc.net/jemalloc.3.html#opt.lg_extent_max_active_fit). В Pipes немедленное слияние уже есть, а utility учитывает ценность большого остатка; поэтому прямое копирование ratio=64 и подбор этого порога оставлены за пределами приоритетных H4–H6. Защита больших дыр заслуживает отдельного задания, только если будет сформулировано отличие от текущей utility и независимая абляция.

Slab reuse мотивирует H6; purge/decay управляют физической памятью, а retain — её виртуальным резервированием. Они не уменьшают уже вырытую траншею. См. [dirty decay](https://jemalloc.net/jemalloc.3.html#opt.dirty_decay_ms), [retain](https://jemalloc.net/jemalloc.3.html#opt.retain).

## mimalloc

Работа [Free List Sharding in Action, 2019, §§2–3](https://www.microsoft.com/en-us/research/wp-content/uploads/2019/06/mimalloc-tr-v1.pdf) объясняет списки свободных блоков на страницах одного size class и временную локальность размещений. Близость времени выделения не раскрывает будущий срок жизни. В Pipes выигрыш возможен через геометрию освобождений; cache locality как таковая в его score не входит.

В просмотренной v3 сначала проверяется первая страница очереди. Медленный путь `mi_page_queue_find_free_ex` собирает освобождённые блоки и просматривает очередь в next-fit порядке; после появления кандидата ограничивает дальнейший поиск, содержит предпочтение более заполненной страницы и переносит выбранную вперёд. Если текущих кандидатов нет, пытается получить fresh page. Ограничение кандидатов не означает константного полного прохода: до первого кандидата может быть просмотрено много страниц. См. [slow path](https://github.com/microsoft/mimalloc/blob/d4881d338125e1cb7c47ba4cfb398d6f7c0c8d45/src/page.c#L944), [выбор и fresh page](https://github.com/microsoft/mimalloc/blob/d4881d338125e1cb7c47ba4cfb398d6f7c0c8d45/src/page.c#L1024), [fast path](https://github.com/microsoft/mimalloc/blob/d4881d338125e1cb7c47ba4cfb398d6f7c0c8d45/src/page.c#L1061). Это мотивирует ограниченный вариант H6, а не полное копирование очереди.

`local_free` и отдельные concurrent frees разделяют быстрый путь и сбор освобождений. Их задержка не является доказанным приёмом улучшения упаковки. Abandonment/reclaim управляют владением страницами, purge — физической памятью. Для последовательного Pipes перенос этих механизмов не обоснован. См. [local free](https://github.com/microsoft/mimalloc/blob/d4881d338125e1cb7c47ba4cfb398d6f7c0c8d45/src/free.c#L27), [collection](https://github.com/microsoft/mimalloc/blob/d4881d338125e1cb7c47ba4cfb398d6f7c0c8d45/src/page.c#L387), [purge](https://github.com/microsoft/mimalloc/blob/d4881d338125e1cb7c47ba4cfb398d6f7c0c8d45/src/arena.c#L1454).

## Сопоставление с нашим кодом

| Механизм | Baseline | SEARCH-v1 gen2 | Решение для следующего поиска |
|---|---|---|---|
| Разбиение и слияние дыр | `consumeAtSide`, `addFreeGap` | `place`, `remove`, `insertGap` | Уже есть; не отдельная новая идея |
| Поиск по размеру | `freeBySize`, частоты размеров и остаток | `bySize_`, DP utility, риски соседей | Не заменять всё общим заданием «добавь best-fit» |
| Сохранение хвоста | Обычный ranking общий; есть узкое исключение в counterfactual mode | Хвост явно добавляется в общий конкурс | H4: общий приоритет доступных внутренних дыр |
| Возраст свободной дыры | В основном индексе только длина и адрес | В `Gap` нет `freeSince`, по размеру выбираются крайние адреса | H5: FIFO среди действительно равноценных дыр |
| Повторное заполнение регионов | Специальные cohort slabs, серии, parity routing | Группы риска и двухфронтовая арена | H6: текущий регион точного размера с общим fallback |
| Рост | Обычный путь минимальный; cohort slab может резервировать больше | `growFor` может добавлять `extraDigs` для арены | Не добавлять новый резерв под H6; в абляции рост одинаков |
| Будущее время удаления | Наблюдаемые шаблоны и короткий rollout | Deaths/exposure по размеру и фазам | Ни один из трёх аллокаторов не предоставляет нам отсутствующие признаки; H1 остаётся отдельной гипотезой |

Одна реализация может содержать полезные и неподходящие для Pipes части одновременно. Установка jemalloc/mimalloc для внутренних контейнеров solver могла бы изменить CPU/RSS, но сама по себе не меняет правило выбора координат труб. В следующий prompt передаются механизмы H4–H6, ограничения и абляции; метрика, seed, модель, budget gate и изоляция SEARCH остаются прежними.
