from pathlib import Path

OUT = Path(__file__).resolve().parent / 'synthetic'
OUT.mkdir(exist_ok=True)

profiles = {
    'staircase_unit': list(range(1, 41)),
    'staircase_two': list(range(1, 40, 2)),
    'staircase_four': list(range(4, 41, 4)),
    'geometric': [1, 2, 4, 8, 16, 32],
}
BATCH = 128
for name, lengths in profiles.items():
    commands = []
    pid = 0
    for length in lengths:
        ids = []
        for _ in range(BATCH):
            pid += 1
            ids.append(pid)
            commands.append(length)
        # Remove the first member of each within-length parity pair.
        commands.extend(-x for x in ids[::2])
    path = OUT / f'{name}.in'
    path.write_text(f'1.0\n{len(commands)}\n' + ' '.join(map(str, commands)) + '\n')
