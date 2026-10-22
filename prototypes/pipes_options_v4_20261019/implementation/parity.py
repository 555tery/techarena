#!/usr/bin/env python3
"""Compile C++ inference probe and compare exported sklearn fixtures exactly."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model-dir",required=True,type=Path)
    ap.add_argument("--cxx",default="c++")
    args=ap.parse_args()
    model=args.model_dir.resolve()
    fixtures=json.loads((model/"parity_fixtures.json").read_text())["fixtures"]
    source=Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="options-v4-parity-") as temp:
        probe=Path(temp)/"probe"
        subprocess.run([args.cxx,"-O2","-std=c++17",f'-DMODEL_HEADER="{model / "model.hpp"}"',str(source/"probe.cpp"),"-o",str(probe)],check=True)
        inputs="".join(" ".join(format(x,".17g") for x in row["features"])+"\n" for row in fixtures)
        result=subprocess.run([str(probe)],input=inputs,text=True,capture_output=True,check=True)
    lines=result.stdout.splitlines()
    if len(lines)!=len(fixtures):
        raise ValueError("probe row count mismatch")
    worst=0.
    for i,(line,expected) in enumerate(zip(lines,fixtures)):
        parts=line.split()
        if len(parts)!=5:
            raise ValueError("probe must output 4 gains and chosen option")
        actual=list(map(float,parts[:4]))
        error=max(abs(a-b) for a,b in zip(actual,expected["gains"]))
        worst=max(worst,error)
        if error>1e-12 or int(parts[4])!=expected["option"]:
            raise ValueError(f"inference parity mismatch at fixture {i}: {line}")
    print(json.dumps({"status":"pass","fixtures":len(fixtures),"max_abs_gain_error":worst,"option_mismatches":0}))

if __name__=="__main__":
    main()
