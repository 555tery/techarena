"""Recompute Open11's exact bound and validate an existing attaining plan.

This is a local audit, not an optimization or platform submission.
"""
import collections,decimal,hashlib,importlib.util,json,subprocess
from fractions import Fraction
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    path=ROOT/'data/pipes/open/11.in'
    judge_src=ROOT/'vendor/pipes_official/interactor.cpp'
    plan_path=ROOT/'prototypes/pipes_open15_overfit_20261019/continuation/pool-order/joint-best.txt'
    solver_dir=ROOT/'prototypes/pipes_closed_ready_20261020/candidates/full'
    original_hashes={line.split()[1]:line.split()[0] for line in (ROOT/'data/pipes/SHA256SUMS').read_text().splitlines()}
    for p in [path,judge_src,judge_src.with_name('testlib.h')]:
        assert sha(p)==original_hashes[str(p.relative_to(ROOT))]
    tokens=path.read_text().split();weight=Fraction(tokens[0]);n=int(tokens[1]);ops=list(map(int,tokens[2:2+n]));trailing=tokens[2+n:]
    assert len(ops)==n and trailing==['0'] and weight==1
    plan=list(map(int,plan_path.read_text().split()))
    assert sha(plan_path)=='4e843f995e6c7ec664114b386a79cc2850b8b11e96765d70ad01a4530f59d10a'
    live={};lengths={};births={};deaths={};cells=[];pid=0;volume=0;peak=-1;peak_certificate=None
    for i,c in enumerate(ops,1):
        if c>0:
            assert 1<=c<=40;pid+=1;lengths[pid]=c;births[pid]=i;live[pid]=c;volume+=c
            x=plan[pid-1];assert x>=0;end=x+c;T=((end+19)//20)*20
            if T>len(cells):cells.extend([0]*(T-len(cells)))
            assert all(v==0 for v in cells[x:end]),(i,'overlap')
            cells[x:end]=[pid]*c
        else:
            assert c<0 and -c in live,(i,'bad deletion')
            k=-c;length=live.pop(k);volume-=length;deaths[k]=i;x=plan[k-1]
            assert cells[x:x+length]==[k]*length,(i,'wrong pipe')
            cells[x:x+length]=[0]*length
        if volume>peak:
            peak=volume
            peak_certificate=dict(operation=i,command=c,occupied_length=volume,alive_count=len(live),
                length_histogram=dict(sorted(collections.Counter(live.values()).items())),
                alive_pids=sorted(live),plan_trench=len(cells))
    assert pid==len(plan) and sum(live.values())==volume==sum(c>0 for c in cells)
    # Independently reconstruct occupancy from half-open lifetime intervals.
    diff=[0]*(n+2)
    for k,L in lengths.items():
        diff[births[k]]+=L;diff[deaths.get(k,n+1)]-=L
    running=0;second_peak=-1;second_peak_at=[]
    for i in range(1,n+1):
        running+=diff[i]
        if running>second_peak:second_peak=running;second_peak_at=[i]
        elif running==second_peak:second_peak_at.append(i)
    assert second_peak==peak and running==volume
    lower=((peak+19)//20)*20;exact=weight*Fraction(volume,lower)
    assert len(cells)==lower==20760 and peak==20759 and volume==20361
    assert peak_certificate['operation']==9819 and peak_certificate['alive_count']==3019
    (HERE/'peak-certificate.json').write_text(json.dumps(peak_certificate,indent=2)+'\n')
    build=json.loads((solver_dir/'build.json').read_text())
    for name,key in [('solution.cpp','source_sha256'),('solver','binary_sha256')]:assert sha(solver_dir/name)==build[key]
    compile_cmd=['clang++','-std=c++17','-O2',str(judge_src),'-o',str(HERE/'interactor')]
    subprocess.run(compile_cmd,check=True,capture_output=True)
    spec=importlib.util.spec_from_file_location('h',ROOT/'tools/pipes_harness.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
    record=h.run_case([str(solver_dir/'solver')],HERE/'interactor',path,HERE/'official',5,60)
    assert record['status']=='ok' and record['trench_length_m']==lower and record['occupied_length_m']==volume
    (HERE/'official-result.json').write_text(json.dumps(record,indent=2)+'\n')
    decimal.getcontext().prec=60
    exact_decimal=decimal.Decimal(exact.numerator)/decimal.Decimal(exact.denominator)
    saved_score=(HERE/'official/score.txt').read_text().strip()
    rounding=decimal.Decimal(saved_score)-exact_decimal
    out=dict(status='verified_exact_optimum_for_this_input_and_rules',input_sha256=sha(path),
        interactor_source_sha256=sha(judge_src),testlib_sha256=sha(judge_src.with_name('testlib.h')),
        recompiled_interactor_sha256=sha(HERE/'interactor'),compile_command=compile_cmd,
        operation_count=n,ignored_trailing_zero=True,placements=pid,deletions=n-pid,final_alive_count=len(live),
        final_length_m=volume,peak_length_m=peak,peak_at=second_peak_at,peak_alive_count=peak_certificate['alive_count'],
        lower_trench_m=lower,exact_maximum_KPI_fraction=str(exact),exact_maximum_KPI_decimal=str(exact_decimal),
        plan_path=str(plan_path),plan_sha256=sha(plan_path),independent_meter_cell_plan_check='passed',
        attaining_solver_source_sha256=build['source_sha256'],attaining_solver_binary_sha256=build['binary_sha256'],
        official_run='ok',official_trench_m=record['trench_length_m'],official_final_occupied_m=record['occupied_length_m'],
        official_score_file=saved_score,rounding_above_exact_maximum=str(rounding),
        integer_overflow_in_normal_response_path='No: readInt bounds both cnt and shift to0..100000000, len<=32 here, PID<=6493, cells<=100000000. No signed32 overflow in checked sums or occupied count.',
        argument='At operation9819,3019 disjoint active pipes occupy20759m. A nondecreasing20m-section trench must have finalT>=20760. Final occupied volume is fixed20361m. Existing valid plan and recompiled official interactor attain20361/20760. Thus this is an exact optimum, not merely an optimistic ceiling.',
        limits='Checked the current local archived input and official interactor. No claim about an unknown different server version or unseen third-party transcript.',
        platform_actions=0,solver_changes=0)
    (HERE/'result.json').write_text(json.dumps(out,indent=2)+'\n')
    report=f'''Открытый тест №11: проверка максимума, 20 октября 2026

Для сохранённого официального входа и интерактора максимум точный:
KPI =20361/20760 =6787/6920 ={exact_decimal}.

После команды9819 (вставка трубы6419 длиной32) активны3019 труб,
их суммарная длина20759м. Они должны размещаться без пересечений.
Траншея не убывает и кратна20м, значит итоговая T>=20760м.
При T=20740 уже в этот момент не хватает19м независимо от алгоритма.
Финальная длина20361м задана входом и от размещений не зависит.

Проверены все9999 команд:6493 вставки,3506 корректных удалений.
В файле после заявленных9999 команд есть служебный0; официальный
интерактор читает ровно9999 команд и сам печатает завершающий0.
Он не меняет ни пик, ни финальный объём. Внутренних нулей нет.
Пик независимо пересчитан через активные PID и интервалы их жизни.

Ранее найденный план joint-best.txt прошёл свежую полную поклеточную
проверку. Сохранённый full-replay solver повторно прошёл заново собранный
официальный interactor:20361 занятая клетка,20760 клеток траншеи.
Следовательно граница достигается. Это не свидетельство качества
replay на неизвестных тестах и не изменение текущего online-ядра.

Уточнение округления: score.txt содержит {saved_score}, что больше
точной дроби на {rounding}. Причина — precision(9), девять значащих
цифр. Это численное округление, не улучшенный план или реальная
прибавка KPI. Более крупное превышение требует другого входа,
других правил/проверяющего кода либо ошибки в заявленных данных.

Текущее online-ядро в предыдущем проверенном прогоне имело22500м
и KPI0.9049333333: улучшить его на этом входе можно, превысить
точный максимум0.9807803468 корректным размещением нельзя.

Полные hashes и результаты:result.json, official-result.json.
Свидетельство пика:peak-certificate.json. Платформа не использовалась,
её текущий interactor и сторонняя неизвестная последовательность
ответов не проверялись. Старые исходники и входы не менялись.
'''
    (HERE/'REPORT.txt').write_text(report)
    print(json.dumps({k:out[k] for k in ['status','peak_length_m','peak_at','lower_trench_m','final_length_m','official_run','official_score_file','rounding_above_exact_maximum']},indent=2))

if __name__=='__main__':main()
