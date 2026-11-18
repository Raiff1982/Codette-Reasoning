# media/ — CodetteMediaEngine, extracted

Extracted on 2026-11-18 by Jonathan's decision (`docs/APPROVALS_2026-11-18.md`, item 6).
The source is `Movie_engine.py` at the repository root. That file is a **chat transcript**,
not a module: it holds three versions of this engine and, between them, a message to Jonathan
offering four directions to extend it. **It is left untouched** (house rule: originals stay).

| File here | From `Movie_engine.py` | What it is |
|---|---|---|
| `codette_media_engine.py` | lines 386–800 | **"Full Pipeline Orchestration"**: JSON render plans, `CodetteMediaPipeline`, a `--plan` command line. The direction the message recommended. Contains every class and method of the other two |
| `lineage/codette_media_engine_subsystems.py` | lines 1–207 | the version with four subsystems (`MediaIntake`, `CompositionPipeline`, `AudioSynchronizer`, `RenderLayer`) |
| `lineage/codette_media_engine_single_class.py` | lines 208–283 | the simpler single-class version |
| (not extracted) | lines 284–385 | the message between versions. It is prose and stays in the transcript |

The order in which A and B were written cannot be told from the file; the names describe what
each contains, not which came first.

## What was repaired, and nothing else

1. Non-breaking spaces that stood in for indentation were replaced with spaces (each indent step
   was written as `NBSP + space`).
2. Each segment's module docstring had lost its opening `"""` with its first line; restored.
3. Then `tools/archive_diff.py`'s `repair()`. On this input it changed nothing more.

No line of code was changed. `tools/archive_diff.py` could not do this on its own: its last
repair keeps the longest prefix that parses, and this file breaks on line 1, so no prefix parses.
The split into segments was done by reading the content.

## Running it

    pip install -r media/requirements.txt
    python media/codette_media_engine.py --plan my_plan.json

A plan:

```json
{
  "clips": ["intro.mp4", "scene1.mp4"],
  "audio": {"path": "music.mp3", "volume": 0.8},
  "text_overlays": [{"text": "Codette", "duration": 3, "fontsize": 60}],
  "output": {"path": "out.mp4", "width": 1280, "height": 720, "fps": 30}
}
```

## Verified, and not

- **Verified 2026-11-18, in a container:** all three import with moviepy 1.0.3. `main(["--plan",
  ...])` rendered two 1-second clips plus a tone into a 2.00 s, 320×240 video with audio.
- **Pillow:** moviepy 1.0.3 calls `PIL.Image.ANTIALIAS`, which Pillow 10 removed, so resizing fails
  with `module 'PIL.Image' has no attribute 'ANTIALIAS'`. Use `Pillow<10` where wheels exist
  (Python ≤ 3.11). The test run above, on Python 3.13, set `PIL.Image.ANTIALIAS =
  PIL.Image.LANCZOS` in the test only; the engine itself was not changed.
- **Not tested:** text overlays. moviepy's `TextClip` needs ImageMagick, which was not installed.
- Nothing in Codette imports this. It is a standalone tool.
