"""
Recovered from the Codette archives — see RECOVERY_MANIFEST.md
"""

#!/usr/bin/env python3
# unicode_shadow_scan.py
# Detect invisible Unicode, homoglyph tricks, bidi overrides, and mixed-script camouflage.
# Author: Generated for Jonathan (Raiff1982) — real, runnable code, no pseudo.

import sys
import json
import unicodedata as ud
from typing import Dict, Any, List, Tuple

ZERO_WIDTHS = {
    0x200B:"ZERO WIDTH SPACE",
    0x200C:"ZERO WIDTH NON-JOINER",
    0x200D:"ZERO WIDTH JOINER",
    0xFEFF:"ZERO WIDTH NO-BREAK SPACE (BOM)",
    0x2060:"WORD JOINER",
    0x180E:"MONGOLIAN VOWEL SEPARATOR"
}

BIDI_CONTROLS = {
    0x202A:"LEFT-TO-RIGHT EMBEDDING (LRE)",
    0x202B:"RIGHT-TO-LEFT EMBEDDING (RLE)",
    0x202D:"LEFT-TO-RIGHT OVERRIDE (LRO)",
    0x202E:"RIGHT-TO-LEFT OVERRIDE (RLO)",
    0x202C:"POP DIRECTIONAL FORMATTING (PDF)",
    0x2066:"LEFT-TO-RIGHT ISOLATE (LRI)",
    0x2067:"RIGHT-TO-LEFT ISOLATE (RLI)",
    0x2068:"FIRST STRONG ISOLATE (FSI)",
    0x2069:"POP DIRECTIONAL ISOLATE (PDI)",
    0x200E:"LEFT-TO-RIGHT MARK (LRM)",
    0x200F:"RIGHT-TO-LEFT MARK (RLM)"
}

# Selected homoglyph confusions relevant to Arabic/Persian and Latin/Cyrillic
HOMOGLYPH_PAIRS = [
    # Arabic vs Persian
    (0x064A, 0x06CC, "Arabic yeh vs Persian yeh"),
    (0x0643, 0x06A9, "Arabic kaf vs Persian keheh"),
    (0x0647, 0x06C1, "Arabic heh vs Urdu heh doachashmee"),
    (0x0649, 0x064A, "alef maksura vs yeh (visual confusion)"),
    # Latin vs Cyrillic
    (0x0061, 0x0430, "Latin a vs Cyrillic a"),
    (0x0065, 0x0435, "Latin e vs Cyrillic ie"),
    (0x006F, 0x043E, "Latin o vs Cyrillic o"),
    (0x0070, 0x0440, "Latin p vs Cyrillic er"),
    (0x0078, 0x0445, "Latin x vs Cyrillic ha"),
    (0x0041, 0x0410, "Latin A vs Cyrillic A"),
    (0x0045, 0x0415, "Latin E vs Cyrillic IE"),
    (0x004F, 0x041E, "Latin O vs Cyrillic O"),
]

def char_info(ch: str) -> Dict[str, Any]:
    cp = ord(ch)
    try:
        name = ud.name(ch)
    except ValueError:
        name = "<unnamed>"
    return {
        "char": ch,
        "codepoint": f"U+{cp:04X}",
        "category": ud.category(ch),
        "name": name
    }

def within(cp: int, start: int, end: int) -> bool:
    return start <= cp <= end

def detect_script(cp: int) -> str:
    # Very lightweight block-based detector for the main cases we care about.
    # Not exhaustive, but useful for mixed-script camouflage.
    if within(cp, 0x0600, 0x06FF) or within(cp, 0x0750, 0x077F) or within(cp, 0x08A0, 0x08FF) \
       or within(cp, 0xFB50, 0xFDFF) or within(cp, 0xFE70, 0xFEFF):
        return "Arabic"
    if within(cp, 0x0400, 0x04FF) or within(cp, 0x0500, 0x052F):
        return "Cyrillic"
    if within(cp, 0x0370, 0x03FF):
        return "Greek"
    if within(cp, 0x0000, 0x007F) or within(cp, 0x0080, 0x00FF) or within(cp, 0x0100, 0x017F) or within(cp, 0x0180, 0x024F):
        return "Latin"
    return "Other"

def analyze(s: str) -> Dict[str, Any]:
    nfc = ud.normalize("NFC", s)
    nfkc = ud.normalize("NFKC", s)
    cps = [ord(c) for c in s]
    infos = [char_info(c) for c in s]

    zero_widths = [i for i,c in enumerate(s) if ord(c) in ZERO_WIDTHS]
    bidi = [i for i,c in enumerate(s) if ord(c) in BIDI_CONTROLS]
    controls = [i for i,c in enumerate(s) if ud.category(c) in ("Cc","Cf") and ord(c) not in ZERO_WIDTHS and ord(c) not in BIDI_CONTROLS]
    ns_marks = [i for i,c in enumerate(s) if ud.category(c).startswith("M")]

    scripts = {}
    for c in s:
        sc = detect_script(ord(c))
        scripts[sc] = scripts.get(sc, 0) + 1
    mixed_scripts = len([sc for sc,cnt in scripts.items() if cnt>0 and sc!="Other"]) > 1

    # Homoglyph checks (pair-wise presence)
    present = set(ord(c) for c in s)
    homoglyph_hits: List[Tuple[str,str,str]] = []
    for a,b,desc in HOMOGLYPH_PAIRS:
        if a in present and b in present:
            homoglyph_hits.append((f"U+{a:04X}", f"U+{b:04X}", desc))

    report = {
        "original": s,
        "nfc": nfc,
        "nfkc": nfkc,
        "length": len(s),
        "codepoints": [f"U+{cp:04X}" for cp in cps],
        "chars": infos,
        "flags": {
            "has_zero_width": len(zero_widths) > 0,
            "has_bidi_controls": len(bidi) > 0,
            "has_other_controls": len(controls) > 0,
            "has_nonspacing_marks": len(ns_marks) > 0,
            "mixed_scripts": mixed_scripts,
        },
        "indices": {
            "zero_width_positions": zero_widths,
            "bidi_positions": bidi,
            "control_positions": controls,
            "nonspacing_mark_positions": ns_marks
        },
        "scripts": scripts,
        "homoglyph_collisions": homoglyph_hits
    }
    return report

def sanitize(s: str, map_persian_to_arabic: bool=True, strip_zero_widths: bool=True, strip_bidi: bool=True) -> str:
    # Optionally map common Persian variants to Arabic baseline
    mapping = {
        0x06CC: 0x064A,  # Farsi Yeh -> Arabic Yeh
        0x06A9: 0x0643,  # Keheh -> Kaf
        0x06C1: 0x0647,  # Heh doachashmee -> Heh
    }
    out = []
    for ch in s:
        cp = ord(ch)
        if strip_zero_widths and cp in ZERO_WIDTHS:
            continue
        if strip_bidi and cp in BIDI_CONTROLS:
            continue
        if map_persian_to_arabic and cp in mapping:
            out.append(chr(mapping[cp]))
        else:
            out.append(ch)
    # Normalize to NFKC to collapse compatibility forms
    cleaned = ud.normalize("NFKC", "".join(out))
    return cleaned

def cli():
    import argparse
    p = argparse.ArgumentParser(description="Scan strings for Unicode shadow attacks (invisible chars, bidi overrides, homoglyphs, mixed scripts).")
    p.add_argument("text", nargs="?", help="Text to scan. If omitted, read from stdin.")
    p.add_argument("--json", action="store_true", help="Print full JSON report.")
    p.add_argument("--sanitize", action="store_true", help="Output sanitized form (maps Persian->Arabic, strips zero-width & bidi).")
    args = p.parse_args()

    if args.text is None:
        data = sys.stdin.read()
    else:
        data = args.text

    report = analyze(data)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        flags = report["flags"]
        print("Length:", report["length"])
        print("Mixed scripts:", flags["mixed_scripts"], report["scripts"])
        print("Zero-width present:", flags["has_zero_width"], "positions:", report["indices"]["zero_width_positions"])
        print("Bidi controls present:", flags["has_bidi_controls"], "positions:", report["indices"]["bidi_positions"])
        print("Other controls present:", flags["has_other_controls"], "positions:", report["indices"]["control_positions"])
        print("Nonspacing marks:", flags["has_nonspacing_marks"], "positions:", report["indices"]["nonspacing_mark_positions"])
        if report["homoglyph_collisions"]:
            print("Homoglyph collisions:")
            for a,b,desc in report["homoglyph_collisions"]:
                print(f"  {a} with {b} -> {desc}")
        print("Codepoints:", " ".join(report["codepoints"]))

    if args.sanitize:
        cleaned = sanitize(data)
        print("\n--- Sanitized ---")
        print(cleaned)

if __name__ == "__main__":
    cli()
