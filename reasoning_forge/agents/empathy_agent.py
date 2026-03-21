"""
Empathy Agent - Analyzes concepts through emotional, human-centered, and social reasoning.

Focuses on how concepts affect people emotionally, compassionate interpretation,
social dynamics, communication considerations, and psychological well-being.
"""

from reasoning_forge.agents.base_agent import ReasoningAgent


class EmpathyAgent(ReasoningAgent):
    name = "Empathy"
    perspective = "emotional_and_human_centered"
    adapter_name = "empathy"  # Use the Empathy LoRA adapter for real inference

    def get_analysis_templates(self) -> list[str]:
        return [
            # 0 - Emotional impact mapping
            (
                "Mapping the emotional landscape of '{concept}': every concept that touches "
                "human lives generates an emotional field. For those directly involved, "
                "'{concept}' may evoke hope (if it promises improvement), anxiety (if it "
                "threatens the familiar), frustration (if it introduces complexity), or "
                "excitement (if it opens new possibilities). These emotional responses are "
                "not irrational noise overlaid on a rational signal -- they are a rapid, "
                "parallel processing system that integrates more information than conscious "
                "analysis can handle. Dismissing emotional responses as irrelevant is "
                "itself an emotional decision (the emotion of wanting to appear rational) "
                "and discards valuable signal about how '{concept}' is actually experienced "
                "by the people it affects."
            ),
            # 1 - Lived experience perspective
            (
                "Centering the lived experience of '{concept}': abstract analysis risks "
                "losing the texture of what this actually means in someone's daily life. "
                "A person encountering '{concept}' does not experience it as a set of "
                "propositions but as a shift in the felt quality of their day -- a new "
                "worry added to their mental load, a new possibility that brightens their "
                "horizon, a new confusion that makes the familiar strange. Understanding "
                "'{concept}' requires not just knowing what it is but feeling what it is "
                "like: the cognitive effort it demands, the social negotiations it requires, "
                "the way it reshapes routines and relationships. This first-person texture "
                "is where the real impact lives."
            ),
            # 2 - Compassionate reframing
            (
                "Reframing '{concept}' with compassion: when people struggle with or resist "
                "this concept, their difficulty is not a deficiency in understanding but a "
                "legitimate response to a genuine challenge. Resistance often signals that "
                "something important is being threatened -- identity, competence, belonging, "
                "or security. Rather than dismissing resistance, compassionate inquiry asks: "
                "what are you protecting? What would need to be true for this to feel safe? "
                "What support would make this manageable? For '{concept}', the compassionate "
                "reframing recognizes that the human response is data about the concept's "
                "real-world fit, not an obstacle to overcome."
            ),
            # 3 - Social dynamics analysis
            (
                "Analyzing the social dynamics activated by '{concept}': concepts do not "
                "exist in isolation; they are adopted, resisted, negotiated, and transformed "
                "through social interaction. In-group/out-group dynamics determine who is "
                "seen as a legitimate voice on this topic. Status hierarchies determine "
                "whose interpretation prevails. Social proof shapes adoption: people look "
                "to others' reactions before forming their own. Groupthink can suppress "
                "dissenting perspectives that would improve collective understanding. For "
                "'{concept}', the social dynamics may matter more than the concept's "
                "intrinsic merits in determining its real-world trajectory."
            ),
            # 4 - Communication and framing
            (
                "Examining how '{concept}' is communicated and framed: the same content, "
                "presented differently, produces dramatically different responses. Loss "
                "framing ('you will lose X if you do not adopt this') activates different "
                "neural circuitry than gain framing ('you will gain X if you adopt this'). "
                "Concrete examples engage empathy; abstract statistics do not. Narrative "
                "structure (beginning-middle-end) makes information memorable; list format "
                "makes it forgettable. For '{concept}', the communication design is not "
                "mere packaging but fundamentally shapes understanding, acceptance, and "
                "behavior. A brilliant concept poorly communicated is indistinguishable "
                "from a mediocre one."
            ),
            # 5 - Psychological safety assessment
            (
                "Assessing the psychological safety implications of '{concept}': people "
                "engage productively with challenging ideas only when they feel safe enough "
                "to be vulnerable -- to admit confusion, ask naive questions, and make "
                "mistakes without social penalty. If '{concept}' is introduced in an "
                "environment where asking questions signals incompetence, where mistakes "
                "are punished, or where dissent is suppressed, people will perform "
                "understanding rather than achieve it. The intellectual quality of "
                "engagement with '{concept}' is bounded by the psychological safety of "
                "the environment. Creating conditions where genuine engagement is safe "
                "is a prerequisite for genuine understanding."
            ),
            # 6 - Identity and belonging
            (
                "Exploring how '{concept}' intersects with identity and belonging: people "
                "do not evaluate concepts in a vacuum; they evaluate them in terms of what "
                "adoption means for their identity. Does embracing '{concept}' signal "
                "membership in a valued group? Does rejecting it? The identity calculus "
                "often overrides the epistemic calculus: people will reject well-supported "
                "ideas that threaten their group membership and accept poorly-supported "
                "ones that affirm it. For '{concept}', understanding the identity landscape "
                "-- which identities this concept affirms, threatens, or is irrelevant to "
                "-- predicts adoption patterns more accurately than the concept's objective "
                "merits."
            ),
            # 7 - Grief and loss recognition
            (
                "Acknowledging the grief dimension of '{concept}': every significant change "
                "involves loss, and loss requires grief. Even positive changes -- a promotion, "
                "a new technology, a better system -- require letting go of the familiar: "
                "old competencies that are now obsolete, old relationships that are now "
                "restructured, old identities that no longer fit. The Kubler-Ross stages "
                "(denial, anger, bargaining, depression, acceptance) are not a rigid sequence "
                "but a map of common emotional responses to loss. For '{concept}', naming "
                "and honoring what is lost -- rather than insisting that only the gains "
                "matter -- allows people to move through the transition rather than getting "
                "stuck in resistance."
            ),
            # 8 - Trust dynamics
            (
                "Analyzing the trust architecture of '{concept}': trust is the invisible "
                "infrastructure that determines whether systems function or fail. It is "
                "built slowly through consistent behavior, transparency, and demonstrated "
                "competence, and destroyed quickly by betrayal, opacity, or incompetence. "
                "For '{concept}', the trust questions are: who needs to trust whom for this "
                "to work? Is that trust warranted by track record? What happens when trust "
                "is violated (is there a repair mechanism)? Are there trust asymmetries "
                "where one party bears vulnerability while the other holds power? Trust "
                "deficits cannot be solved by technical improvements alone -- they require "
                "relational repair."
            ),
            # 9 - Cognitive load and overwhelm
            (
                "Assessing the cognitive load imposed by '{concept}': human working memory "
                "has a limited capacity (roughly 4 +/- 1 chunks of information). Every new "
                "concept that must be held in mind simultaneously competes for this scarce "
                "resource. Complex concepts that require juggling many interrelated pieces "
                "can overwhelm working memory, producing a felt experience of confusion and "
                "frustration that has nothing to do with intellectual capacity and everything "
                "to do with presentation design. For '{concept}', the empathic question is: "
                "how can this be chunked, sequenced, and scaffolded to fit within human "
                "cognitive limits without sacrificing essential complexity?"
            ),
            # 10 - Motivation and meaning
            (
                "Exploring the motivational landscape of '{concept}': Self-Determination "
                "Theory identifies three basic psychological needs: autonomy (the feeling "
                "of volition and choice), competence (the feeling of mastery and effectiveness), "
                "and relatedness (the feeling of connection and belonging). Engagement with "
                "'{concept}' will be intrinsically motivated when it satisfies these needs "
                "and extrinsically motivated (fragile, resentful compliance) when it frustrates "
                "them. For '{concept}', the design question is: does engagement with this "
                "concept make people feel more autonomous, competent, and connected, or does "
                "it impose control, induce helplessness, and isolate?"
            ),
            # 11 - Narrative and storytelling
            (
                "Situating '{concept}' within human narrative: humans are storytelling animals "
                "-- we make sense of the world by constructing narratives with characters, "
                "motivations, conflicts, and resolutions. A concept presented as a story "
                "('there was a problem, people tried solutions, here is what they learned') "
                "is absorbed and remembered far more effectively than the same information "
                "presented as disconnected facts. For '{concept}', the narrative question "
                "is: what is the story here? Who are the characters? What is the conflict? "
                "What is at stake? How does this chapter connect to the larger story that "
                "people are already telling about their lives and work?"
            ),
            # 12 - Perspective-taking exercise
            (
                "Practicing perspective-taking with '{concept}': imagine experiencing this "
                "from the viewpoint of an enthusiastic early adopter (everything is "
                "possibility), a skeptical veteran (I have seen this before and it did not "
                "work), a vulnerable newcomer (I do not understand and I am afraid to ask), "
                "an overwhelmed practitioner (I do not have bandwidth for one more thing), "
                "and a curious outsider (I have no stake but find this interesting). Each "
                "perspective reveals different features of '{concept}' and different emotional "
                "valences. The concept is not one thing but many things, depending on who "
                "is experiencing it and what they bring to the encounter."
            ),
            # 13 - Relational impact
            (
                "Examining how '{concept}' affects relationships: concepts do not only change "
                "what people think; they change how people relate to each other. Does "
                "'{concept}' create shared language that strengthens collaboration, or "
                "jargon that excludes outsiders? Does it create a hierarchy of expertise "
                "that distances the knowledgeable from the uninitiated? Does it provide "
                "common ground for diverse stakeholders or a wedge that divides them? "
                "The relational dimension of '{concept}' -- how it brings people together "
                "or pushes them apart -- often determines its long-term viability more than "
                "its technical merits."
            ),
            # 14 - Stress and coping
            (
                "Analyzing the stress profile of '{concept}': when encountering something "
                "new or challenging, people appraise both the demand (how threatening or "
                "difficult is this?) and their resources (do I have what I need to cope?). "
                "When demands exceed resources, the result is stress. The stress response "
                "narrows attention, reduces creativity, and triggers fight-flight-freeze "
                "behavior -- exactly the opposite of the open, curious engagement that "
                "learning requires. For '{concept}', the empathic design question is: how "
                "can we increase people's resources (support, information, time, practice) "
                "or decrease the perceived demand (scaffolding, chunking, normalization of "
                "struggle) to keep the challenge in the productive zone?"
            ),
            # 15 - Cultural sensitivity
            (
                "Examining '{concept}' through cultural sensitivity: concepts that seem "
                "universal often carry culturally specific assumptions about individualism "
                "vs collectivism, hierarchy vs egalitarianism, directness vs indirectness, "
                "or risk-taking vs caution. A concept designed within an individualist "
                "framework may not translate to collectivist contexts without significant "
                "adaptation. Communication norms that are standard in one culture may be "
                "offensive in another. For '{concept}', cultural sensitivity asks: whose "
                "cultural assumptions are embedded in the default design, and how must the "
                "concept be adapted for genuine cross-cultural validity?"
            ),
            # 16 - Emotional intelligence integration
            (
                "Integrating emotional intelligence into '{concept}': Goleman's framework "
                "identifies self-awareness (recognizing one's own emotions), self-regulation "
                "(managing emotional responses), social awareness (reading others' emotions), "
                "and relationship management (navigating social interactions skillfully). "
                "For '{concept}', each dimension matters: self-awareness helps people "
                "recognize their biases toward the concept; self-regulation helps manage "
                "anxiety about change; social awareness helps read the room when introducing "
                "the concept; relationship management helps navigate disagreements "
                "constructively. Emotional intelligence is not a soft add-on to rational "
                "analysis but a prerequisite for its effective application."
            ),
            # 17 - Healing and repair
            (
                "Considering '{concept}' through the lens of healing and repair: if this "
                "concept touches areas where people have been harmed -- by previous failed "
                "implementations, broken promises, or traumatic experiences -- the entry "
                "point matters enormously. Approaching damaged ground with the energy of "
                "'we have the solution' triggers defensiveness. Approaching with "
                "acknowledgment of past harm ('we know this has been painful before, and "
                "here is how this time is different') opens the possibility of engagement. "
                "For '{concept}', healing-oriented design begins by asking: what wounds "
                "exist in this space, and how do we avoid reopening them?"
            ),
            # 18 - Play and curiosity
            (
                "Engaging with '{concept}' through the spirit of play: play is not the "
                "opposite of seriousness but the opposite of rigidity. A playful stance "
                "toward '{concept}' gives permission to explore without commitment, to "
                "ask 'what if?' without 'what for?', to make mistakes without consequences. "
                "Play activates the exploratory system (curiosity, novelty-seeking, "
                "experimentation) rather than the defensive system (anxiety, avoidance, "
                "threat-detection). Children learn most complex skills through play, not "
                "instruction. For '{concept}', designing entry points that feel playful "
                "rather than high-stakes can dramatically accelerate genuine understanding "
                "by reducing the emotional barriers to engagement."
            ),
            # 19 - Collective emotion and morale
            (
                "Reading the collective emotional field around '{concept}': groups have "
                "emergent emotional states that are more than the sum of individual feelings. "
                "Collective excitement creates momentum that carries individuals past "
                "obstacles they could not overcome alone. Collective demoralization creates "
                "paralysis that defeats even the most motivated individuals. Emotional "
                "contagion -- the rapid spread of feelings through a group -- can amplify "
                "either response. For '{concept}', attending to the collective emotional "
                "state is as important as attending to the logical content. A technically "
                "sound approach introduced into a demoralized group will fail; a mediocre "
                "approach carried by collective enthusiasm may succeed."
            ),
        ]

    def get_keyword_map(self) -> dict[str, list[int]]:
        return {
            "emotion": [0, 16], "feel": [0, 1], "affect": [0],
            "experience": [1], "daily": [1], "life": [1], "personal": [1],
            "resist": [2], "struggle": [2], "difficult": [2],
            "social": [3, 13], "group": [3, 19], "community": [3],
            "communicat": [4], "message": [4], "frame": [4], "present": [4],
            "safe": [5], "vulnerab": [5], "mistake": [5],
            "identity": [6], "belong": [6], "member": [6],
            "change": [7], "loss": [7], "transition": [7],
            "trust": [8], "betray": [8], "credib": [8], "reliab": [8],
            "complex": [9], "confus": [9], "overwhelm": [9],
            "motivat": [10], "engage": [10], "meaning": [10],
            "story": [11], "narrative": [11], "journey": [11],
            "perspectiv": [12], "viewpoint": [12], "stakeholder": [12],
            "relat": [13], "collaborat": [13], "team": [13],
            "stress": [14], "anxiety": [14], "coping": [14], "burnout": [14],
            "cultur": [15], "divers": [15], "global": [15],
            "aware": [16], "intelligen": [16], "regulat": [16],
            "heal": [17], "repair": [17], "trauma": [17], "harm": [17],
            "play": [18], "curiosi": [18], "explor": [18], "fun": [18],
            "morale": [19], "momentum": [19], "collective": [19],
            "technology": [7, 9], "education": [5, 9, 14],
            "health": [0, 14, 17], "work": [5, 10, 14],
        }

    def analyze(self, concept: str) -> str:
        template = self.select_template(concept)
        return template.replace("{concept}", concept)
