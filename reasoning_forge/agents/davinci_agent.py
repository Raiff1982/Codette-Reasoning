"""
DaVinci Agent - Analyzes concepts through creative, inventive, and cross-domain reasoning.

Focuses on cross-domain connections, biomimicry and nature-inspired solutions,
iterative improvement possibilities, visual/spatial reasoning, and novel
combinations of existing ideas.
"""

from reasoning_forge.agents.base_agent import ReasoningAgent


class DaVinciAgent(ReasoningAgent):
    name = "DaVinci"
    perspective = "creative_and_inventive"
    adapter_name = "davinci"  # Use the DaVinci LoRA adapter for real inference

    def get_analysis_templates(self) -> list[str]:
        return [
            # 0 - Cross-domain analogy
            (
                "Drawing cross-domain connections to '{concept}': the deepest insights often "
                "come from recognizing structural similarities between apparently unrelated "
                "fields. A river delta and a lightning bolt share the same branching "
                "optimization geometry. A market economy and an ant colony share the same "
                "decentralized coordination logic. For '{concept}', the creative question "
                "is: what other domain exhibits the same deep structure? If we map the "
                "entities, relationships, and dynamics of '{concept}' onto those of the "
                "analogous domain, which features are preserved (revealing shared principles) "
                "and which break (revealing domain-specific constraints)? The preserved "
                "features point toward universal laws; the broken features point toward "
                "opportunities for domain-specific innovation."
            ),
            # 1 - Biomimicry lens
            (
                "Examining '{concept}' through biomimicry: nature has been solving design "
                "problems for 3.8 billion years through evolutionary optimization. Bones "
                "achieve maximum strength with minimum material by using trabecular "
                "architecture -- hollow struts arranged along stress lines. Spider silk "
                "achieves tensile strength exceeding steel at a fraction of the weight "
                "through hierarchical nanostructure. Termite mounds maintain constant "
                "internal temperature without energy input through passive ventilation "
                "design. For '{concept}', the biomimicry question is: what organism or "
                "ecosystem has already solved an analogous problem, and what principle "
                "does its solution exploit that we have not yet applied?"
            ),
            # 2 - Combinatorial invention
            (
                "Approaching '{concept}' through combinatorial creativity: most inventions "
                "are novel combinations of existing elements. The printing press combined "
                "the wine press, movable type, oil-based ink, and paper. The smartphone "
                "combined a phone, camera, GPS, accelerometer, and internet browser into "
                "a device that is qualitatively different from any of its components. For "
                "'{concept}', the combinatorial strategy asks: what are the elemental "
                "components, and what happens when we recombine them in unusual ways? "
                "Pair each element with every other element and ask whether the combination "
                "produces something valuable. The most productive combinations are often "
                "between elements from distant categories that no one thought to connect."
            ),
            # 3 - Inversion and reversal
            (
                "Inverting '{concept}': one of the most powerful creative strategies is "
                "systematic inversion -- taking every assumption and reversing it. If the "
                "current approach pushes, try pulling. If it adds, try subtracting. If it "
                "centralizes, try distributing. If it speeds up, try slowing down. Many "
                "breakthrough solutions came from inverting an assumption everyone took for "
                "granted. Vacuum cleaners worked by pushing air until Dyson inverted the "
                "flow. Assembly lines brought work to workers; Toyota inverted this by "
                "bringing workers to work (cellular manufacturing). For '{concept}', "
                "systematically listing and inverting each assumption reveals a space of "
                "unconventional approaches that conventional thinking renders invisible."
            ),
            # 4 - Visual-spatial reasoning
            (
                "Visualizing the spatial architecture of '{concept}': representing abstract "
                "relationships as spatial structures makes hidden patterns visible. If we "
                "map the components of '{concept}' to nodes and their relationships to "
                "edges, the resulting graph reveals clustering (tightly connected subgroups), "
                "bridges (elements connecting otherwise separate clusters), hubs (elements "
                "with many connections), and periphery (weakly connected elements). The "
                "topology of this graph -- its shape, density, and symmetry -- encodes "
                "information about the concept's structure that verbal description alone "
                "cannot capture. Hub nodes are high-leverage intervention points; bridges "
                "are fragile connections whose failure would fragment the system."
            ),
            # 5 - Constraint as catalyst
            (
                "Using constraints as creative catalysts for '{concept}': rather than seeing "
                "limitations as obstacles, use them as forcing functions for innovation. "
                "Twitter's 140-character limit forced a new style of writing. The sonnet's "
                "14-line constraint forced poetic compression. Budget constraints force "
                "elegant engineering. For '{concept}', deliberately imposing additional "
                "constraints -- what if we had to solve this with half the resources? In "
                "one-tenth the time? With no electricity? For a user who cannot see? -- "
                "often breaks through conventional thinking by invalidating the default "
                "approach and forcing genuinely creative alternatives."
            ),
            # 6 - First principles reconstruction
            (
                "Reconstructing '{concept}' from first principles: strip away all inherited "
                "conventions, historical accidents, and 'we have always done it this way' "
                "accretions. What remains when we reduce the problem to its fundamental "
                "requirements? Starting from physical laws, human needs, and mathematical "
                "constraints, what is the minimum viable solution? Often the gap between "
                "this first-principles design and the current state reveals enormous "
                "inefficiency that is invisible from within the conventional framework. "
                "SpaceX re-derived rocket design from first principles and found that "
                "materials cost only 2% of the final price. For '{concept}', the first-"
                "principles question is: if we were designing this from scratch today, "
                "knowing what we know, what would it look like?"
            ),
            # 7 - Morphological analysis
            (
                "Applying morphological analysis to '{concept}': decompose the concept into "
                "its independent dimensions, list the possible values for each dimension, "
                "and then systematically explore the combinatorial space. If '{concept}' has "
                "five dimensions with four options each, the morphological space contains "
                "1024 configurations. Most are impractical, but a systematic sweep guarantees "
                "that no promising combination is overlooked by the biases of free-form "
                "brainstorming. The power of morphological analysis is that it converts "
                "creative search from a haphazard process into a structured exploration, "
                "surfacing configurations that no one would think of spontaneously because "
                "they cross conventional category boundaries."
            ),
            # 8 - Prototype thinking
            (
                "Applying prototype thinking to '{concept}': instead of perfecting a plan "
                "before executing, build the quickest possible embodiment of the core idea "
                "and learn from its failures. The prototype is not the solution but a "
                "question asked in physical form: 'does this work?' Each prototype cycle "
                "-- build, test, learn, rebuild -- compresses the feedback loop and "
                "generates knowledge that purely theoretical analysis cannot provide. For "
                "'{concept}', the prototype question is: what is the smallest, cheapest, "
                "fastest experiment that would test the most critical assumption? Building "
                "that experiment, even if crude, will teach us more than months of "
                "theoretical refinement."
            ),
            # 9 - Emergent properties through scale
            (
                "Exploring emergent properties of '{concept}' at different scales: systems "
                "often exhibit qualitatively new behavior when scaled up or down. A single "
                "neuron computes nothing interesting; a billion networked neurons produce "
                "consciousness. A single transaction is trivial; billions of transactions "
                "produce market dynamics. For '{concept}', the scale question asks: what "
                "happens when we multiply the instances by a thousand? By a million? What "
                "new phenomena emerge at scale that are absent at the individual level? "
                "Conversely, what happens when we reduce to a single instance? Scale "
                "transitions often reveal the concept's most interesting properties."
            ),
            # 10 - Da Vinci's sfumato (ambiguity as resource)
            (
                "Embracing the sfumato of '{concept}': Leonardo da Vinci practiced sfumato "
                "-- the technique of leaving edges soft and ambiguous rather than sharply "
                "defined. In creative reasoning, maintaining productive ambiguity resists "
                "premature closure and keeps the interpretive space open. The undefined "
                "edges of '{concept}' are not defects but fertile zones where new "
                "connections can form. Attempts to define everything precisely may satisfy "
                "the desire for clarity but kill the creative potential that lives in "
                "the ambiguous spaces between categories. Sit with the ambiguity long "
                "enough and patterns emerge that rigid definitions would have prevented."
            ),
            # 11 - Lateral thinking transfer
            (
                "Applying lateral thinking to '{concept}': Edward de Bono's lateral "
                "thinking techniques include random entry (inject an unrelated concept "
                "and force a connection), provocation (make a deliberately absurd statement "
                "and extract useful ideas from it), and challenge (question why things are "
                "done the current way). For '{concept}', a random entry might connect it "
                "to deep-sea bioluminescence, medieval cathedral construction, or jazz "
                "improvisation. The forced connection between '{concept}' and a random "
                "domain breaks habitual thought patterns and creates novel pathways that "
                "logical deduction alone cannot reach."
            ),
            # 12 - Fractal self-similarity
            (
                "Examining '{concept}' for fractal self-similarity: does the same pattern "
                "recur at different scales? Coastlines look similar whether photographed "
                "from a satellite or a drone. Organizational hierarchies replicate the same "
                "power dynamics from teams to departments to divisions. Blood vessel "
                "networks branch according to the same rules from arteries to capillaries. "
                "If '{concept}' exhibits self-similarity, then understanding the pattern at "
                "one scale gives us understanding at all scales. A single well-studied "
                "instance contains the blueprint for the entire hierarchy, and interventions "
                "that work at one scale can be adapted to work at others."
            ),
            # 13 - Negative space analysis
            (
                "Analyzing the negative space of '{concept}': just as a sculptor defines a "
                "form by removing material, we can define '{concept}' by examining what it "
                "is not. What has been excluded, ignored, or left unsaid? The negative space "
                "-- the complement of the concept -- often contains crucial information. "
                "What alternatives were considered and rejected? What possibilities does "
                "the current framing render invisible? The adjacent possible (the set of "
                "things that are one step away from existing) is often more interesting "
                "than the concept itself, because it represents the immediate frontier "
                "of innovation."
            ),
            # 14 - Systems of constraints (Rube Goldberg inversion)
            (
                "Simplifying '{concept}' by subtracting rather than adding: the natural "
                "tendency in design is to add features, layers, and complexity. The "
                "harder and more valuable creative move is subtraction: what can we "
                "remove while preserving or improving function? Antoine de Saint-Exupery "
                "said perfection is achieved not when there is nothing left to add, but "
                "when there is nothing left to take away. For '{concept}', the subtraction "
                "exercise asks: what happens if we remove each component in turn? Which "
                "removals are catastrophic (essential components) and which are beneficial "
                "(removing parasitic complexity)? The minimal viable version is often "
                "more powerful than the maximal one."
            ),
            # 15 - TRIZ inventive principles
            (
                "Applying TRIZ inventive principles to '{concept}': Genrich Altshuller's "
                "analysis of 200,000 patents revealed 40 recurring inventive principles. "
                "Segmentation (divide a monolithic system into parts). Extraction (remove "
                "a problematic element and deal with it separately). Local quality (make "
                "each part optimized for its local function rather than forcing uniformity). "
                "Asymmetry (break the symmetry of a symmetric design to improve function). "
                "Nesting (place one object inside another). Prior action (perform required "
                "changes before they are needed). For '{concept}', systematically applying "
                "each principle generates a structured menu of inventive strategies that "
                "goes far beyond unconstrained brainstorming."
            ),
            # 16 - Synesthesia and cross-modal thinking
            (
                "Engaging cross-modal perception for '{concept}': what does this concept "
                "sound like? What texture does it have? What temperature? What color? "
                "Cross-modal associations -- thinking about a concept through sensory "
                "channels that do not literally apply -- activate neural pathways that "
                "linear verbal reasoning does not reach. Kandinsky heard colors and saw "
                "sounds; this synesthetic thinking produced radically new art. For "
                "'{concept}', translating it into sensory terms (the rhythm of its "
                "processes, the texture of its interactions, the weight of its consequences) "
                "can reveal structural features that abstract analysis misses."
            ),
            # 17 - Nature's design patterns
            (
                "Identifying nature's design patterns in '{concept}': evolution has converged "
                "on certain solutions repeatedly because they are optimal under common "
                "constraints. Hexagonal packing (beehives, basalt columns) maximizes area "
                "with minimum material. Branching networks (trees, rivers, lungs, lightning) "
                "optimize distribution from a source to a volume. Spiral growth (shells, "
                "galaxies, hurricanes) manages expansion while maintaining structural "
                "integrity. For '{concept}', asking which of nature's recurring design "
                "patterns applies suggests time-tested architectures that human design "
                "has not yet exploited."
            ),
            # 18 - Bisociation and humor
            (
                "Applying Koestler's bisociation to '{concept}': Arthur Koestler proposed "
                "that creativity, humor, and scientific discovery share the same cognitive "
                "mechanism: bisociation -- the simultaneous perception of a situation in "
                "two habitually incompatible frames of reference. The collision of frames "
                "produces a flash of insight (in science), a punchline (in humor), or a "
                "novel artifact (in art). For '{concept}', identifying two incompatible "
                "but individually valid frames and forcing them to coexist generates the "
                "cognitive tension from which genuinely original ideas spring. The more "
                "distant the frames, the more surprising and potentially valuable the "
                "bisociative insight."
            ),
            # 19 - Future archaeology
            (
                "Practicing future archaeology on '{concept}': imagine examining the "
                "artifacts of this concept a hundred years from now, from a future "
                "civilization's perspective. What would they find elegant? What would "
                "they find primitive? What would puzzle them about our choices? This "
                "temporal displacement reveals assumptions we cannot see from within our "
                "own era. The future archaeologist would ask: why did they do it this way "
                "when a simpler method was available? What constraint -- technological, "
                "social, or cognitive -- forced this particular design? For '{concept}', "
                "this exercise separates the timeless core from the historically contingent "
                "shell and suggests directions for forward-looking redesign."
            ),
        ]

    def get_keyword_map(self) -> dict[str, list[int]]:
        return {
            "analog": [0, 18], "similar": [0, 12], "connect": [0, 4],
            "nature": [1, 17], "biolog": [1, 17], "organism": [1],
            "combin": [2, 7], "element": [2, 7], "component": [2],
            "invert": [3], "revers": [3], "opposit": [3],
            "visual": [4], "spatial": [4], "map": [4], "graph": [4],
            "constrain": [5], "limit": [5], "restrict": [5],
            "first principle": [6], "fundament": [6], "basic": [6],
            "dimension": [7], "option": [7], "configur": [7],
            "prototype": [8], "experiment": [8], "test": [8], "iterate": [8],
            "scale": [9, 12], "grow": [9], "expand": [9],
            "ambigu": [10], "fuzzy": [10], "unclear": [10],
            "creativ": [11, 18], "novel": [11, 18], "innovat": [11],
            "pattern": [12, 17], "recur": [12], "repeat": [12],
            "absent": [13], "missing": [13], "negative": [13],
            "simplif": [14], "remov": [14], "minimal": [14],
            "invent": [15], "patent": [15], "engineer": [15],
            "sense": [16], "perceiv": [16], "feel": [16],
            "evolut": [17], "converge": [17], "branch": [17],
            "humor": [18], "surprising": [18], "collision": [18],
            "future": [19], "legacy": [19], "long-term": [19],
            "technology": [2, 6, 15], "design": [1, 14, 15],
            "art": [10, 16], "music": [16, 18],
        }

    def analyze(self, concept: str) -> str:
        template = self.select_template(concept)
        return template.replace("{concept}", concept)
