"""Record a local recommendation separately from the saved platform submission."""
import json
from pathlib import Path
from evaluate import HERE, ROOT


def main():
    outcome = json.loads((HERE/'outcome.json').read_text())
    final = json.loads((HERE/'analysis-final.json').read_text())
    assert outcome['recommended'] == 'hybrid'
    page = f'''# Online, полный replay и осторожный гибрид

Локальный раунд 20 октября 2026: пользователь разрешил отказаться от максимума Open15 ради обобщаемости.
[Отчёт](../../prototypes/pipes_closed_ready_20261020/report.html), [план до результатов](../../prototypes/pipes_closed_ready_20261020/experiment.json), [исходник выпуска](../../prototypes/pipes_closed_ready_20261020/release/solution.cpp), [пакет Windows](../../prototypes/pipes_closed_ready_20261020/closed-ready.zip).

## Сравниваемые политики

Общее ядро — trial22, SHA `988927c6…1242e4`. Online после namespace/emit-обёртки побайтно равен исходному trial22 на всех Open15 (280156 команд). Full использует совместную таблицу Open15 до расхождения, затем без ограничений старого Planner/episode продолжает тем же ядром из реального состояния. Hybrid дополнительно разрешает replay только при `newT <= shadowOnline.T` и размещении на границе физического свободного промежутка. При отказе навсегда переключается на online.

Импорт восстанавливает причинную историю, lifetime/cohort/run/Fenwick-модели. Ownership всех физических щелей становится shared, age — последняя эпоха удаления; чужие slab reservations снимаются. Это общий механизм full/hybrid, не эквивалент запуска online с начала. Ограничение hybrid относится к длине траншеи во время replay, не гарантирует качество будущего suffix.

## Заранее заданная проверка

Три политики, calibration64 (32 ordinary +32 prefix), отдельные final128 (64+64), Open15 и три stress по200000 команд. Генератор не читал кандидатов/результатов; final ordinary содержит новые композиции16 механизмов. Prefix охватывает все15 публичных тестов и8 типов suffix. Все195 новых файлов уникальны, нет совпадений с590 hash-токенами из12 перечисленных старых manifests; это ограниченная проверка дубликатов.

До результатов зафиксированы допуски относительно online: family-macro каждого stratum не ниже более чем на0.002; ни один ordinary KPI не ниже80% online; корректность/ресурсы. Среди допустимых — минимальный максимальный regret сценариев `Open15+84*((1-p)*ordinary+p*prefix)`, p=0/1, tie0.01 в пользу простоты. На calibration выбран hybrid; full не прошёл prefix-допуск. Выбор и бинарники frozen до final. Это анализ чувствительности, не оценка неизвестного распределения закрытых.

## Независимые результаты

| Вариант | Open15 | Ordinary macro KPI | Prefix macro KPI | Final: wins/ties/losses vs online |
|---|---:|---:|---:|---:|
| Online |30.09096789|0.87589466|0.82134447|0/128/0|
| Full |30.75747405|0.87619414|0.77679836|16/88/24|
| Hybrid |30.10271159|0.87586574|0.82096387|8/114/6|

Hybrid прошёл заранее заданное подтверждение. Худшая потеря vs online: −0.03858477; у full −0.78050420. Средняя ΔKPI hybrid по всем128 =−0.00020623: улучшение обобщаемости относительно online **не установлено**. Family-bootstrap95% включает0 в обеих группах. Рекомендация hybrid следует заранее выбранному критерию и сохраняет +0.01174370 Open15 относительно online; это малое преимущество, а не универсальное доминирование. При ретроспективном повторном выборе с tie0.01 final предпочёл бы online; после final политика не перенастраивалась.

## Выпуск и ресурсы

В выпуске изменён только ввод/вывод: ручной integer parser, POSIX read/write или WinAPI ReadFile/WriteFile. Reverse replacements восстанавливают frozen source побайтно. Ответы совпали на210 входах / {outcome['exact_output_parity_commands']} командах. Затем пройдены210 официальных интерактивных запусков выпуска; вместе с630 исходными сравнительными —840 запусков.

SHA256 выпуска `{outcome['source_sha256']}`. Максимум CPU **{outcome['selected_maximum_cpu_s']:.6f} с**, RSS **{outcome['selected_maximum_rss_mib']:.3f} MiB** на macOS arm64, один solver worker. Windows10/G5420 и нативная MSVC-сборка **не проверены**; пакет содержит исходник, build script и runner с привязкой к одному CPU, user+kernel time и независимой проверкой размещений. 16GB RAM машины не меняют лимит256MiB процесса.

Платформа не использовалась; canonical и старые frozen источники сохранены. Последняя известная отправка по сохранённому журналу — speed-v29 без поддержки неизвестных входов, не этот выпуск. Данные final128 теперь наблюдались и годятся для регрессии; следующая настройка требует новых независимых входов.
'''
    assert len(page.encode()) < 8192
    (ROOT/'wiki/research/Closed-ready-comparison.md').write_text(page)
    home = ROOT/'wiki/Home.md'
    text = home.read_text()
    link = '- [Сравнение online, replay и осторожного гибрида](research/Closed-ready-comparison.md) — новый набор64+128, отказ от максимума Open15, выпуск с быстрым I/O и честными границами переноса.\n'
    if link not in text:
        text = text.replace('## Исследования и отчёты\n\n', '## Исследования и отчёты\n\n'+link)
        assert len(text.encode()) < 8192
        home.write_text(text)
    status = ROOT/'wiki/project/Current-state.md'
    text = status.read_text()
    if '20 октября: **локальный hybrid**' in text:
        print('wiki already current')
        return
    paragraphs = text.split('\n\n')
    paragraphs[1] = '20 октября: **локальный hybrid**, Open15 **30.10271159**, новые64+128 тестов. Превосходство над online по обобщаемости не установлено. [Выпуск и сравнение](../research/Closed-ready-comparison.md).\n\nПоследний сохранённый срез платформы19 октября: **speed-v29**, **1666321**, 15/15 Accepted, **30.75747405**, неизвестные входы не поддерживает. Платформа сейчас не проверялась. [Журнал](../../prototypes/pipes_open15_overfit_20261019/continuation/platform-speed-20261019/result.json).'
    text = '\n\n'.join(paragraphs)
    assert len(text.encode()) < 8192
    status.write_text(text)
    print('wiki updated')


if __name__ == '__main__':
    main()
