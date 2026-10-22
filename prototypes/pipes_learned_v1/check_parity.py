#!/usr/bin/env python3
"""Compare exported C++ and NumPy scores AND actual action choices."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'train'))
import train_mlp as trainer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('model')
    parser.add_argument('probe')
    parser.add_argument('csv')
    parser.add_argument('report')
    args = parser.parse_args()
    model = json.loads(Path(args.model).read_text())
    data = trainer.load_csv(Path(args.csv))
    tensors = model['weights']
    params = {
        'w1': np.array(tensors['w1_row_major_128x32'], dtype=np.float32).reshape(128, 32),
        'b1': np.array(tensors['b1'], dtype=np.float32),
        'w2': np.array(tensors['w2'], dtype=np.float32),
        'b2': np.array([tensors['b2']], dtype=np.float32),
    }
    mean = np.array(model['normalization']['mean'], dtype=np.float32)
    scale = np.array(model['normalization']['scale'], dtype=np.float32)
    normalized = np.clip((data.x - mean) * scale, -8, 8)
    predictions = trainer.forward(normalized, params)[2]
    text = '\n'.join(' '.join(format(float(v), '.9g') for v in row) for row in data.x) + '\n'
    result = subprocess.run([str(Path(args.probe).resolve())], input=text, capture_output=True, text=True, check=True)
    cpp = np.array([float(v) for v in result.stdout.split()], dtype=np.float32)
    assert len(cpp) == len(predictions)
    margin = np.float32(model['deployment_margin'] if model['deployable'] else 1e30)

    def choices(scores, old_double=False):
        selected = []
        for gid, rows in enumerate(data.group_rows):
            base = int(data.baseline_row[gid])
            best = min(rows, key=lambda row: (float(scores[row]), data.action[row]))
            difference = (float(scores[base]) - float(scores[best]) if old_double
                          else np.float32(scores[base] - scores[best]))
            selected.append(int(best) if best != base and difference > margin else base)
        return np.array(selected)

    py_choice = choices(predictions)
    cpp_choice = choices(cpp)
    old_choice = choices(predictions, old_double=True)
    report = {
        'rows': len(cpp), 'states': data.groups,
        'max_score_abs_difference': float(np.max(np.abs(cpp - predictions))),
        'mean_score_abs_difference': float(np.mean(np.abs(cpp - predictions))),
        'action_mismatches_python_vs_cpp': int(np.sum(py_choice != cpp_choice)),
        'old_double_threshold_action_mismatches': int(np.sum(old_choice != py_choice)),
        'cpp_changes': int(np.sum(cpp_choice != data.baseline_row)),
        'model_sha256': hashlib.sha256(Path(args.model).read_bytes()).hexdigest(),
        'probe_sha256': hashlib.sha256(Path(args.probe).read_bytes()).hexdigest(),
        'csv_sha256': data.sha256,
    }
    Path(args.report).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    assert report['max_score_abs_difference'] < 5e-5
    assert report['action_mismatches_python_vs_cpp'] == 0


if __name__ == '__main__':
    main()
