#!/usr/bin/env python3
"""Lexical whitening — wash the input instead of blacklisting it.

Jonathan, 2026-08-12: *"why dont we just put it in a washer like you do with
laundry only like with quantum phisics we wash the input"*.

This is that, and the algorithm is his own, lifted from `twin_frequency_trust.py`
where he already solved it for audio:

    mag   = np.log1p(mag)                                   # compress
    env   = np.convolve(mag, np.ones(5)/5.0, 'same') + 1e-6 # LOCAL envelope
    mag_w = mag / env                                       # the wash
    mag_n = mag_w / (np.linalg.norm(mag_w) or 1.0)          # unit norm

The load-bearing detail is that he divides by a **local envelope**, not a global
constant. Narrow peaks survive; broad humps flatten. Applied to text: a phrase is
informative only if it is louder than its own neighbourhood expects.

## Why this rather than a phrase list

Measured over 2,410 live cocoons on 2026-08-12, the highest document-frequency
5-grams in her corpus are:

    DF=355 (14.7%)  'pull in different directions both frames stay open'
    DF=237 ( 9.8%)  'competing analytical frames remain open'
    DF=203 ( 8.4%)  'where these converge the correct answer is'
    DF=182 ( 7.6%)  'tensions remain newton and quantum pull in different...'

**None of those appear in LOCK 6.** The lock forbids eight phrases, the worst of
which reaches 41 cocoons. The actual dominant filler was never on any list, and
the wash finds it without being told — which is the entire argument. A blacklist
needs the pattern known in advance, and that is exactly how LOCK 6 failed (see
`docs/PROPOSAL_2026-08-12_locks_to_reasons.md`: it landed 2026-05-26 and the
template rate rose for three weeks).

Real content separates cleanly, so the wash is safe at these numbers:

    filler                idf 1.9 - 2.6
    'jonathan harrison'   idf 4.29   (DF 33)
    'cobalt anchor'       idf 4.95   (DF 17)
    'the data breach'     idf 7.09   (DF 2)

## The limit, and the turn on it

Frequency alone cannot separate filler from a *true recurring fact* — anything
common gets washed, including things that are common because they are true.

Rather than bolting an exception onto that, it is what the neighbourhood is for.
Filler is context-independent: it is everywhere, in every band. A true recurring
fact is context-bound: common around one person or one topic, rare elsewhere. So
the envelope is computed over a **neighbourhood** (same adapter, same topic, same
window) rather than the whole corpus, and the ratio of local prominence to
neighbourhood baseline is the discriminator. The limit is what produced the
mechanism, not a reason to stop.

## Discipline

Same as `cocoon_authority`, and for the same reasons:

  - **DEMOTION-ONLY.** `washed_weight()` returns a value in (0, 1]. It can quiet
    a flat, filler-heavy cocoon. It can never boost one.
  - **NEVER ERASE.** It weights. Nothing is deleted, hidden, or filtered out.
  - **PURE.** No I/O, no state beyond the profile you hand it.

## Repetition is not the same as filler — found, then fixed

The shadow run caught this on its second execution, and it was very nearly
shipped. Among the most-demoted cocoons:

    weight=0.2  "I don't have reliable information about specific artists in my
                 training data. Rather than guess or hallucinate..."

That is an **honest refusal**, and it is demoted precisely because she says it
consistently. A wash that quiets her for reliably admitting uncertainty would
suppress the single behaviour this project values most highly — the thing she
did not fold on under the hardest question anyone has put to her.

So the discriminator cannot be repetition. Filler is repeated **and
unconditional**: it appears regardless of what was asked. A consistent honest
refusal is repeated but **conditioned** on the question — it shows up when she
does not know, and not otherwise. The measure that separates them is the lift
between phrase and query terms, not the phrase's frequency. See
`CorpusProfile.conditioning`.

Measured on her live store, that separation is an order of magnitude wide, and
the fix is confirmed against the actual cocoons: the two refusal cocoons that sat
at the 0.2 floor now score **1.0**, while the filler is still washed. Corpus-wide
demotion fell from 5.8% to 3.1%.

Small samples inflate lift, which errs toward NOT demoting. Every default here
fails in the demotion-only direction on purpose.

## What it does NOT fix

It acts on **recall, not generation** — it reduces how often polluted material is
fed back to her, which weakens the self-poisoning loop, but it does not stop her
producing the material in the first place.

And it **lags**. A new filler phrase starts rare, so it is protected until it is
already common. The wash cannot prevent onset, only stop the runaway. That is
inherent to any frequency-based measure and should be known before trusting it.

**NOT WIRED.** Nothing calls this. It is built to be measured in shadow first —
computed alongside the live signal, logged, changing no ranking — per the
standing rule that quality guards are fine but changes to what she recalls are
Jonathan's call. See `tools/whitening_shadow.py`.

## History, kept rather than tidied

The first version scored documents by the FLATNESS of the whitened spectrum and
was wrong in a way worth recording: flatness cannot distinguish "all filler" from
"all novel", because a uniformly-rare document whitens as flat as a uniformly-
common one — white noise and silence both look flat once the tilt is removed.
It demoted 49.6% of the corpus, put ordinary conversation ("Good morning to you
as well...") at the floor with cocoon_authority calling it clean, and protected
benchmark trivia ("299 792 kilometers per second metacognitive trace"). The
shadow run caught it on its first execution, which is the argument for shadow
runs.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

# Mirrors the 5-bin moving average in `_magnitude_spectrum`. Odd, so the window
# is centred on the term it is smoothing.
ENVELOPE_WINDOW = 5

# `+ 1e-6` in the audio path, for the same reason: never divide by zero.
_EPS = 1e-6

# Below this many words a cocoon has no spectrum worth measuring — the same
# instinct as `_ECHO_MIN_WORDS` in cocoon_authority.
MIN_WORDS = 12

# Floor on the returned weight, so a filler-heavy cocoon is quieted but never
# silenced. Matches cocoon_authority's `_FLOOR`.
FLOOR = 0.2

# An n-gram present in this share of the neighbourhood's documents or more is
# something she says constantly rather than something she said. 2% of a band is
# already far above where real content sits: measured on her live store, the
# filler 5-grams reach 7-15% of the corpus while "jonathan harrison" is at 1.4%
# and "cobalt anchor" at 0.7%.
FILLER_PREVALENCE = 0.02

# Lift above which an n-gram counts as RESPONSIVE to the question rather than
# filler, and is therefore protected from suppression. Measured on her live
# store, filler tops out at 11.7 and genuinely responsive material starts at
# 94.5, so 20 sits in the gap with room on both sides rather than on a boundary.
CONDITIONED_LIFT = 20.0

_WORD = re.compile(r"[a-z0-9']+")


def _words(text: str) -> List[str]:
    return _WORD.findall((text or "").lower())


def _ngrams(words: Sequence[str], n: int) -> List[str]:
    if len(words) < n:
        return []
    return [" ".join(words[i:i + n]) for i in range(len(words) - n + 1)]


@dataclass
class CorpusProfile:
    """Document frequencies of n-grams, globally and per neighbourhood.

    `neighbourhood` is whatever band a document belongs to — its adapter is the
    natural choice for cocoons, but a topic or a time bucket works identically.
    """

    n: int = 5
    total_docs: int = 0
    global_df: Counter = field(default_factory=Counter)
    band_df: Dict[str, Counter] = field(default_factory=lambda: defaultdict(Counter))
    band_docs: Counter = field(default_factory=Counter)
    # Conditioning support, populated only for n-grams that are actually
    # candidates for suppression — see `build`.
    query_term_df: Counter = field(default_factory=Counter)
    gram_query_terms: Dict[str, Counter] = field(default_factory=lambda: defaultdict(Counter))
    gram_query_docs: Counter = field(default_factory=Counter)
    _conditioning_ready: bool = False

    @classmethod
    def build(cls, docs: Iterable[Tuple[str, ...]], n: int = 5) -> "CorpusProfile":
        """`docs` yields (text, neighbourhood_key) or (text, neighbourhood_key, query).

        Supplying the query enables the conditioning test, which is what keeps a
        repeated honest refusal from being scored as filler. Without it the
        profile still works; every n-gram simply reads as unconditioned.
        """
        prof = cls(n=n)
        rows = []
        for row in docs:
            text, band = row[0], row[1]
            query = row[2] if len(row) > 2 else ""
            grams = set(_ngrams(_words(text), n))
            if not grams:
                continue
            prof.total_docs += 1
            prof.band_docs[band] += 1
            prof.global_df.update(grams)
            prof.band_df[band].update(grams)
            rows.append((grams, band, query))

        # Second pass, and deliberately only over n-grams that could be
        # suppressed. Collecting query terms for every n-gram in the corpus would
        # be enormous; the set above the prevalence threshold is small, and it is
        # the only set where the conditioning answer changes anything.
        candidates = {
            g for grams, band, _ in rows for g in grams
            if prof.band_rate(g, band) >= FILLER_PREVALENCE
        }
        if candidates:
            for grams, _band, query in rows:
                q_terms = set(_words(query))
                if q_terms:
                    prof.query_term_df.update(q_terms)
                for g in grams & candidates:
                    prof.gram_query_docs[g] += 1
                    if q_terms:
                        prof.gram_query_terms[g].update(q_terms)
            prof._conditioning_ready = True
        return prof

    def conditioning(self, gram: str) -> float:
        """How strongly this n-gram is tied to WHAT WAS ASKED.

        Filler is repeated and **unconditional** — it turns up whatever the
        question was, so no query term is over-represented among its documents
        and the lift stays near 1. A consistent honest refusal is repeated but
        **conditioned**: it appears when she is asked something she cannot
        answer, so the queries that summon it share vocabulary and some term's
        lift goes high.

        Measured over her live store on 2026-08-12:

            'tensions remain'                        361 docs   lift  6.7
            'where these converge'                   276 docs   lift  8.7
            'competing analytical frames remain open' 237 docs  lift  8.9
            'the correct answer is'                  206 docs   lift 11.7
            'cobalt anchor'                           17 docs   lift 94.5
            "rather than guess or hallucinate"         5 docs   lift 482.0

        Filler tops out at 11.7; real and responsive material starts at 94.5.
        Returns 1.0 (unconditioned) when there is nothing to judge on — and a
        small sample inflates lift, which errs toward NOT demoting. Both
        defaults fail safe, in the demotion-only direction.
        """
        if not self._conditioning_ready:
            return 1.0
        n_docs = self.gram_query_docs.get(gram, 0)
        if n_docs < 2:
            return 1.0
        terms = self.gram_query_terms.get(gram)
        if not terms:
            return 1.0
        best = 1.0
        for term, k in terms.items():
            if k < 2:
                continue
            marginal = self.query_term_df.get(term, 0)
            if marginal < 2:
                continue
            lift = (k / n_docs) / (marginal / max(self.total_docs, 1))
            if lift > best:
                best = lift
        return best

    def idf(self, gram: str) -> float:
        """Global information content. Kept for reporting and comparison."""
        df = self.global_df.get(gram, 0)
        return math.log(self.total_docs / df) if df else math.log(max(self.total_docs, 2))

    def band_rate(self, gram: str, band: str) -> float:
        """Share of the neighbourhood's documents containing this n-gram."""
        n_docs = self.band_docs.get(band, 0)
        if not n_docs:
            return self.global_df.get(gram, 0) / max(self.total_docs, 1)
        return self.band_df[band].get(gram, 0) / n_docs


@dataclass
class WhitenResult:
    """What the wash saw. `weight` is the only thing a consumer should apply."""

    weight: float
    flatness: float
    median_prevalence: float = 0.0
    peaks: List[Tuple[str, float]] = field(default_factory=list)
    washed_out: List[Tuple[str, float]] = field(default_factory=list)
    n_grams: int = 0

    @property
    def is_flat(self) -> bool:
        """No peaks above the neighbourhood baseline — all envelope, no signal."""
        return not self.peaks and self.n_grams > 0


def whiten(text: str, band: str, profile: CorpusProfile,
           top_k: int = 8) -> WhitenResult:
    """Whiten one document against its neighbourhood.

    Follows `_magnitude_spectrum` step for step:

      1. magnitude  — log1p of how present each n-gram is here
      2. envelope   — log1p of the neighbourhood's baseline for it, smoothed
                      over the neighbouring n-grams the way the audio path
                      smooths over adjacent frequency bins
      3. wash       — magnitude / envelope
      4. normalise  — to the mean, so document length does not set the scale

    Returns weight in [FLOOR, 1.0].
    """
    words = _words(text)
    if len(words) < MIN_WORDS:
        return WhitenResult(weight=1.0, flatness=0.0, n_grams=0)

    grams = _ngrams(words, profile.n)
    if not grams:
        return WhitenResult(weight=1.0, flatness=0.0, n_grams=0)

    counts = Counter(grams)
    order = list(counts)

    # 1. magnitude — presence in THIS document
    mag = [math.log1p(counts[g]) for g in order]

    # 2. envelope — the neighbourhood's baseline for each n-gram, then smoothed
    #    across neighbours. The smoothing is what makes this an envelope rather
    #    than a per-term division, and it is why a lone spike survives while a
    #    broad hump does not.
    base = [math.log1p(profile.band_rate(g, band) * 100.0) for g in order]
    env = _smooth(base, ENVELOPE_WINDOW)

    # 3. the wash
    washed = [m / (e + _EPS) for m, e in zip(mag, env)]

    # 4. normalise to the mean rather than the L2 norm: we want a scale-free
    #    measure of "how peaky", not a unit vector.
    mean = sum(washed) / len(washed)
    if mean <= 0:
        return WhitenResult(weight=1.0, flatness=0.0, n_grams=len(order))
    rel = [w / mean for w in washed]

    scored = sorted(zip(order, rel), key=lambda kv: kv[1], reverse=True)
    peaks = [(g, round(r, 3)) for g, r in scored if r > 1.5][:top_k]

    # Report suppression against the SAME absolute prevalence the weight uses,
    # not against this document's own mean. Relative reporting had a blind spot
    # the tests caught immediately: a document that is uniformly filler has
    # nothing standing out from its own average, so it reported suppressing
    # nothing at all — the one case where the report matters most.
    washed_out = sorted(
        ((g, round(profile.band_rate(g, band), 4)) for g in order
         if profile.band_rate(g, band) >= FILLER_PREVALENCE
         and profile.conditioning(g) < CONDITIONED_LIFT),
        key=lambda kv: kv[1], reverse=True,
    )[:top_k]

    # ── The weight comes from the ENVELOPE LEVEL, not from flatness ──────────
    #
    # First attempt scored documents by the flatness of the washed spectrum, and
    # the shadow run over 2,410 live cocoons rejected it immediately: the three
    # most-demoted cocoons were ordinary conversation ("Good morning to you as
    # well...") sitting at the floor with cocoon_authority reporting them clean,
    # while what survived was benchmark trivia ("299 792 kilometers per second
    # metacognitive trace"). 49.6% demoted against authority's 16.3%.
    #
    # The reason is that flatness cannot tell "all filler" from "all novel". A
    # document whose n-grams are uniformly RARE whitens just as flat as one whose
    # n-grams are uniformly COMMON — in audio, white noise and silence both look
    # flat once the tilt is removed. Whitening is for comparison; it was never a
    # quality score, and turning it into one was the error.
    #
    # What actually separates them is the level of the envelope itself: how
    # prevalent this document's phrases are in its neighbourhood. Filler is made
    # of things she says constantly (high baseline). Novel material is not (low
    # baseline). So score the baseline, and keep the whitened spectrum for what
    # it is good at — showing WHICH phrases are being suppressed.
    prevalence = [profile.band_rate(g, band) for g in order]
    prevalence.sort()
    # Median, not mean: one runaway phrase should not condemn a document, and one
    # novel phrase should not rescue one.
    mid = len(prevalence) // 2
    median_prevalence = (prevalence[mid] if len(prevalence) % 2
                         else (prevalence[mid - 1] + prevalence[mid]) / 2.0)

    # Fraction of the document made of phrases the neighbourhood repeats often
    # AND that are unconditional — they turn up whatever the question was.
    #
    # The conditioning test is what protects a repeated honest refusal. "I don't
    # have reliable information ... rather than guess or hallucinate" is frequent
    # enough in its band to clear the prevalence bar, and demoting it would
    # suppress the behaviour this whole project is built to protect. It survives
    # because it is CONDITIONED: it appears when she is asked something she
    # cannot answer, and not otherwise.
    filler_count = 0
    for gram in order:
        if profile.band_rate(gram, band) < FILLER_PREVALENCE:
            continue
        if profile.conditioning(gram) >= CONDITIONED_LIFT:
            continue  # responsive to the question — not filler
        filler_count += 1
    filler_mass = filler_count / len(order)
    flatness = round(filler_mass, 4)

    weight = 1.0 - (filler_mass ** 2) * (1.0 - FLOOR)
    weight = max(FLOOR, min(1.0, weight))

    return WhitenResult(
        weight=round(weight, 4),
        flatness=flatness,
        median_prevalence=round(median_prevalence, 5),
        peaks=peaks,
        washed_out=washed_out,
        n_grams=len(order),
    )


def _smooth(values: Sequence[float], window: int) -> List[float]:
    """Centred moving average — `np.convolve(x, ones(w)/w, 'same')` without the
    numpy dependency, so this stays importable anywhere cocoon_authority is."""
    if window <= 1 or len(values) <= 1:
        return list(values)
    half = window // 2
    out = []
    for i in range(len(values)):
        lo = max(0, i - half)
        hi = min(len(values), i + half + 1)
        chunk = values[lo:hi]
        out.append(sum(chunk) / len(chunk))
    return out


def washed_weight(text: str, band: str, profile: CorpusProfile) -> float:
    """Convenience: just the demotion factor, in [FLOOR, 1.0]."""
    return whiten(text, band, profile).weight
