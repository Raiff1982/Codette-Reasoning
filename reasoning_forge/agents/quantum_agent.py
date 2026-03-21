"""
Quantum Agent - Analyzes concepts through probabilistic and uncertainty reasoning.

Focuses on superposition of possibilities, measurement effects, probabilistic
vs deterministic outcomes, entanglement and correlations, and wave-particle
duality analogies.
"""

from reasoning_forge.agents.base_agent import ReasoningAgent


class QuantumAgent(ReasoningAgent):
    name = "Quantum"
    perspective = "probabilistic_and_uncertainty"
    adapter_name = "quantum"  # Use the Quantum LoRA adapter for real inference

    def get_analysis_templates(self) -> list[str]:
        return [
            # 0 - Superposition of possibilities
            (
                "Before we commit to a single interpretation, '{concept}' exists in a "
                "superposition of multiple valid framings simultaneously. Each framing "
                "carries a probability amplitude -- not a classical probability, but a "
                "complex weight that can interfere constructively or destructively with "
                "others. Some framings reinforce each other, producing high-probability "
                "interpretations; others cancel out, revealing that certain seemingly "
                "plausible readings are actually suppressed by internal contradictions. "
                "The richest understanding comes from maintaining this superposition as "
                "long as possible, resisting the temptation to collapse prematurely into "
                "a single narrative."
            ),
            # 1 - Measurement disturbance
            (
                "The act of examining '{concept}' necessarily disturbs it. Any attempt to "
                "pin down one aspect with high precision introduces uncertainty into "
                "complementary aspects. If we measure the current state with perfect "
                "accuracy, we lose information about the trajectory of change. If we "
                "track the dynamics precisely, the instantaneous state becomes blurred. "
                "This is not a failure of our instruments -- it is a fundamental feature "
                "of systems where the observer and observed are entangled. The experimental "
                "design (which questions we choose to ask) shapes the answers we can obtain, "
                "making the framing of inquiry as important as the inquiry itself."
            ),
            # 2 - Complementarity
            (
                "'{concept}' exhibits complementarity: it has pairs of properties that "
                "cannot be simultaneously specified with arbitrary precision. Like position "
                "and momentum in quantum mechanics, knowing one aspect exhaustively means "
                "accepting irreducible uncertainty in its complement. The wave-like view "
                "emphasizes distributed patterns, interference, and coherence across the "
                "whole system. The particle-like view emphasizes localized events, discrete "
                "outcomes, and individual instances. Neither view alone is complete; both "
                "are needed, and the apparent contradiction between them is not a defect "
                "but the deepest feature of the subject."
            ),
            # 3 - Probability amplitudes and interference
            (
                "Analyzing the probability landscape of '{concept}': outcomes are not "
                "determined by summing classical probabilities but by summing amplitudes "
                "that can interfere. Two pathways to the same outcome may cancel each other "
                "(destructive interference), making a seemingly likely result improbable. "
                "Alternatively, they may reinforce (constructive interference), making an "
                "unlikely outcome surprisingly common. This means we cannot reason about "
                "'{concept}' by considering each factor in isolation and adding up their "
                "effects -- the cross-terms between factors, the interference pattern, "
                "carries critical information that purely additive thinking misses."
            ),
            # 4 - Entanglement and correlation
            (
                "Multiple elements of '{concept}' are entangled: measuring or changing one "
                "instantaneously constrains what we can know about the others, regardless "
                "of the apparent separation between them. These correlations are stronger "
                "than any classical explanation permits -- they cannot be reproduced by "
                "assuming each element has pre-existing definite properties. This means "
                "'{concept}' is not decomposable into fully independent parts. The "
                "correlations between components carry information that is not contained "
                "in any component individually. Analyzing the parts in isolation and then "
                "trying to reconstruct the whole will systematically miss these non-local "
                "correlations."
            ),
            # 5 - Collapse and decision
            (
                "At some point, the superposition of possibilities around '{concept}' must "
                "collapse into a definite outcome. This collapse -- the moment of decision, "
                "measurement, or commitment -- is irreversible. Before collapse, all "
                "possibilities coexist and influence each other through interference. After "
                "collapse, one outcome is realized and the others vanish. The timing of "
                "this collapse matters enormously: collapsing too early (deciding prematurely) "
                "forecloses options that might have interfered constructively. Collapsing "
                "too late risks decoherence, where the environment randomizes the phases "
                "and destroys the delicate interference patterns that could have guided "
                "a better outcome."
            ),
            # 6 - Tunneling through barriers
            (
                "Within '{concept}', there may be barriers that appear insurmountable "
                "under classical analysis -- energy gaps too wide, transitions too "
                "improbable. But quantum tunneling demonstrates that a nonzero probability "
                "exists for traversing barriers that classical reasoning says are impassable. "
                "The tunneling probability depends exponentially on the barrier width and "
                "height: thin barriers are penetrable, thick ones are not. For '{concept}', "
                "this suggests asking: are the perceived obstacles genuinely thick barriers, "
                "or are they thin barriers that appear impenetrable only because we are "
                "applying classical (deterministic) reasoning to an inherently probabilistic "
                "situation?"
            ),
            # 7 - Decoherence and information leakage
            (
                "The coherence of '{concept}' -- the ability of its different aspects to "
                "interfere constructively -- is fragile. Interaction with a noisy environment "
                "causes decoherence: the quantum-like superposition of possibilities decays "
                "into a classical mixture where different outcomes no longer interfere. "
                "Each interaction with the environment leaks information about the system's "
                "state, effectively performing a partial measurement. The decoherence time "
                "sets the window within which coherent reasoning about '{concept}' remains "
                "valid. Beyond that window, the interference effects have washed out and "
                "we are left with classical probabilistic reasoning -- still useful, but "
                "less powerful."
            ),
            # 8 - No-cloning and uniqueness
            (
                "The no-cloning theorem states that an unknown quantum state cannot be "
                "perfectly copied. Applied to '{concept}': if the concept embodies a unique "
                "configuration of entangled properties, it cannot be perfectly replicated "
                "by decomposing it into parts and reassembling them. Any attempt to copy "
                "it disturbs the original. This has profound implications: unique instances "
                "of '{concept}' are genuinely irreplaceable, not merely practically "
                "difficult to reproduce. Strategies that depend on exact replication must "
                "be replaced by strategies that work with approximate copies and manage "
                "the fidelity loss."
            ),
            # 9 - Uncertainty principle application
            (
                "Heisenberg's uncertainty principle, generalized beyond physics, suggests "
                "that '{concept}' has conjugate properties that trade off precision. "
                "Specifying the concept's scope with extreme precision makes its future "
                "trajectory unpredictable. Specifying the direction of change precisely "
                "blurs the current boundaries. The product of these uncertainties has a "
                "minimum value -- we cannot reduce both below a threshold. Practical "
                "wisdom lies in choosing which uncertainty to minimize based on what "
                "decisions we need to make, accepting that the conjugate uncertainty "
                "will necessarily increase."
            ),
            # 10 - Quantum Zeno effect
            (
                "Frequent observation of '{concept}' can freeze its evolution -- the "
                "quantum Zeno effect. Continuously monitoring whether the system has "
                "changed forces it to remain in its initial state, because each "
                "observation collapses the evolving superposition back to the starting "
                "point before significant transition amplitude accumulates. Paradoxically, "
                "the most watched aspects of '{concept}' may be the least likely to "
                "change. Allowing unmonitored evolution -- stepping back and not measuring "
                "for a while -- may be necessary for genuine transformation to occur."
            ),
            # 11 - Eigenstate decomposition
            (
                "Decomposing '{concept}' into its eigenstates -- the stable, self-consistent "
                "configurations that persist under the relevant operator -- reveals the "
                "natural modes of the system. Each eigenstate has a definite value for "
                "the quantity being measured; a general state is a superposition of these "
                "eigenstates. The eigenvalue spectrum (the set of possible measurement "
                "outcomes) may be discrete, continuous, or mixed. Discrete spectra imply "
                "quantized behavior: only certain values are possible, and the system "
                "jumps between them. Identifying the eigenstates of '{concept}' tells us "
                "what the stable configurations are and what transitions between them look like."
            ),
            # 12 - Path integral perspective
            (
                "From the path integral perspective, '{concept}' does not follow a single "
                "trajectory from start to finish. Instead, every conceivable path contributes "
                "to the final outcome, each weighted by a phase factor. Most paths cancel "
                "each other out through destructive interference, leaving only a narrow "
                "bundle of 'classical' paths that dominate the sum. But near decision points, "
                "barriers, or transitions, the non-classical paths contribute significantly, "
                "and the outcome depends on the full ensemble of possibilities. This perspective "
                "counsels against fixating on the most likely path and instead attending to "
                "the full distribution of paths that contribute to the result."
            ),
            # 13 - Entanglement entropy and information
            (
                "The entanglement entropy of '{concept}' measures how much information about "
                "one part of the system is encoded in its correlations with other parts rather "
                "than in the part itself. High entanglement entropy means the subsystem appears "
                "maximally disordered when examined alone, even though the joint system may be "
                "in a pure, fully determined state. This is a profound observation: local "
                "ignorance can coexist with global certainty. For '{concept}', apparent "
                "randomness or confusion at one level may dissolve into perfect order when "
                "we expand our view to include the correlated components."
            ),
            # 14 - Basis dependence and frame choice
            (
                "Our analysis of '{concept}' depends critically on the basis we choose -- "
                "the set of fundamental categories into which we decompose the concept. "
                "A different basis (a different set of fundamental categories) can make a "
                "confused-looking problem transparent, or a simple-looking problem intractable. "
                "There is no uniquely 'correct' basis; the optimal choice depends on which "
                "question we are asking. The interference terms that appear in one basis "
                "become diagonal (simple) in another. Finding the basis that diagonalizes "
                "the problem -- the natural language in which '{concept}' expresses itself "
                "most simply -- is often the breakthrough that transforms understanding."
            ),
            # 15 - Coherent vs incoherent mixtures
            (
                "A critical distinction for '{concept}': is the coexistence of multiple "
                "interpretations a coherent superposition (where they interfere and interact) "
                "or an incoherent mixture (where they merely coexist without interaction, "
                "like balls in an urn)? A coherent superposition produces interference "
                "effects -- outcomes that no single interpretation predicts. An incoherent "
                "mixture produces only the probabilistic average of individual interpretations. "
                "The practical difference is enormous: coherent combinations can exhibit "
                "effects (constructive peaks, destructive nulls) that are impossible in "
                "any classical mixture."
            ),
            # 16 - Quantum error and robustness
            (
                "How robust is '{concept}' against errors and noise? Quantum error correction "
                "teaches that information can be protected by encoding it redundantly across "
                "entangled components. No single component carries the full information, so "
                "no single error can destroy it. For '{concept}', the analogous question is: "
                "how is the essential meaning distributed across its components? If it is "
                "concentrated in a single fragile element, one disruption destroys it. If "
                "it is encoded holographically across many entangled elements, it is "
                "remarkably robust against local damage."
            ),
            # 17 - Born rule and outcome probabilities
            (
                "The Born rule assigns probabilities to outcomes as the squared magnitude "
                "of the amplitude. Applied to '{concept}': the probability of a particular "
                "interpretation prevailing is not the amplitude of support for it but the "
                "amplitude squared -- a nonlinear transformation. Small differences in "
                "amplitude translate to large differences in probability. A framing with "
                "twice the amplitude is four times as likely to be realized. This squared "
                "relationship means that dominant framings dominate more than linear "
                "reasoning predicts, while minority framings are suppressed more severely "
                "than their representation in discourse would suggest."
            ),
            # 18 - Contextuality
            (
                "'{concept}' may be contextual: the outcome of examining one property "
                "depends on which other properties are being examined simultaneously. "
                "There is no assignment of pre-existing definite values to all properties "
                "that reproduces the observed correlations -- the properties do not exist "
                "independently of the measurement context. This is stronger than mere "
                "observer bias: it means the properties are genuinely undefined until "
                "a context is specified. For '{concept}', this implies that asking 'what "
                "is it really?' without specifying the context of inquiry is a question "
                "that has no answer."
            ),
            # 19 - Quantum advantage
            (
                "Is there a quantum advantage in reasoning about '{concept}'? Classical "
                "reasoning processes information one path at a time. Quantum-inspired "
                "reasoning processes all paths simultaneously through superposition, "
                "using interference to amplify correct conclusions and suppress incorrect "
                "ones. The advantage is greatest for problems with hidden structure -- "
                "where the correct answer is encoded in correlations between variables "
                "that classical single-path reasoning cannot efficiently explore. If "
                "'{concept}' has such hidden structure, maintaining a superposition of "
                "hypotheses and allowing them to interfere will converge on the answer "
                "faster than serially testing each hypothesis."
            ),
        ]

    def get_keyword_map(self) -> dict[str, list[int]]:
        return {
            "possibilit": [0, 5], "option": [0, 5], "choice": [0, 5],
            "measure": [1, 10], "observ": [1, 10], "monitor": [1, 10],
            "complement": [2], "dual": [2], "wave": [2], "particle": [2],
            "probabilit": [3, 17], "likel": [3, 17], "chance": [3, 17],
            "correlat": [4, 13], "connect": [4], "relat": [4],
            "decid": [5], "commit": [5], "irreversib": [5],
            "barrier": [6], "obstacle": [6], "impossibl": [6],
            "noise": [7, 16], "decay": [7], "environm": [7],
            "unique": [8], "copy": [8], "replica": [8],
            "uncertain": [9], "tradeoff": [9], "precis": [9],
            "watch": [10], "surveil": [10], "frequent": [10],
            "stable": [11], "mode": [11], "spectrum": [11],
            "path": [12], "trajectory": [12], "possib": [12],
            "inform": [13], "entropy": [13], "knowledge": [13],
            "categor": [14], "basis": [14], "framework": [14], "frame": [14],
            "coexist": [15], "mixture": [15], "blend": [15],
            "robust": [16], "error": [16], "protect": [16],
            "dominant": [17], "major": [17], "minor": [17],
            "context": [18], "depend": [18], "situati": [18],
            "advantage": [19], "efficien": [19], "complex": [19],
            "technology": [6, 19], "society": [4, 7], "learning": [10, 12],
            "intelligence": [14, 19], "evolution": [5, 12],
            "health": [1, 9], "network": [4, 13],
        }

    def analyze(self, concept: str) -> str:
        template = self.select_template(concept)
        return template.replace("{concept}", concept)
