#!/usr/bin/env python3
"""Measure whether a response actually landed — in the moment, not on a delay.

The optimizer's reward has never had an outcome term. `user_continued` was
always None, so every tuning decision rested on process proxies (coherence,
tension, latency) and none on whether the answer worked. This supplies the
missing term.

WHY THE OBVIOUS VERSION IS WORSE THAN NOTHING
---------------------------------------------
"The user sent another message, therefore they were engaged" rewards failure.
If an answer is wrong and has to be chased, that produces a follow-up. If an
answer is right and the user is satisfied, that produces silence. Naive
engagement scoring would teach the optimizer to prefer answers that need
chasing — an actively inverted signal, worse than the None it replaces.

So this classifier is built to DISCRIMINATE, and to abstain when it cannot:

    False  - evidence the answer did NOT land: the user re-asked the same
             thing, or corrected/rejected it.
    True   - evidence it DID land: the follow-up picks up content from the
             RESPONSE, not merely from the question. The user took something
             from the answer and moved forward with it.
    None   - genuinely unknown. Topic change, bare acknowledgement, session
             end. Absence of evidence is recorded as absence, never as False.

That last case matters. A session ending is not a negative result — the user
may have got exactly what they needed and left. Scoring silence as failure
would be the same class of error as scoring chasing as success.

ON TIMING ("not on the next turn — in the moment")
--------------------------------------------------
Engagement looks like it can only be known later, which is what the earlier
design assumed: buffer the turn, resolve it when the next one arrives. That is
unnecessary. The user's message is simultaneously the input to turn N and the
outcome measurement for turn N-1 — the same event, read from two frames. By the
time a query is in hand, the previous query and response are already in session
history, so the previous turn's outcome is fully determined at that instant.

Hence: a pure function of three strings, no pending state, no deferred writes,
nothing to flush or lose if a process dies mid-session.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

__all__ = [
    "classify_engagement", "EngagementResult", "push_off",
    "classify_from_history",
]

# Explicit rejection of the previous answer. Anchored at the start of the
# message or after a clause break, so "no" inside ordinary prose ("there is no
# reason to think that") does not trip it.
_CORRECTION = re.compile(
    r"(?:^|[.;!?]\s+)\s*(?:"
    r"no[,.\s]|nope\b|nah\b|wrong\b|that'?s not\b|thats not\b|not what i\b|"
    r"you (?:misunderstood|missed|didn'?t|did not|got it wrong)\b|"
    r"i didn'?t ask\b|that'?s wrong\b|incorrect\b|actually,?\s+(?:no|it)\b|"
    r"re-?read\b|try again\b|not quite\b|doesn'?t answer\b"
    r")", re.I)

# Pure acknowledgement with no new content — uninformative, not positive.
# Allows several stacked together ("ok thanks", "yep got it, cheers"), which is
# how people actually close a turn; a single-token pattern mislabelled those as
# topic changes. The verdict was already correct (None either way), but the
# recorded reason is what anyone auditing the log reads.
_ACK_WORD = (r"ok(?:ay)?|k|thanks|thank you|thanks!|ty|cheers|cool|nice|great|"
             r"got it|sure|perfect|lovely|yep|yes|yeah|right|awesome|"
             r"mm+|hm+|\U0001F44D")
_ACK_ONLY = re.compile(
    rf"^\s*(?:(?:{_ACK_WORD})[\s,.!]*)+$", re.I)

_STOPWORDS = frozenset("""
a an the and or but if then than that this these those is are was were be been
being do does did doing have has had having i you he she it we they me him her
us them my your his its our their of in on at to for with from by as about into
over after before between out up down off again further once here there all any
both each few more most other some such no nor not only own same so too very can
will just should now what which who whom whose when where why how
""".split())

_TOKEN = re.compile(r"[a-z0-9][a-z0-9'-]*")


def _content_tokens(text: str) -> set:
    """Lowercased content words, stopwords and one-character noise removed."""
    return {
        t for t in _TOKEN.findall((text or "").lower())
        if t not in _STOPWORDS and len(t) > 2
    }


def _overlap(a: set, b: set) -> float:
    """Jaccard overlap. 0.0 when either side is empty."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


class EngagementResult(tuple):
    """(value, reason). `value` is True / False / None — None means not measured."""

    __slots__ = ()

    def __new__(cls, value: Optional[bool], reason: str):
        return super().__new__(cls, (value, reason))

    @property
    def value(self) -> Optional[bool]:
        return self[0]

    @property
    def reason(self) -> str:
        return self[1]

    @property
    def measured(self) -> bool:
        return self[0] is not None


# Tuned to be conservative: it is better to abstain than to assert a
# measurement that is really a guess. See the tests for the boundary cases.
RE_ASK_THRESHOLD = 0.60      # query-to-query overlap that counts as a re-ask
UPTAKE_THRESHOLD = 0.10      # of the follow-up's NEW content, how much came
                             # from the response rather than the old question


def classify_engagement(
    prev_query: str,
    prev_response: str,
    next_query: str,
) -> EngagementResult:
    """Did the previous response land? Judged from the follow-up, in the moment.

    Order matters: negative evidence is checked before positive, because a
    correction often also contains uptake from the response it is correcting.
    """
    if not (prev_query or "").strip() or not (prev_response or "").strip():
        return EngagementResult(None, "no previous turn to judge")
    if not (next_query or "").strip():
        return EngagementResult(None, "session ended — silence is not a verdict")

    # 1. Explicit correction or rejection. Strongest negative evidence there is.
    if _CORRECTION.search(next_query):
        return EngagementResult(False, "follow-up corrects or rejects the answer")

    q_prev = _content_tokens(prev_query)
    q_next = _content_tokens(next_query)
    r_prev = _content_tokens(prev_response)

    # 2. Re-ask. The same question again means the answer did not land, whatever
    #    else was in it.
    if _overlap(q_prev, q_next) >= RE_ASK_THRESHOLD:
        return EngagementResult(False, "follow-up re-asks the same question")

    # 3. Bare acknowledgement. Polite, but carries no information about whether
    #    the content was any use.
    if _ACK_ONLY.match(next_query):
        return EngagementResult(None, "bare acknowledgement — uninformative")

    # 4. Uptake. Of the follow-up's content that is NOT just a restatement of
    #    the old question, how much came from the response? Subtracting the old
    #    question is the point: it separates "engaged with the answer" from
    #    "still circling the original topic".
    novel = q_next - q_prev
    if not novel:
        return EngagementResult(None, "follow-up adds no new content")

    from_response = novel & r_prev
    uptake = len(from_response) / len(novel)
    if uptake >= UPTAKE_THRESHOLD:
        return EngagementResult(
            True, f"follow-up builds on the answer (uptake {uptake:.2f})")

    # 5. New content, none of it from the response: a topic change. That says
    #    nothing about whether the previous answer was good.
    return EngagementResult(None, "topic change — no evidence either way")


def classify_from_history(messages, next_query: str) -> EngagementResult:
    """Convenience wrapper: pull the previous exchange out of session history.

    `messages` is the session's message list — dicts with 'role' and 'content'.
    Call this BEFORE appending the current turn, while the last entries are
    still the previous user query and the response to it. That ordering is the
    whole trick: at that instant the previous turn's outcome is already
    determined and nothing needs to be buffered or resolved later.

    Returns an abstaining result rather than raising if history is short or
    malformed — a measurement problem must never break a turn.
    """
    try:
        prev_query = prev_response = ""
        # Walk backwards for the most recent assistant reply and the user
        # message that prompted it.
        for i in range(len(messages) - 1, -1, -1):
            m = messages[i]
            if not prev_response and m.get("role") == "assistant":
                prev_response = m.get("content") or ""
                for j in range(i - 1, -1, -1):
                    if messages[j].get("role") == "user":
                        prev_query = messages[j].get("content") or ""
                        break
                break
        return classify_engagement(prev_query, prev_response, next_query)
    except Exception as e:  # never let measurement break a turn
        return EngagementResult(None, f"engagement not measured ({e})")


def push_off(result: EngagementResult, prev_adapter: str = "") -> dict:
    """Turn the measurement at the wall into momentum for the CURRENT turn.

    The swimmer's flip: arriving at the wall is not the end of the length, it
    is where the direction reverses and the push comes from. The user's message
    is that wall. Reading it only backwards — scoring the turn that just ended
    — throws away the half of the information that points forwards.

    The same classification that resolves the previous turn's reward is
    available *before* the current turn is routed, and it is the most direct
    evidence there is about what to do next:

        the answer did not land   -> do not push off in the same direction.
                                     Steer away from the adapter that just
                                     failed and widen the perspective set.
        the answer landed         -> push off the way you came in. Continuity
                                     is working; keep the approach.
        not measured              -> no push. Absence of evidence must not
                                     become a steer, for the same reason it
                                     must not become a reward.

    Returns a hint dict, deliberately advisory. It carries no authority of its
    own — the router decides whether to honour it, and in shadow mode nothing
    consumes it at all. That keeps this reversible and observable first, which
    is the same discipline the optimizer itself is held to.
    """
    value = result.value
    if value is False:
        return {
            "steer": "diverge",
            "reason": result.reason,
            "avoid_adapter": prev_adapter or None,
            # A failed answer is evidence the single-perspective read was
            # wrong, not that it needed more of the same.
            "widen_perspectives": True,
            "confidence": 0.6 if "corrects" in result.reason else 0.4,
        }
    if value is True:
        return {
            "steer": "continue",
            "reason": result.reason,
            "prefer_adapter": prev_adapter or None,
            "widen_perspectives": False,
            "confidence": 0.4,
        }
    return {
        "steer": "none",
        "reason": result.reason,
        "widen_perspectives": False,
        "confidence": 0.0,
    }
