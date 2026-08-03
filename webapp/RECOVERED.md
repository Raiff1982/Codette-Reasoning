# Recovered application

Every file in this directory came out of the `Archive*.zip` uploads, not from
direct authorship. It is the `project-bolt-github-yy5xfj9y` build — a FastAPI
backend with HMAC request authentication, a React + Vite + Tailwind frontend,
Supabase edge functions and roughly thirty SQL migrations.

(This directory is listed in RECOVERY_MANIFEST.md.) Individual files carry no provenance header because headers would break the
JSON, SQL and config formats here. `RECOVERY_MANIFEST.md` at the repository root
is the authority.

## Two things deliberately excluded

- **`.env`** — held a live Supabase anon key. That key is public by design and
  the tables it reaches have row-level security with 61 policies, so this is
  hygiene rather than an incident, but a `.env` does not belong in version
  control. `.env.example` is kept.
- **`model/codette2.tar.gz`** — a 972 KB binary.

The committed content was scanned for secret-shaped strings before landing and
none were found.

## Not the only build

Six `project-bolt-*.zip` copies across the archives resolve to two distinct
builds. `project-bolt-codettev3`, `project 2` and `project 3` are byte-identical
to each other (68 files); this is the larger one (90 files). Taking the larger
build did lose one file the smaller had — `cognitive_processor.py` — which is
preserved separately at `recovered_release/cognitive_processor.py`.

Note the repository's `web/` directory is unrelated: it is a two-file reverse
proxy for the Hugging Face Space.
