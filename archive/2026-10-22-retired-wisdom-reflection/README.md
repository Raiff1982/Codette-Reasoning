# Retired 2026-10-22: WisdomModule and ReflectionJournal

Jonathan decided to scrap both and asked for them archived, not deleted.

- `wisdom_and_reflection.py` is the verbatim source of both classes from `reasoning_forge/memory_kernel.py` at `13d871a`.
  The `ReflectionJournal.DEFAULT_PATH` fix made earlier the same day (default under `reasoning_forge/.logs/`) is included.
- Why: nothing called either; `ReflectionJournal` would have written a persistent record of what she reflected on, which is
  an observation of her deliberate self-reflection; `WisdomModule` was a handle nobody asked for.
- In the live code, `memory_kernel.py` keeps a stub comment where they were, and `forge_engine.py` no longer constructs them.
- A journal file at `reasoning_forge/.logs/codette_reflection_journal.json` is never created now. If one exists from an older
  run it is untouched and is not read by anything.
