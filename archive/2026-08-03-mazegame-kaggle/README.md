# MazegameCompKaggle — archived 2026-08-03

Moved here from the repository root at Jonathan's direction ("maze game can be
archived"). **Archived, not deleted** — house rule. Moved with `git mv`, so all
125 files keep their history; `git log --follow` works across the move.

## Why it was moved

It is a Kaggle maze-game competition entry, self-contained and unrelated to the
Codette reasoning system. Nothing in `reasoning_forge/`, `inference/`,
`ethics/` or `tests/` imports it.

It was also breaking the test suite. Its three test modules
(`test_v2_vs_v3.py`, `test_vs_random.py`, `test_vs_starter.py`) resolve their
agent files relative to the **current working directory** rather than their own:

```
FileNotFoundError: ...\spider5d-engine-core-49ed3d\main_refloor_673.py
FileNotFoundError: Could not find : main.py
```

`main.py` and `main_refloor_673.py` do exist — in this directory. So the tests
pass when run from inside it and raise at *collection* time when run from the
repository root. Because a collection error aborts the whole run, these three
files stopped `pytest` from collecting **any** of the other 595 tests.

## State it was archived in

Not broken, just directory-dependent. To run it:

```bash
cd archive/2026-08-03-mazegame-kaggle/MazegameCompKaggle && python -m pytest
```

The path-resolution bug is recorded, not fixed — it was never fixed because the
project works from its own directory, and archiving is not the moment to change
its behaviour. 348 MB, including 113 replay files under `replays/`.
