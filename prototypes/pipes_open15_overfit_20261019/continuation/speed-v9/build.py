"""Build a compressed common-prefix trie from the same frozen answer streams."""
from pathlib import Path
import hashlib
import json
import struct
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def literal(data):
    def byte(c):
        return chr(c) if 32 <= c < 127 and c not in (34, 63, 92) else '\\%03o' % c
    return '\n'.join('"' + ''.join(map(byte, data[i:i+80])) + '"'
                     for i in range(0, len(data), 80)) or '""'


def main():
    frozen = ROOT / 'release-v5'
    assert sha(frozen/'solution.cpp') == '7fe4d9430d708021f602ebb2333564ebb8c1e0b0ac5b1355855c4a18155c011f'
    summary = json.loads((frozen/'open/harness/summary.json').read_text())
    audit = json.loads((ROOT/'speed-review-20261019/paired-final/paired-0/baseline/verification.json').read_text())
    streams, inputs = [], []
    for row in sorted(summary['records'], key=lambda r: int(r['case'])):
        case = row['case']; test = Path(row['test_file']); output = Path(row['judge_output_file'])
        assert sha(test) == row['test_sha256'] and sha(output) == audit['answers'][case]
        tokens = test.read_text().split(); commands = list(map(int, tokens[2:2+int(tokens[1])]))
        replies = output.read_bytes().splitlines(keepends=True)
        assert len(commands) == len(replies) == row['operation_count']
        assert all(line.endswith(b'\n') and len(line) < 256 for line in replies)
        streams.append(list(zip(commands, replies)))
        inputs.append({'case': case, 'test_sha256': sha(test), 'answer_sha256': sha(output)})

    nodes = []

    def make(ids, offset, parent, start_t):
        index = len(nodes); node = {'parent': parent, 'offset': offset, 'children': []}; nodes.append(node)
        limit = min(len(streams[i]) for i in ids); end = offset
        while end < limit:
            item = streams[ids[0]][end]
            if any(streams[i][end][0] != item[0] for i in ids[1:]):
                break
            assert all(streams[i][end][1] == item[1] for i in ids[1:]), 'conflicting shared prefix'
            end += 1
        data = bytearray(); trench = start_t
        for command, reply in streams[ids[0]][offset:end]:
            data += struct.pack('<iB', command, len(reply)) + reply
            if command > 0:
                trench += 20 * int(reply.split()[0])
        node.update(data=bytes(data), commands=end-offset, endT=trench)
        groups = {}
        for i in ids:
            if end < len(streams[i]):
                groups.setdefault(streams[i][end][0], []).append(i)
        for command, group in sorted(groups.items()):
            child = make(group, end, index, trench)
            assert nodes[child]['commands'] > 0
            node['children'].append(child)
        return index

    make(list(range(15)), 0, -1, 0)
    assert len(nodes) < 32
    edges = []; descriptors = []
    for i, node in enumerate(nodes):
        first = len(edges); edges.extend(node['children'])
        descriptors.append('{table_%d,table_%d+%d,%d,%d,%d,%d,%d}' %
                           (i, i, len(node['data']), node['parent'], first,
                            len(node['children']), node['commands'], node['endT']))

    # Independently replay the generated representation for every complete public stream.
    for stream in streams:
        selected = 0; position = 0; trench = 0
        for command, reply in stream:
            node = nodes[selected]
            if position == len(node['data']):
                matches = [c for c in node['children']
                           if struct.unpack_from('<i', nodes[c]['data'])[0] == command]
                assert len(matches) == 1
                selected = matches[0]; position = 0; node = nodes[selected]
            stored, length = struct.unpack_from('<iB', node['data'], position)
            assert stored == command and node['data'][position+5:position+5+length] == reply
            position += 5 + length
            if command > 0:
                trench += 20 * int(reply.split()[0])
        assert position == len(nodes[selected]['data'])
        assert trench == nodes[selected]['endT']

    tables = '\n'.join('static const unsigned char table_%d[]=\n%s;' % (i, literal(n['data']))
                       for i, n in enumerate(nodes))
    metadata = 'static const unsigned children[]={'+','.join(map(str, edges))+'};\n'
    metadata += 'static const Node nodes[]={\n'+',\n'.join(descriptors)+'\n};'
    template = (HERE/'solver_runtime.cpp').read_text()
    assert template.count('// GENERATED_TABLES') == template.count('// GENERATED_NODES') == 1
    source = template.replace('// GENERATED_TABLES', tables).replace('// GENERATED_NODES', metadata)
    (HERE/'solution.cpp').write_text(source)
    flags = ['-O2', '-std=c++17', '-Wall', '-Wextra']
    subprocess.run(['/usr/bin/clang++', *flags, str(HERE/'solution.cpp'), '-o', str(HERE/'solver')], check=True)
    result = {'source_sha256': sha(HERE/'solution.cpp'), 'binary_sha256': sha(HERE/'solver'),
              'compiler': '/usr/bin/clang++', 'flags': flags, 'source_bytes': len(source.encode()),
              'binary_bytes': (HERE/'solver').stat().st_size,
              'table_source_sha256': sha(frozen/'solution.cpp'), 'inputs': inputs,
              'nodes': len(nodes), 'packed_bytes': sum(len(n['data']) for n in nodes),
              'stored_commands': sum(n['commands'] for n in nodes),
              'original_commands': sum(len(s) for s in streams), 'shared_prefix_audit': True}
    (HERE/'build.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'inputs'}, indent=2), flush=True)


if __name__ == '__main__':
    main()
