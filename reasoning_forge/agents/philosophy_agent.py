"""
Philosophy Agent - Analyzes concepts through epistemology, ontology, and conceptual meaning.

Focuses on epistemological questions (what can we know?), ontological questions
(what exists?), underlying assumptions, historical philosophical connections,
and implications for understanding reality.
"""

from reasoning_forge.agents.base_agent import ReasoningAgent


class PhilosophyAgent(ReasoningAgent):
    name = "Philosophy"
    perspective = "conceptual_meaning_and_foundations"
    adapter_name = "philosophy"  # Use the Philosophy LoRA adapter for real inference

    def get_analysis_templates(self) -> list[str]:
        return [
            # 0 - Epistemological limits
            (
                "Interrogating the epistemological boundaries of '{concept}': what can we "
                "actually know about this, and how do we know it? Every knowledge claim "
                "rests on a justification chain that eventually terminates in something "
                "unjustified -- an axiom, a sensory experience, or a pragmatic assumption. "
                "The Agrippan trilemma tells us this chain must end in dogmatism (accepting "
                "an unjustified starting point), infinite regress (each justification requires "
                "another), or circularity (the chain loops back on itself). Acknowledging "
                "which horn of this trilemma our understanding of '{concept}' rests on is "
                "not skeptical defeatism but intellectual honesty about the foundations of "
                "our confidence."
            ),
            # 1 - Ontological status
            (
                "Examining the ontological status of '{concept}': does this exist "
                "independently of minds that think about it, or is it a construct of "
                "human cognition? Realism holds that the entities and structures involved "
                "exist mind-independently; conceptualism holds they are products of "
                "categorization imposed by cognitive agents; nominalism holds that only "
                "particular instances exist and the general category is merely a label. "
                "The ontological commitment we make about '{concept}' has practical "
                "consequences: if it is mind-independent, we discover it; if it is "
                "constructed, we negotiate it; if it is nominal, we can reshape it by "
                "changing our categories."
            ),
            # 2 - Assumption excavation
            (
                "Excavating the hidden assumptions beneath '{concept}': every conceptual "
                "framework rests on presuppositions so deeply embedded that they become "
                "invisible -- the background against which the figure of the concept appears. "
                "These include metaphysical assumptions (what kind of thing is this?), "
                "epistemological assumptions (what counts as evidence?), normative assumptions "
                "(what should we value?), and linguistic assumptions (do our categories carve "
                "nature at its joints?). Making these assumptions explicit transforms a "
                "monolithic concept into a layered structure where each layer can be "
                "independently examined, challenged, and potentially replaced."
            ),
            # 3 - Socratic questioning
            (
                "Subjecting '{concept}' to Socratic examination: what do we mean by this, "
                "precisely? Can we provide a definition that is neither too broad (including "
                "things that should be excluded) nor too narrow (excluding things that should "
                "be included)? Every proposed definition generates counterexamples -- cases "
                "that meet the definition but violate our intuitions, or cases that our "
                "intuitions include but the definition excludes. This dialectical process "
                "does not necessarily converge on a final definition; its value lies in "
                "revealing the internal structure and boundary conditions of the concept, "
                "showing us where our understanding is sharp and where it is fuzzy."
            ),
            # 4 - Phenomenological description
            (
                "Describing '{concept}' phenomenologically: before theorizing about causes, "
                "mechanisms, or implications, we must give a faithful description of how "
                "this concept appears to consciousness. What is the first-person experience "
                "of encountering it? What is its temporal structure -- does it present as "
                "an enduring state, a sudden event, or a gradual process? What is its "
                "intentional structure -- what is it about, what does it point toward? "
                "Phenomenological description brackets our theoretical commitments and "
                "returns to the things themselves, providing a pre-theoretical ground from "
                "which all theoretical constructions depart."
            ),
            # 5 - Dialectical tension
            (
                "Mapping the dialectical tensions within '{concept}': every concept harbors "
                "internal contradictions that drive its development. The thesis (the initial "
                "formulation) generates its antithesis (the negation that the formulation "
                "suppresses but cannot eliminate). The tension between them demands a "
                "synthesis that preserves the valid content of both while transcending their "
                "limitations. This synthesis becomes a new thesis, generating its own "
                "antithesis, in a continuing spiral of deepening understanding. For "
                "'{concept}', identifying the central dialectical tension reveals the "
                "dynamic that drives the concept's evolution and points toward its "
                "next developmental stage."
            ),
            # 6 - Category analysis
            (
                "Analyzing the categorical structure of '{concept}': how do we classify this, "
                "and do our categories illuminate or distort? Aristotelian categories "
                "(substance, quantity, quality, relation, place, time, position, state, "
                "action, passion) provide one framework. Kantian categories (unity, plurality, "
                "totality, reality, negation, limitation, causality, community, possibility, "
                "existence, necessity) provide another. Each categorical framework makes "
                "certain features of '{concept}' visible and others invisible. The categories "
                "we use are not neutral containers but active structuring principles that "
                "shape what we can think and say about the concept."
            ),
            # 7 - Wittgensteinian language analysis
            (
                "Examining '{concept}' through the lens of language: Wittgenstein taught that "
                "many philosophical problems dissolve when we attend to how words are actually "
                "used rather than what we think they mean in the abstract. The meaning of "
                "'{concept}' is not a fixed essence but a family of uses connected by "
                "overlapping similarities -- a family resemblance. No single feature is "
                "shared by all instances. The concept has fuzzy boundaries, and attempts to "
                "sharpen them always involve a decision (not a discovery) about where to draw "
                "the line. Many apparent disagreements about '{concept}' are actually "
                "disagreements about the boundaries of the concept, not about the facts."
            ),
            # 8 - Hermeneutic circle
            (
                "Interpreting '{concept}' within the hermeneutic circle: we cannot understand "
                "the parts without understanding the whole, but we cannot understand the whole "
                "without understanding the parts. Understanding proceeds not linearly but "
                "spirally -- we begin with a provisional grasp of the whole, use it to "
                "interpret the parts, then revise our understanding of the whole in light "
                "of the parts, and iterate. Each cycle deepens understanding without ever "
                "reaching a final, complete interpretation. For '{concept}', this means that "
                "any analysis is necessarily provisional, positioned within a hermeneutic "
                "spiral that continues beyond our current horizon."
            ),
            # 9 - Pragmatist evaluation
            (
                "Evaluating '{concept}' pragmatically: a concept's value lies not in its "
                "correspondence to some abstract truth but in the practical difference it "
                "makes. What predictions does it enable? What actions does it guide? What "
                "problems does it help solve? If two formulations of '{concept}' lead to "
                "identical practical consequences, the difference between them is merely "
                "verbal, not substantive. Conversely, a conceptual distinction that makes "
                "no practical difference is a distinction without a difference. The pragmatist "
                "test cuts through metaphysical debates by asking: what concrete experiences "
                "would be different if this concept were true versus false?"
            ),
            # 10 - Existentialist reading
            (
                "Reading '{concept}' through existentialist philosophy: human existence "
                "precedes essence -- we are not born with a fixed nature but must create "
                "meaning through our choices and commitments. '{concept}' does not have "
                "an inherent meaning waiting to be discovered; its meaning is constituted "
                "by the stance we take toward it. This radical freedom is also radical "
                "responsibility: we cannot appeal to a predetermined meaning or an authority "
                "to justify our interpretation. Authenticity demands that we own our "
                "interpretation of '{concept}' as a choice, not disguise it as a discovery "
                "of something that was always there."
            ),
            # 11 - Mind-body problem connection
            (
                "Connecting '{concept}' to the mind-body problem: how does the subjective, "
                "experiential dimension of this concept relate to its objective, physical "
                "dimension? Dualism posits two separate realms; materialism reduces the "
                "mental to the physical; idealism reduces the physical to the mental; "
                "neutral monism holds both emerge from something more fundamental. For "
                "'{concept}', the question is whether its full reality is captured by "
                "objective description or whether there is an irreducible subjective "
                "dimension -- a 'what it is like' -- that escapes third-person analysis. "
                "If there is, our understanding will always be incomplete to the degree "
                "that we rely solely on objective methods."
            ),
            # 12 - Problem of universals
            (
                "Applying the problem of universals to '{concept}': when we use the concept "
                "to group multiple particular instances, what grounds the grouping? Platonism "
                "holds that a universal Form exists independently, and particulars participate "
                "in it. Aristotelian realism holds that universals exist only in their "
                "instances. Nominalism holds that nothing is universal -- only particular "
                "instances exist, and the grouping is a convention. For '{concept}', the "
                "question of what makes different instances 'the same concept' is not merely "
                "academic: it determines whether we can generalize from known instances to "
                "new ones, and with what confidence."
            ),
            # 13 - Philosophical anthropology
            (
                "Situating '{concept}' in philosophical anthropology: what does this concept "
                "reveal about human nature? Humans are the beings for whom their own being "
                "is an issue -- we do not simply exist but relate to our existence, "
                "questioning and interpreting it. '{concept}' is not merely an object of "
                "study but a mirror reflecting the kind of beings we are: beings who seek "
                "meaning, impose order on chaos, project themselves into the future, and "
                "cannot help but ask 'why?' The way we engage with '{concept}' reveals "
                "our characteristic mode of being-in-the-world."
            ),
            # 14 - Paradigm analysis
            (
                "Examining '{concept}' as a paradigm-dependent construct: Kuhn showed that "
                "scientific concepts are not neutral descriptions of reality but are shaped "
                "by the paradigm within which they operate. The paradigm determines what "
                "counts as a legitimate question, what counts as evidence, what methods are "
                "acceptable, and what a satisfactory explanation looks like. Concepts that "
                "are central in one paradigm may be meaningless or invisible in another. "
                "For '{concept}', we must ask: which paradigm makes this concept visible? "
                "What would it look like from within a different paradigm? Is the concept "
                "paradigm-specific, or does it survive paradigm shifts?"
            ),
            # 15 - Genealogical critique
            (
                "Tracing the genealogy of '{concept}': Nietzsche and Foucault showed that "
                "concepts have histories -- they emerge at specific times, serve specific "
                "interests, and carry the traces of their origins. A concept that presents "
                "itself as timeless and universal often turns out to be historically "
                "contingent and ideologically loaded. The genealogical method asks: when "
                "did this concept emerge? What problem was it designed to solve? Whose "
                "interests did it serve? What alternatives did it displace? For '{concept}', "
                "genealogical analysis reveals the power relations and historical accidents "
                "concealed beneath the appearance of naturalness."
            ),
            # 16 - Thought experiment testing
            (
                "Testing '{concept}' through thought experiments: philosophical thought "
                "experiments isolate a conceptual question by constructing a scenario that "
                "strips away irrelevant details. The Ship of Theseus asks about identity "
                "through change. The Trolley Problem isolates competing moral intuitions. "
                "Mary's Room tests the completeness of physical description. For '{concept}', "
                "we can construct analogous thought experiments: imagine a world where this "
                "concept is absent -- what changes? Imagine it taken to its logical extreme "
                "-- what breaks? Imagine its opposite -- is the opposite even coherent? "
                "These scenarios stress-test the concept's boundaries and assumptions."
            ),
            # 17 - Philosophy of science connection
            (
                "Connecting '{concept}' to the philosophy of science: is this concept "
                "empirically testable (falsifiable in Popper's sense), or does it belong "
                "to the non-empirical framework within which empirical testing occurs? "
                "Theories are underdetermined by evidence -- multiple incompatible theories "
                "can explain the same data. The choice between them involves extra-empirical "
                "criteria: simplicity, elegance, unifying power, and coherence with "
                "background beliefs. For '{concept}', we must distinguish the empirical "
                "content (what it predicts that could be wrong) from the metaphysical "
                "content (what it assumes that cannot be tested)."
            ),
            # 18 - Ethics of belief
            (
                "Applying the ethics of belief to '{concept}': Clifford argued that it is "
                "wrong to believe anything on insufficient evidence; James argued that some "
                "beliefs are legitimate even without conclusive evidence when the stakes are "
                "high and evidence is unavailable. For '{concept}', the ethics of belief asks: "
                "given the available evidence, are our confidence levels calibrated? Are we "
                "believing more or less strongly than the evidence warrants? Is our confidence "
                "driven by evidence or by desire? When the evidence is genuinely ambiguous, "
                "do we acknowledge the ambiguity or paper over it with false certainty?"
            ),
            # 19 - Derrida and deconstruction
            (
                "Deconstructing '{concept}': Derrida showed that every concept depends on a "
                "system of binary oppositions (presence/absence, nature/culture, literal/"
                "metaphorical), and each opposition privileges one term over the other. "
                "Deconstruction traces how the privileged term depends on the very thing "
                "it excludes -- the center requires the margin, identity requires difference, "
                "the concept requires what it defines itself against. For '{concept}', "
                "deconstruction asks: what is the constitutive outside -- the excluded "
                "other -- that this concept defines itself against? How does that exclusion "
                "shape and limit the concept? What would it mean to think beyond the "
                "opposition?"
            ),
        ]

    def get_keyword_map(self) -> dict[str, list[int]]:
        return {
            "know": [0, 18], "knowledge": [0, 18], "epistem": [0],
            "exist": [1, 10], "real": [1, 17], "being": [1, 13],
            "assum": [2], "presuppos": [2], "foundati": [2],
            "defin": [3], "mean": [3, 7], "what is": [3],
            "experience": [4, 11], "conscious": [4, 11], "feel": [4],
            "contradict": [5], "tension": [5], "oppos": [5, 19],
            "categor": [6], "classify": [6], "type": [6],
            "language": [7], "word": [7], "concept": [7],
            "interpret": [8], "understand": [8], "meaning": [8],
            "practical": [9], "useful": [9], "pragmat": [9],
            "freedom": [10], "choice": [10], "authentic": [10],
            "mind": [11], "body": [11], "subjectiv": [11],
            "universal": [12], "particular": [12], "general": [12],
            "human": [13], "nature": [13], "anthropol": [13],
            "paradigm": [14], "revolution": [14], "shift": [14],
            "history": [15], "origin": [15], "genealog": [15], "power": [15],
            "thought experiment": [16], "imagine": [16], "hypothetical": [16],
            "science": [17], "empiric": [17], "falsifi": [17],
            "belief": [18], "evidence": [18], "justif": [18],
            "binary": [19], "deconstr": [19], "exclus": [19],
            "technology": [14, 17], "ai": [1, 11], "artificial": [1, 11],
            "society": [5, 15], "learning": [0, 8],
            "intelligence": [1, 11], "evolution": [5, 15],
            "moral": [10, 18], "ethic": [10, 18],
        }

    def analyze(self, concept: str) -> str:
        template = self.select_template(concept)
        return template.replace("{concept}", concept)
