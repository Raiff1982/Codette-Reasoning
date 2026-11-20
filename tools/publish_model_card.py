#!/usr/bin/env python3
"""Publish a reviewed model card to the Hugging Face Hub. Manual, one file at a time.

Added 2026-11-20. The Hugging Face connector the assistant works with can read the
Hub but not write to it (a direct write came back 403, the pull-request route an
authorization error). Jonathan's answer: it has to go through GitHub. So the card
lives in this repository, is reviewed and merged here, and this script, run by
.github/workflows/publish-model-card.yml when he presses Run, sends it. The token
is his and lives in a GitHub secret; nothing here asks for it in chat.

THE RULES (each one is a way an upload tool can go wrong, turned round):

  1. ALLOWLIST. Only the cards named in CARDS can be sent, each from a fixed source
     file to a fixed destination. Nothing on the command line or in a workflow
     input can name another file or another repository. Adding a card is a
     reviewed change to this file.
  2. ONE FILE, ONE COMMIT. A single README. Never a folder, never weights.
  3. NOTHING THAT LOOKS LIKE A CREDENTIAL. A card containing a token-shaped string
     is refused, so a pasted key cannot be published. The match is never printed.
  4. VERIFIED. After the upload the script downloads that exact revision and
     compares its sha256 with the source. A mismatch fails the run.
  5. THE TOKEN STAYS OUT OF OUTPUT. Read from HF_TOKEN only, never printed, and
     scrubbed from any error text.
  6. --dry-run does everything except talk to the Hub, and needs no token.

Stock, said plainly: huggingface_hub's HfApi.upload_file and hf_hub_download, and
the argparse / exit-code layout. Written for this project: the allowlist, the
credential-shape refusal, the verify-after-upload step, and a dry run that works
without a token. The Hub keeps the previous card in its history, so an upload
replaces nothing for good.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
CARD_DIR = Path("training") / "model_cards"
MAX_BYTES = 200_000

# name -> fixed source and destination. This is the whole of what can be published.
CARDS: Dict[str, Dict[str, str]] = {
    "empathy_v4": {
        "source": "training/model_cards/empathy_v4_README.md",
        "repo_id": "Raiff1982/codette-adapters-v4",
        "repo_type": "model",
        "path_in_repo": "empathy/README.md",
        "message": "Add model card for the empathy v4 adapter",
    },
}

# Shapes of credentials. A card containing one is refused (rule 3).
_SECRET_SHAPES = re.compile(
    r"hf_[A-Za-z0-9]{30,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9]{30,}")


class Refused(Exception):
    """The card was not sent, and why."""


class VerificationFailed(Exception):
    """The Hub's copy does not match the source."""


def load_card(name: str, root: Path = REPO_ROOT) -> Tuple[bytes, str]:
    """The card's bytes and sha256, or Refused. Touches nothing outside `root`."""
    if name not in CARDS:
        raise Refused(f"unknown card {name!r}; known cards: {', '.join(sorted(CARDS))}")
    card_dir = (Path(root) / CARD_DIR).resolve()
    src = (Path(root) / CARDS[name]["source"]).resolve()
    if card_dir not in src.parents:
        raise Refused(f"{CARDS[name]['source']} is not inside {CARD_DIR.as_posix()}/")
    if not src.is_file():
        raise Refused(f"{CARDS[name]['source']} does not exist")
    data = src.read_bytes()
    if not data.strip():
        raise Refused("the card is empty")
    if len(data) > MAX_BYTES:
        raise Refused(f"the card is {len(data)} bytes; the limit is {MAX_BYTES}")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise Refused("the card is not UTF-8 text") from None
    if "\x00" in text:
        raise Refused("the card contains a NUL byte")
    if not text.startswith("---\n") or text.find("\n---\n", 4) == -1:
        raise Refused("a Hub card starts with a front matter block between two '---' lines")
    if _SECRET_SHAPES.search(text):
        raise Refused("the card contains text shaped like a credential (not shown)")
    return data, hashlib.sha256(data).hexdigest()


def describe(name: str, data: bytes, digest: str) -> str:
    c = CARDS[name]
    return "\n".join([
        f"card        : {name}",
        f"source      : {c['source']}",
        f"size        : {len(data)} bytes",
        f"sha256      : {digest[:16]}...",
        f"destination : hf://{c['repo_type']}s/{c['repo_id']}/{c['path_in_repo']}",
    ])


def publish(name: str, token: str, provenance: str, root: Path = REPO_ROOT) -> str:
    """Upload one card, then download that revision and compare. Returns the revision."""
    data, digest = load_card(name, root)
    card = CARDS[name]
    import huggingface_hub                 # late, so --dry-run and every refusal never need it

    api = huggingface_hub.HfApi(token=token)
    info = api.upload_file(
        path_or_fileobj=data,
        path_in_repo=card["path_in_repo"],
        repo_id=card["repo_id"],
        repo_type=card["repo_type"],
        commit_message=card["message"],
        commit_description=(f"Published by tools/publish_model_card.py from {card['source']} "
                            f"(sha256 {digest[:16]}). {provenance}"),
    )
    revision = getattr(info, "oid", None) or "main"
    fetched = huggingface_hub.hf_hub_download(
        repo_id=card["repo_id"], filename=card["path_in_repo"], repo_type=card["repo_type"],
        revision=revision, token=token)
    got = hashlib.sha256(Path(fetched).read_bytes()).hexdigest()
    if got != digest:
        raise VerificationFailed(
            f"the Hub's copy at {revision} has sha256 {got[:16]}..., the source has {digest[:16]}...")
    return revision


def _scrub(text: str, token: Optional[str]) -> str:
    return text.replace(token, "***") if token else text


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description="Publish one reviewed model card to the Hugging Face Hub.")
    ap.add_argument("card", choices=sorted(CARDS), help="which card (the list is in this file)")
    ap.add_argument("--dry-run", action="store_true",
                    help="check and print what would be sent; send nothing and read no token")
    ap.add_argument("--provenance", default="a manual run of tools/publish_model_card.py",
                    help="where this run came from, recorded in the Hub commit description")
    args = ap.parse_args(argv)

    try:
        data, digest = load_card(args.card)
    except Refused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    print(describe(args.card, data, digest))

    if args.dry_run:
        print("dry run: nothing was sent and no token was read")
        return 0

    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        print("STOPPED: the HF_TOKEN secret is not set, so nothing was sent. Add it under "
              "Settings, Secrets and variables, Actions (a fine-grained token with write "
              "access to the one model repository).", file=sys.stderr)
        return 3
    try:
        revision = publish(args.card, token, args.provenance)
    except Refused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    except VerificationFailed as e:
        print(f"NOT VERIFIED: {_scrub(str(e), token)}", file=sys.stderr)
        return 4
    except Exception as e:                                       # report, never hide
        print(f"FAILED: {type(e).__name__}: {_scrub(str(e), token)}", file=sys.stderr)
        return 5
    print(f"published and verified at revision {revision}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
