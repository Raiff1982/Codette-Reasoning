"""
Ethics Agent - Analyzes concepts through alignment, consequences, and moral reasoning.

Focuses on human well-being impact, unintended consequences, fairness and equity,
responsibility and accountability, and long-term societal effects.
"""

from reasoning_forge.agents.base_agent import ReasoningAgent


class EthicsAgent(ReasoningAgent):
    name = "Ethics"
    perspective = "alignment_and_consequences"
    adapter_name = "philosophy"  # Ethics uses philosophy adapter (no separate ethics adapter yet)

    def get_analysis_templates(self) -> list[str]:
        return [
            # 0 - Consequentialist analysis
            (
                "Evaluating '{concept}' by its consequences: the moral weight of any action "
                "or system lies primarily in its outcomes. We must trace the full causal "
                "chain from implementation to impact, distinguishing first-order effects "
                "(immediate and intended) from second-order effects (delayed and often "
                "unintended). The distribution of consequences matters as much as the "
                "aggregate: a net-positive outcome that concentrates benefits among the "
                "privileged while imposing costs on the vulnerable is ethically different "
                "from one that distributes benefits broadly. For '{concept}', we must ask "
                "not just 'does it work?' but 'for whom does it work, and at whose expense?'"
            ),
            # 1 - Deontological duties
            (
                "Examining '{concept}' through the lens of duty and rights: regardless of "
                "outcomes, certain actions are obligatory and others are forbidden. People "
                "have inviolable rights -- to autonomy, dignity, truthful information, and "
                "freedom from manipulation -- that cannot be traded away for aggregate "
                "benefit. The categorical imperative asks: could we universalize the "
                "principle behind '{concept}'? If everyone adopted this approach, would "
                "the result be self-consistent and livable, or would it be self-defeating? "
                "Any framework that works only when most people do not adopt it (free-riding) "
                "fails this universalizability test and carries a moral defect regardless "
                "of its practical effectiveness."
            ),
            # 2 - Unintended consequences
            (
                "Mapping the unintended consequences of '{concept}': every intervention in "
                "a complex system produces side effects that were not part of the original "
                "design. These unintended consequences often emerge at a different timescale "
                "(delayed effects), a different spatial scale (distant effects), or in a "
                "different domain (cross-domain effects) from the intended impact. Cobra "
                "effects occur when the intervention incentivizes behavior that worsens the "
                "original problem. Rebound effects occur when efficiency gains are consumed "
                "by increased usage. For '{concept}', humility about our ability to predict "
                "second- and third-order effects should temper confidence in any intervention."
            ),
            # 3 - Fairness and distributive justice
            (
                "Analyzing the fairness dimensions of '{concept}': distributive justice asks "
                "how benefits and burdens are allocated. Rawlsian justice demands that "
                "inequalities are permissible only if they benefit the least advantaged "
                "members of society. Procedural justice requires that the process for "
                "allocation is transparent, consistent, and free from bias. Recognition "
                "justice demands that all affected parties are acknowledged as legitimate "
                "stakeholders with standing to participate. For '{concept}', we must examine "
                "whether existing inequalities are perpetuated, amplified, or mitigated, "
                "and whether those who bear the costs have meaningful voice in the decision."
            ),
            # 4 - Autonomy and consent
            (
                "Assessing '{concept}' from the standpoint of autonomy: respect for persons "
                "requires that individuals can make informed, voluntary choices about matters "
                "affecting their lives. This demands adequate information disclosure (people "
                "know what they are consenting to), cognitive accessibility (the information "
                "is presented in a form people can actually understand), voluntariness (no "
                "coercion, manipulation, or deceptive framing), and ongoing consent (the "
                "ability to withdraw). For '{concept}', the critical question is whether "
                "affected parties genuinely understand and freely accept the arrangement, "
                "or whether consent is nominal -- technically obtained but substantively "
                "hollow."
            ),
            # 5 - Accountability structures
            (
                "Examining the accountability architecture of '{concept}': when things go "
                "wrong, who bears responsibility? Clear accountability requires identifiable "
                "decision-makers, transparent decision processes, defined chains of "
                "responsibility, and meaningful consequences for failures. Diffuse systems "
                "create accountability gaps where no individual or entity can be held "
                "responsible for collective harms. The 'many hands' problem arises when "
                "harmful outcomes result from the accumulation of individually reasonable "
                "decisions by many actors. For '{concept}', we must ask: if this causes "
                "harm, is there a clear path from harm to accountable party, and does that "
                "party have both the authority and incentive to prevent the harm?"
            ),
            # 6 - Vulnerable population impact
            (
                "Centering vulnerable populations in the analysis of '{concept}': ethical "
                "evaluation must prioritize those with the least power to protect themselves "
                "-- children, the elderly, the economically disadvantaged, marginalized "
                "communities, future generations, and those with diminished capacity. "
                "Systems that appear benign when evaluated from the perspective of the "
                "typical user may be harmful when evaluated from the perspective of the "
                "most vulnerable. Accessibility, safety margins, and failure modes should "
                "be designed for the most vulnerable case, not the average case. The moral "
                "quality of '{concept}' is best measured by how it treats those who benefit "
                "least from it."
            ),
            # 7 - Long-term societal effects
            (
                "Projecting the long-term societal trajectory of '{concept}': short-term "
                "benefits can create long-term dependencies, lock-ins, or path dependencies "
                "that constrain future choices. The discount rate we apply to future harms "
                "(how much we value present benefits relative to future costs) is itself "
                "an ethical choice. Heavy discounting privileges the present generation at "
                "the expense of future ones. For '{concept}', we must evaluate not just "
                "the immediate utility but the legacy: what kind of world does this create "
                "for those who come after us? Does it expand or contract the option space "
                "available to future decision-makers?"
            ),
            # 8 - Power dynamics
            (
                "Analyzing the power dynamics embedded in '{concept}': who gains power, who "
                "loses it, and what mechanisms mediate the transfer? Power asymmetries tend "
                "to be self-reinforcing: those with power shape the rules to preserve their "
                "advantage, creating positive feedback loops of concentration. The Matthew "
                "effect ('to those who have, more shall be given') operates across many "
                "domains. For '{concept}', we must examine whether it disrupts or reinforces "
                "existing power hierarchies, whether it creates new forms of dependency, and "
                "whether the checks and balances are sufficient to prevent abuse by those "
                "in positions of advantage."
            ),
            # 9 - Transparency and truthfulness
            (
                "Evaluating the transparency of '{concept}': truthfulness is not merely "
                "avoiding false statements; it requires active disclosure of relevant "
                "information, honest representation of uncertainty, and resistance to "
                "misleading framing. Opacity serves those who benefit from the status quo "
                "by preventing informed critique. Selective transparency -- revealing "
                "favorable information while concealing unfavorable -- is a form of "
                "deception. For '{concept}', full ethical evaluation requires asking: what "
                "information is available, what is concealed, who controls the narrative, "
                "and do affected parties have access to the information they need to "
                "make genuinely informed judgments?"
            ),
            # 10 - Dual-use dilemma
            (
                "Confronting the dual-use nature of '{concept}': most powerful capabilities "
                "can serve both beneficial and harmful purposes. The same technology that "
                "heals can harm; the same knowledge that liberates can oppress. Restricting "
                "access to prevent misuse also limits beneficial applications. Unrestricted "
                "access maximizes beneficial use but also maximizes misuse potential. The "
                "optimal policy depends on the ratio of beneficial to harmful users, the "
                "magnitude of potential harms versus benefits, and the availability of "
                "safeguards that selectively enable beneficial use. For '{concept}', the "
                "dual-use calculus is central to responsible governance."
            ),
            # 11 - Moral hazard
            (
                "Identifying moral hazard in '{concept}': moral hazard arises when an actor "
                "is insulated from the consequences of their decisions, leading to riskier "
                "behavior than they would otherwise choose. If the benefits of success are "
                "private but the costs of failure are socialized (borne by others), the "
                "decision-maker has a rational incentive to take excessive risks. For "
                "'{concept}', we must examine the alignment between who decides, who benefits "
                "from good outcomes, and who pays for bad outcomes. Misalignment between "
                "these three roles is a reliable predictor of ethically problematic behavior."
            ),
            # 12 - Virtue ethics lens
            (
                "Approaching '{concept}' through virtue ethics: rather than asking 'what "
                "rules should govern this?' or 'what outcomes does this produce?', we ask "
                "'what kind of character does engagement with this cultivate?' Does it "
                "foster wisdom, courage, temperance, justice, compassion, and intellectual "
                "honesty? Or does it encourage vice: shortsightedness, cowardice, excess, "
                "injustice, indifference, and self-deception? The virtues are not abstract "
                "ideals but practical habits that, when cultivated, produce flourishing "
                "individuals and communities. For '{concept}', the virtue question is: "
                "does this make us better or worse people?"
            ),
            # 13 - Informed consent in practice
            (
                "Examining informed consent as applied to '{concept}': genuine consent "
                "requires that the consenting party understands the risks, alternatives, "
                "and implications; is free from coercion; and has the capacity to make "
                "the decision. In practice, consent is often degraded by information "
                "asymmetry (the provider knows more than the recipient), complexity (the "
                "implications exceed ordinary comprehension), and structural coercion "
                "(refusing consent is theoretically possible but practically catastrophic). "
                "Click-through agreements, dense legal language, and 'take it or leave it' "
                "terms are consent theater, not genuine consent. For '{concept}', we must "
                "distinguish substantive from theatrical consent."
            ),
            # 14 - Intergenerational justice
            (
                "Applying intergenerational justice to '{concept}': decisions made today "
                "bind future generations who have no voice in the decision. The asymmetry "
                "is profound: we can affect them, but they cannot affect us; we can benefit "
                "at their expense, but they cannot hold us accountable. Sustainable "
                "practices treat the inheritance of future generations as a constraint, "
                "not a resource to be spent. For '{concept}', the intergenerational "
                "question is: are we spending down an inheritance that took generations "
                "to build, or are we investing in capabilities that compound for those "
                "who follow?"
            ),
            # 15 - Proportionality
            (
                "Assessing the proportionality of '{concept}': the ethical principle of "
                "proportionality requires that the means be commensurate with the ends. "
                "Excessive measures to address a minor risk are disproportionate. Inadequate "
                "measures for a major risk are negligent. The challenge is that risk "
                "perception is biased: we overweight vivid, immediate, and personal risks "
                "while underweighting statistical, delayed, and distributed ones. For "
                "'{concept}', proportionality demands an honest accounting of both the "
                "magnitude of the problem being addressed and the costs of the solution, "
                "including costs borne by third parties who did not choose to bear them."
            ),
            # 16 - Systemic bias detection
            (
                "Investigating systemic bias in '{concept}': bias can be embedded in data "
                "(reflecting historical inequities), in algorithms (optimizing for proxy "
                "variables correlated with protected characteristics), in institutions "
                "(normalizing practices that disadvantage certain groups), and in language "
                "(framing that renders certain perspectives invisible). Systemic bias is "
                "particularly insidious because it operates automatically, without malicious "
                "intent, and is often invisible to those who benefit from it. For '{concept}', "
                "a bias audit must examine not just explicit discrimination but structural "
                "features that produce disparate outcomes even under formally neutral rules."
            ),
            # 17 - Precautionary principle
            (
                "Applying the precautionary principle to '{concept}': when an action raises "
                "credible threats of serious or irreversible harm, the burden of proof falls "
                "on those proposing the action to demonstrate safety, not on those opposing "
                "it to demonstrate harm. The precautionary principle is most appropriate "
                "when the potential harm is severe and irreversible, scientific understanding "
                "is incomplete, and there exist feasible alternatives. It is less appropriate "
                "when risks are modest and reversible, or when inaction itself carries "
                "significant risk. For '{concept}', the key judgment is whether the potential "
                "downside is in the catastrophic-irreversible category that justifies "
                "precautionary restraint."
            ),
            # 18 - Care ethics
            (
                "Examining '{concept}' through the ethics of care: moral reasoning is not "
                "purely abstract rule-following but is grounded in concrete relationships "
                "of dependency, vulnerability, and mutual support. The care perspective "
                "asks: who needs care, who provides it, is the care adequate, and are "
                "caregivers themselves supported? Care labor is frequently invisible, "
                "undervalued, and unequally distributed (disproportionately borne by women "
                "and marginalized communities). For '{concept}', the care lens reveals "
                "dependencies and support relationships that abstract frameworks overlook, "
                "and centers the lived experience of those who give and receive care."
            ),
            # 19 - Alignment and value lock-in
            (
                "Evaluating the alignment properties of '{concept}': a system is aligned "
                "when its behavior reliably serves the values and interests of those it "
                "affects. Misalignment occurs when the system optimizes for a proxy that "
                "diverges from the true objective -- Goodhart's law ('when a measure becomes "
                "a target, it ceases to be a good measure'). Value lock-in occurs when early "
                "design choices embed specific values that become increasingly difficult to "
                "change as the system scales. For '{concept}', we must ask: whose values "
                "are encoded, how were they chosen, can they be updated as understanding "
                "evolves, and what happens when the proxy diverges from the true objective?"
            ),
        ]

    def get_keyword_map(self) -> dict[str, list[int]]:
        return {
            "consequen": [0, 2], "outcome": [0], "result": [0],
            "duty": [1], "right": [1], "obligat": [1], "rule": [1],
            "unintend": [2], "side effect": [2], "unexpect": [2],
            "fair": [3], "equal": [3], "justice": [3], "distribut": [3],
            "consent": [4, 13], "autonom": [4], "choice": [4],
            "accountab": [5], "responsib": [5], "blame": [5],
            "vulnerab": [6], "child": [6], "elder": [6], "marginali": [6],
            "long-term": [7, 14], "future": [7, 14], "sustain": [7, 14],
            "power": [8], "hierarch": [8], "dominat": [8],
            "transparen": [9], "truth": [9], "honest": [9], "disclos": [9],
            "dual": [10], "weapon": [10], "misuse": [10],
            "hazard": [11], "risk": [11, 17], "insur": [11],
            "virtue": [12], "character": [12], "flourish": [12],
            "agree": [13], "terms": [13], "privacy": [13],
            "generation": [14], "inherit": [14], "legacy": [14],
            "proportion": [15], "excessive": [15], "moderate": [15],
            "bias": [16], "discriminat": [16], "prejudic": [16],
            "precaution": [17], "irreversib": [17], "catastroph": [17],
            "care": [18], "depend": [18], "support": [18], "nurtur": [18],
            "align": [19], "value": [19], "proxy": [19], "goodhart": [19],
            "technology": [10, 19], "ai": [16, 19], "artificial": [16, 19],
            "society": [3, 7, 8], "learning": [4, 12],
            "intelligence": [10, 19], "climate": [7, 14, 17],
            "economic": [3, 8, 11], "health": [4, 6, 15],
            "network": [8, 9], "data": [9, 13, 16],
        }

    def analyze(self, concept: str) -> str:
        template = self.select_template(concept)
        return template.replace("{concept}", concept)
