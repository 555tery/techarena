---
name: edit-program
description: Edit a program for next experimentation.
---

# What the skill is about
Create the next program variant safely for iterative optimization experiments.

# When to use the skill
- After reviewing the latest evaluation results (or at the very beginning).
- When you want to test a new idea without overwriting previous attempts.

# What to do
1. Find the next unused program index `<idx>` from `./program_<idx>`.
2. Clone the full previous program project (`program_<idx-1>`) into the new `program_<idx>` with the trusted clone utility:
   - `${TASK_PYTHON:-$WRAPPER_PYTHON} -I -m src.investigation.program_clone --from "./program_<idx-1>" --to "./program_<idx>"`
   - The utility creates the destination and applies the `program_spec.toml` copy rules without carrying evaluator artifacts.
   - For every source after `program_0`, the utility refuses to clone until canonical evaluation and mirrored rubric artifacts prove the previous iteration is complete.
   - Do not use `cp`, `cp -r`, `cp -a`, `rsync`, or any other recursive copy. If the trusted clone fails, stop the attempt and report the error; do not fall back to another clone method.
4. Edit code under `./program_<idx>/src/**` (and update `program_spec.toml` if you change entrypoint or language).
5. Keep all older `program_<idx>` directories unchanged.
6. Never edit `./evaluate.py` or `./capture.py`.
7. Before creating `program_<idx>`, ensure previous evaluated `program_<idx-1>` already has:
- `metrics.json`
- `correct.json`
- `program_<idx-1>/rubric_status.json`
- `./rubric_status.json` mirrored to that latest evaluated artifact
8. If latest rubric status has `overall_pass: true`, stop; do not create another program directory.
9. Single-attempt evaluation cap: never create/evaluate beyond `program_2`.

# Example usage
```bash
${TASK_PYTHON:-$WRAPPER_PYTHON} -I -m src.investigation.program_clone --from "./program_2" --to "./program_3"
# edit ./program_3/src/** (and ./program_3/program_spec.toml if needed)
```
