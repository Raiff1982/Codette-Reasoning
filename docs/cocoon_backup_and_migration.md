# Cocoon Backup And Migration

Codette's memory and session continuity can be moved between machines if you copy the right files.

## Main Files

- `data/codette_memory.db`
  - unified cocoon memory
- `data/codette_sessions.db`
  - saved session state
- `cocoons/`
  - legacy or supplemental cocoon artifacts

## Minimum Backup

For most users, backing up these two files is enough:

```text
data/codette_memory.db
data/codette_sessions.db
```

## Safer Full Backup

Also include:

```text
cocoons/
data/results/
demo/outputs/
logs/
```

## Migration Steps

1. Stop the server on the source machine.
2. Copy the files/directories above.
3. Place them in the same relative locations on the destination machine.
4. Start the server.
5. Verify with:
   - `GET /api/session`
   - `GET /api/governor`
   - continuity recall in the UI

## Privacy Note

Cocoons and saved sessions can contain:
- user prompts
- system responses
- continuity summaries
- decision landmarks
- cited web research summaries

Treat them as potentially sensitive data.

## Export And Import

The server also supports session export/import endpoints:
- `POST /api/session/export`
- `POST /api/session/import`

Those are useful for moving specific conversations without copying the entire database.
