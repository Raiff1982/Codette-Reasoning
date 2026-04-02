# Demo Outputs

Saved local demo runs belong in this folder.

Recommended artifact types:
- `local_demo_YYYYMMDD_HHMMSS.json`
- `local_demo_YYYYMMDD_HHMMSS.md`

These files are useful as proof because they preserve:
- exact requests
- exact returned JSON
- latency per call

Generate them with:

```bash
python demo/run_local_api_demo.py
python demo/run_local_api_demo.py --include-web
```
