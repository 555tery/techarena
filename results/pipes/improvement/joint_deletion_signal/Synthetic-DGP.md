# Synthetic DGP v3

Эта спецификация — planted positive control предсказательной процедуры. Она не является evidence о real Pipes-потоках. Все размещения и геометрия целевых пар должны идти из online-ответов frozen-final solver; пары не задаются напрямую генератором.

## Marginal hazards и finite association

На границе epoch для активной target трубы длины `L` и возраста `age` команд вычисляется

`p(L,age)=min(0.35, 0.08 + 0.012*floor((L−1)/5) + 0.02*a)`,

где `a=0` при возрасте `<128`, `1` при `128–511`, `2` при `512–2047`, `3` при `>=2048`. Значит каждый PID имеет свой hazard по длине и возрасту.

В independent mode все target PID получают независимые свежие `U(pid,epoch)~Uniform(0,1)` и событие `Y=1[U<p]`. В grouped mode на границе epoch применяется тот же greedy geometry matcher, что и в estimator. В каждом selected pair с равными длинами (`relation=1`) задаётся `OR=exp(2)`. Для маргиналей `p_A,p_B` находим `q` из

`q*(1−p_A−p_B+q) / ((p_A−q)*(p_B−q)) = exp(2)`

на интервале Fréchet `[max(0,p_A+p_B−1), min(p_A,p_B)]`. Затем берём два независимых свежих stateless draws от `(seed,epoch,pid)`: `Y_A=1[U_A<p_A]`; условно на `Y_A`, `Y_B=1[U_B<q/p_A]` при `Y_A=1`, иначе `Y_B=1[U_B<(p_B−q)/(1−p_A)]`. Так `P(Y_A=1)=p_A`, `P(Y_B=1)=p_B`, `P(Y_A=Y_B=1)=q` и log-OR равен 2. Другие трубы, включая пары `relation=0`, остаются независимы. Pair matching disjoint, так что target PID входит не более чем в один joint sampler за epoch. Используемые вероятности строго внутри `(0,1)`, поэтому условные пороги определены.

В phase mode epochs `0–77` independent, `78–155` grouped. Пары заново извлекаются на каждой границе по фактической геометрии. После замены PID их фактические размеры/координаты задаёт solver; искусственный lane или test label не назначается.

## Валидная команда Pipes

Каждый поток начинается с 32 целевых труб и setup ровно в 128 команд. Initial lengths:

`[4,4,4,7,7,7,10,10,10,13,13,13,16,16,16,19,19,19,22,22,22,25,25,25,28,28,28,31,31,31,34,34]`.

Setup дополняется `+1,-PID` filler циклом. Затем 156 epochs по 128 команд — всего 20,096 команд, завершающий `0` не включается. В каждом epoch 32 target PID обрабатываются по возрастанию PID. При событии добавляются команды `-PID`, `+L` той же длины и filler `+1,-PID`; без события — два filler `+1,-PID` цикла. Значит каждая target занимает ровно 4 команды и вся эпоха ровно 128 команд. Замена получает новый PID; filler удаляется сразу после размещения. Никакая труба не перемещается.

24 replicate на режим. Для `r=0,…,23` и индекса `m=0` independent, `1` grouped, `2` phase, `seed=202610170000+1000*m+r`. Режим и replicate известны только генератору, не предиктору. Draw использует stateless SplitMix64 keyed by seed, epoch и PID.

## Файлы, хеши и изоляция

Eval output фиксирован в `results/pipes/improvement/joint_deletion_signal/eval/{mode}/`. Корень `eval/` должен содержать ровно три mode directories. Для каждого режима допускается ровно 73 файла: `manifest.json` и 24 троицы `{mode}-{00..23}.in`, `{mode}-{00..23}.judge_output.txt`, `{mode}-{00..23}.metadata.json`. Manifest хранит фиксированный список stems/seeds, `OR`, source SHA-256 manifest и SHA каждого input/reply/metadata. Перед scoring evaluator hard-fail при неизвестном, отсутствующем или изменённом файле и сверяет manifest со source hashes. После review его SHA передаётся evaluator как `--approved-manifest-sha256`; отдельно нужен v3 approval token.

Smoke, если его отдельно разрешат, использует только `train-smoke/` в этой папке. Eval не glob-ит эту папку и не принимает из неё файлы. Генератор создаёт только новые каталоги и отказывается перезаписывать существующий `eval/` или `train-smoke/`, чтобы старые/лишние outputs не могли пройти как новый фиксированный набор.
