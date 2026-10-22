#!/usr/bin/env python3
"""Export double weights without quantization; optionally select an audited checkpoint."""
import argparse
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("weights", type=Path)
p.add_argument("header", type=Path)
a = p.parse_args()
values = [float(x) for x in a.weights.read_text().split()]
assert len(values) == 105 and all(abs(x) < 1e100 for x in values)
text = '#pragma once\n#include "policy.hpp"\nnamespace trajectory {\ninline constexpr Weights TrainedWeights{{\n'
text += ',\n'.join(format(x, '.17g') for x in values)
text += '\n}};\n}\n'
a.header.write_text(text)
a.header.with_suffix(a.header.suffix + '.json').write_text(json.dumps({
    'weights_file': str(a.weights.resolve()),
    'weights_sha256': hashlib.sha256(a.weights.read_bytes()).hexdigest(),
    'header_sha256': hashlib.sha256(a.header.read_bytes()).hexdigest(),
    'architecture': '24->4 tanh->1', 'parameters': 105,
    'quantization': None,
    'roundtrip_exact': all(float(format(x, '.17g')) == x for x in values),
}, indent=2) + '\n')
