#!/usr/bin/env python3
"""Build the pure Cangjie port using an explicit, local SDK."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import time

BASE = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sdk', type=Path, default=BASE / 'toolchain/cangjie')
    parser.add_argument('--source', type=Path, default=BASE / 'src')
    parser.add_argument('--output', type=Path, default=BASE / 'bin/solution-cj')
    parser.add_argument('--opt', default='2', choices=['0', '1', '2', 's', 'z'])
    args = parser.parse_args()
    sdk = args.sdk.resolve()
    env = os.environ.copy()
    env['CANGJIE_HOME'] = str(sdk)
    compiler = sdk / ('bin/cjc.exe' if os.name == 'nt' else 'bin/cjc')
    flags = ['-O' + args.opt]
    if platform.system() == 'Darwin':
        env['SDKROOT'] = subprocess.check_output(['xcrun', '--sdk', 'macosx', '--show-sdk-path'], text=True).strip()
        flags.append('--set-runtime-rpath')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    command = [str(compiler), *flags, '-p', str(args.source.resolve()), '-o', str(args.output.resolve())]
    started = time.time()
    result = subprocess.run(command, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log = args.output.with_suffix('.build.log')
    log.write_text(result.stdout)
    record = {'command': command, 'sdk_version': subprocess.check_output([str(compiler), '--version'], text=True),
              'returncode': result.returncode, 'duration_s': time.time() - started,
              'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(args.source.glob('*.cj'))},
              'SDKROOT': env.get('SDKROOT'), 'host': platform.platform()}
    if result.returncode == 0:
        record['binary_sha256'] = hashlib.sha256(args.output.read_bytes()).hexdigest()
    args.output.with_suffix('.build.json').write_text(json.dumps(record, indent=2) + '\n')
    print(result.stdout[-6000:])
    print('Build exit:', result.returncode, 'Log:', log)
    raise SystemExit(result.returncode)

if __name__ == '__main__':
    main()
