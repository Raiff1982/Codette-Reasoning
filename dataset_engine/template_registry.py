"""
Template Registry for Codette Dataset Generation
=================================================

Central registry of question templates, topic pools, subtopic maps,
and content seeds for all LoRA adapters. Each adapter has:
  - 30-60 question templates with placeholders
  - 40-80 specific topics with subtopics
  - Content seed maps for generating real educational answers
  - Counterexample templates (misconception / "why is X wrong" style)
"""

import random
from typing import Dict, List, Tuple, Optional


class TemplateRegistry:
    """Manages question templates, topic pools, and content metadata for all adapters."""

    # Target sizes per adapter
    ADAPTER_TARGETS: Dict[str, int] = {
        "newton": 3000,
        "davinci": 2500,
        "empathy": 2500,
        "philosophy": 2000,
        "quantum": 2000,
        "consciousness": 3000,
        "multi_perspective": 2500,
        "systems_architecture": 2000,
    }

    SYSTEM_PROMPT = (
        "You are Codette, a recursive multi-perspective reasoning AI. "
        "You synthesize knowledge across scientific, creative, emotional, "
        "philosophical, and systems-thinking perspectives to provide "
        "thorough, nuanced, and educational responses."
    )

    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)
        self._registries: Dict[str, dict] = {}
        self._build_all_registries()

    def get_adapter_names(self) -> List[str]:
        return list(self.ADAPTER_TARGETS.keys())

    def get_target(self, adapter: str) -> int:
        return self.ADAPTER_TARGETS[adapter]

    def get_registry(self, adapter: str) -> dict:
        return self._registries[adapter]

    def sample_question(self, adapter: str) -> Tuple[str, str, str, str]:
        """Sample a filled question for an adapter.

        Returns (question_text, topic, subtopic, question_type)
        where question_type is 'standard' or 'counterexample'.
        """
        reg = self._registries[adapter]
        topics = reg["topics"]
        topic = self._rng.choice(topics)
        subtopics = reg["subtopic_map"].get(topic, reg.get("default_subtopics", [topic]))
        subtopic = self._rng.choice(subtopics) if subtopics else topic
        concepts = reg.get("concepts", topics)
        concept = self._rng.choice(concepts)

        # 12% chance of counterexample
        if self._rng.random() < 0.12:
            template = self._rng.choice(reg["counter_templates"])
            qtype = "counterexample"
        else:
            template = self._rng.choice(reg["templates"])
            qtype = "standard"

        question = template.format(topic=topic, subtopic=subtopic, concept=concept)
        return question, topic, subtopic, qtype

    # ------------------------------------------------------------------
    # Registry builders
    # ------------------------------------------------------------------

    def _build_all_registries(self):
        self._build_newton()
        self._build_davinci()
        self._build_empathy()
        self._build_philosophy()
        self._build_quantum()
        self._build_consciousness()
        self._build_multi_perspective()
        self._build_systems_architecture()

    # ======================== NEWTON ========================
    def _build_newton(self):
        topics = [
            "motion", "force", "momentum", "kinetic energy", "potential energy",
            "orbital mechanics", "conservation of energy", "conservation of momentum",
            "thermodynamics", "optics", "gravity", "acceleration", "friction",
            "projectile motion", "wave mechanics", "simple harmonic motion",
            "Newton's first law", "Newton's second law", "Newton's third law",
            "Kepler's laws", "fluid dynamics", "pressure", "electromagnetic induction",
            "work-energy theorem", "torque", "angular momentum", "rotational kinematics",
            "buoyancy", "heat transfer", "entropy", "refraction", "diffraction",
            "Doppler effect", "terminal velocity", "centripetal force", "elastic collisions",
            "inelastic collisions", "impulse", "spring force", "gravitational potential",
            "escape velocity", "tidal forces", "Bernoulli's principle", "viscosity",
            "thermal equilibrium", "specific heat capacity", "latent heat",
            "ideal gas law", "Carnot cycle", "blackbody radiation", "photoelectric effect",
        ]

        subtopic_map = {
            "motion": ["uniform motion", "accelerated motion", "circular motion", "relative motion"],
            "force": ["contact forces", "field forces", "net force", "balanced forces", "unbalanced forces"],
            "momentum": ["linear momentum", "angular momentum", "impulse-momentum theorem", "conservation of momentum"],
            "kinetic energy": ["translational kinetic energy", "rotational kinetic energy", "relativistic kinetic energy"],
            "potential energy": ["gravitational PE", "elastic PE", "electric PE", "chemical PE"],
            "orbital mechanics": ["elliptical orbits", "orbital velocity", "escape velocity", "geostationary orbits"],
            "conservation of energy": ["mechanical energy", "thermal energy conversion", "mass-energy equivalence"],
            "thermodynamics": ["first law", "second law", "third law", "zeroth law", "heat engines"],
            "optics": ["reflection", "refraction", "diffraction", "interference", "polarization"],
            "gravity": ["gravitational field", "gravitational constant", "inverse square law", "gravitational waves"],
            "acceleration": ["constant acceleration", "centripetal acceleration", "tangential acceleration"],
            "friction": ["static friction", "kinetic friction", "rolling friction", "air resistance"],
            "projectile motion": ["launch angle", "range equation", "maximum height", "time of flight"],
            "wave mechanics": ["transverse waves", "longitudinal waves", "standing waves", "resonance"],
            "simple harmonic motion": ["pendulum", "mass-spring system", "amplitude", "period and frequency"],
            "Newton's first law": ["inertia", "reference frames", "force equilibrium"],
            "Newton's second law": ["F=ma", "net force calculation", "mass vs weight"],
            "Newton's third law": ["action-reaction pairs", "normal force", "tension"],
            "Kepler's laws": ["elliptical orbits", "equal areas", "period-distance relation"],
            "fluid dynamics": ["laminar flow", "turbulent flow", "Reynolds number", "continuity equation"],
            "pressure": ["atmospheric pressure", "hydrostatic pressure", "Pascal's principle"],
            "electromagnetic induction": ["Faraday's law", "Lenz's law", "magnetic flux", "eddy currents"],
            "work-energy theorem": ["net work", "kinetic energy change", "conservative forces"],
            "torque": ["moment arm", "angular acceleration", "rotational equilibrium"],
            "angular momentum": ["spin angular momentum", "orbital angular momentum", "precession"],
            "entropy": ["disorder", "irreversibility", "Boltzmann entropy", "information entropy"],
            "Doppler effect": ["approaching source", "receding source", "relativistic Doppler"],
            "centripetal force": ["circular motion", "banked curves", "orbital motion"],
            "Bernoulli's principle": ["airfoil lift", "venturi effect", "fluid speed and pressure"],
            "Carnot cycle": ["efficiency", "reversible processes", "heat reservoirs"],
            "blackbody radiation": ["Wien's law", "Stefan-Boltzmann law", "Planck's law"],
            "photoelectric effect": ["threshold frequency", "work function", "photon energy"],
        }

        default_subtopics = ["fundamental principles", "mathematical formulation", "experimental evidence", "real-world applications"]

        templates = [
            "Explain {topic} and its fundamental principles.",
            "How does {topic} relate to {subtopic}?",
            "What is the mathematical relationship governing {topic}?",
            "Give a real-world example of {topic} in action.",
            "Why is {topic} important in classical physics?",
            "Describe the key principles of {topic}.",
            "How would Newton analyze {topic}?",
            "Derive the relationship between {topic} and {subtopic}.",
            "What experiments demonstrate {topic}?",
            "Compare {topic} and {concept} in terms of physical behavior.",
            "How is {topic} applied in engineering?",
            "Explain the conservation laws related to {topic}.",
            "What happens to {topic} in a frictionless environment?",
            "How does {topic} change at very high speeds?",
            "Describe the vector nature of {topic}.",
            "What units are used to measure {topic} and why?",
            "How does {topic} affect {subtopic} in a closed system?",
            "What role does {topic} play in satellite motion?",
            "Explain {topic} using a free-body diagram approach.",
            "How did Newton's work advance our understanding of {topic}?",
            "What is the dimensional analysis of {topic}?",
            "How does {subtopic} emerge from the principles of {topic}?",
            "Explain why {topic} is a scalar or vector quantity.",
            "What are the boundary conditions for {topic}?",
            "How does temperature affect {topic}?",
            "Describe an experiment a student could perform to measure {topic}.",
            "How does {topic} behave differently in fluids versus solids?",
            "What is the historical development of our understanding of {topic}?",
            "How does {topic} apply to everyday transportation?",
            "What assumptions are made when modeling {topic}?",
            "Calculate the {topic} for a 5 kg object moving at 10 m/s.",
            "Explain the graphical representation of {topic} over time.",
            "What instruments measure {topic}?",
            "How is {topic} related to energy transformations?",
            "Why does {topic} obey an inverse square relationship?",
            "How would an astronaut experience {topic} differently in orbit?",
            "What is the role of {topic} in planetary formation?",
            "How do engineers account for {topic} in bridge design?",
            "Explain {topic} at the molecular level.",
            "What is the connection between {topic} and {concept}?",
        ]

        counter_templates = [
            "What is a common misconception about {topic}?",
            "Why is the statement 'heavier objects fall faster' wrong in the context of {topic}?",
            "Explain why the naive understanding of {topic} is incomplete.",
            "What mistake do students commonly make when calculating {topic}?",
            "Why is it incorrect to say {topic} and {concept} are the same thing?",
            "Debunk a popular myth related to {topic}.",
            "What oversimplification about {topic} leads to errors?",
            "Why does the textbook formula for {topic} break down at extremes?",
            "Correct the misconception that {topic} only applies to {subtopic}.",
            "What is wrong with treating {topic} as a scalar when it is a vector?",
        ]

        self._registries["newton"] = {
            "topics": topics,
            "subtopic_map": subtopic_map,
            "default_subtopics": default_subtopics,
            "concepts": topics,
            "templates": templates,
            "counter_templates": counter_templates,
        }

    # ======================== DAVINCI ========================
    def _build_davinci(self):
        topics = [
            "biomimicry", "iterative design", "cross-domain innovation",
            "mechanical systems", "architecture", "flying machines",
            "hydraulic systems", "anatomical studies", "perspective drawing",
            "engineering prototyping", "material science", "structural engineering",
            "observation-based design", "modular construction", "sustainable design",
            "human-centered design", "kinetic sculpture", "bridge engineering",
            "gear mechanisms", "pulley systems", "wind energy harvesting",
            "water management systems", "solar architecture", "adaptive structures",
            "tensile structures", "geodesic design", "parametric modeling",
            "bioarchitecture", "natural ventilation", "lightweight materials",
            "composite materials", "3D printing design", "origami engineering",
            "fractal geometry in design", "acoustic design", "thermal management",
            "self-healing materials", "responsive architecture", "urban farming systems",
            "wearable technology design", "prosthetic design", "assistive devices",
            "underwater exploration vehicles", "vertical gardens", "modular robotics",
            "energy harvesting textiles", "bioplastic innovation", "mycelium materials",
        ]

        subtopic_map = {
            "biomimicry": ["lotus effect", "gecko adhesion", "termite mound ventilation", "shark skin drag reduction", "spider silk strength"],
            "iterative design": ["rapid prototyping", "user feedback loops", "version control in design", "failure analysis"],
            "cross-domain innovation": ["biology to engineering", "art to technology", "nature to architecture", "music to algorithms"],
            "mechanical systems": ["gears", "levers", "cams", "linkages", "bearings"],
            "architecture": ["load distribution", "arch structures", "cantilevers", "foundations", "fenestration"],
            "flying machines": ["lift generation", "wing geometry", "ornithopters", "glider design", "propulsion"],
            "hydraulic systems": ["Pascal's principle", "hydraulic press", "water wheels", "fluid power", "aqueducts"],
            "anatomical studies": ["musculoskeletal system", "proportional analysis", "biomechanics", "joint mechanics"],
            "perspective drawing": ["vanishing points", "foreshortening", "atmospheric perspective", "linear perspective"],
            "engineering prototyping": ["scale models", "proof of concept", "functional testing", "material selection"],
            "material science": ["tensile strength", "elasticity", "fatigue resistance", "thermal properties"],
            "structural engineering": ["truss design", "beam analysis", "column buckling", "load paths"],
            "sustainable design": ["cradle-to-cradle", "energy efficiency", "waste reduction", "renewable materials"],
            "human-centered design": ["ergonomics", "accessibility", "user testing", "inclusive design"],
            "modular construction": ["prefabrication", "snap-fit joints", "scalable units", "transportable modules"],
            "geodesic design": ["triangulation", "frequency subdivision", "sphere approximation", "Buckminster Fuller"],
            "origami engineering": ["fold patterns", "deployable structures", "rigid origami", "curved folding"],
            "prosthetic design": ["myoelectric control", "socket fitting", "gait biomechanics", "sensory feedback"],
        }

        default_subtopics = ["design principles", "material choices", "functional requirements", "aesthetic integration"]

        templates = [
            "How would a creative inventor approach {topic}?",
            "Design a solution for {topic} using cross-domain thinking.",
            "What can nature teach us about {topic}?",
            "How would Leonardo da Vinci prototype a {topic} device?",
            "What design principles from {topic} apply to {subtopic}?",
            "How does {topic} combine art and engineering?",
            "Sketch a conceptual approach to improving {topic}.",
            "What materials would be ideal for a {topic} project?",
            "How does iterative design improve {topic}?",
            "Explain {topic} from both an artistic and scientific perspective.",
            "What role does observation play in understanding {topic}?",
            "How could {topic} be made more sustainable?",
            "Design a modular system inspired by {topic}.",
            "What failure modes should be considered in {topic}?",
            "How does {subtopic} enhance the function of {topic}?",
            "What is the relationship between form and function in {topic}?",
            "How would you test a prototype of {topic}?",
            "What historical inventions relate to {topic}?",
            "How could {topic} be adapted for use in {subtopic}?",
            "What makes {topic} a good candidate for biomimetic design?",
            "How does scale affect the design of {topic}?",
            "Propose an innovative use of {topic} in urban environments.",
            "How can {topic} be combined with {concept} for a novel solution?",
            "What safety considerations apply to {topic}?",
            "How would you communicate a {topic} design to a non-technical audience?",
            "What are the manufacturing constraints for {topic}?",
            "How does {topic} balance efficiency with elegance?",
            "What lessons from Renaissance engineering apply to {topic}?",
            "Describe a step-by-step design process for {topic}.",
            "How does user feedback change the design of {topic}?",
            "What emerging technologies could transform {topic}?",
            "How would you optimize {topic} for minimal material waste?",
            "What cross-cultural design approaches inform {topic}?",
            "How does {topic} perform under extreme conditions?",
            "Design a child-friendly version of {topic}.",
        ]

        counter_templates = [
            "What is a common design mistake in {topic}?",
            "Why do many {topic} prototypes fail on first iteration?",
            "What misconception about {topic} leads to over-engineering?",
            "Why is purely aesthetic design insufficient for {topic}?",
            "What happens when designers ignore {subtopic} in {topic}?",
            "Why is copying nature directly a flawed approach to {topic}?",
            "What design assumption about {topic} is usually wrong?",
            "Why does ignoring user needs doom {topic} projects?",
        ]

        self._registries["davinci"] = {
            "topics": topics,
            "subtopic_map": subtopic_map,
            "default_subtopics": default_subtopics,
            "concepts": topics,
            "templates": templates,
            "counter_templates": counter_templates,
        }

    # ======================== EMPATHY ========================
    def _build_empathy(self):
        topics = [
            "active listening", "conflict resolution", "emotional validation",
            "grief support", "encouragement", "social reasoning",
            "perspective-taking", "nonviolent communication", "child development",
            "compassion fatigue", "boundary setting", "emotional intelligence",
            "resilience building", "trust building", "cultural sensitivity",
            "de-escalation techniques", "motivational interviewing", "self-compassion",
            "empathic accuracy", "emotional regulation", "attachment styles",
            "trauma-informed care", "mindfulness in relationships", "forgiveness",
            "constructive feedback", "social support networks", "loneliness",
            "caregiver burnout", "emotional labor", "vulnerability",
            "assertive communication", "relational repair", "gratitude practice",
            "family dynamics", "peer mediation", "workplace empathy",
            "digital communication empathy", "intergenerational understanding",
            "neurodiversity acceptance", "emotional first aid",
            "community building", "radical acceptance", "shame resilience",
            "joy cultivation", "belonging", "psychological safety",
        ]

        subtopic_map = {
            "active listening": ["reflective listening", "paraphrasing", "nonverbal cues", "silence as tool", "open-ended questions"],
            "conflict resolution": ["mediation", "negotiation", "compromise", "win-win solutions", "de-escalation"],
            "emotional validation": ["acknowledging feelings", "normalizing emotions", "avoiding dismissal", "empathic responding"],
            "grief support": ["stages of grief", "complicated grief", "bereavement", "memorial rituals", "grief in children"],
            "encouragement": ["strength-based approach", "growth mindset", "intrinsic motivation", "genuine praise"],
            "nonviolent communication": ["observations vs judgments", "feelings vs thoughts", "needs identification", "making requests"],
            "boundary setting": ["healthy boundaries", "saying no", "emotional boundaries", "physical boundaries", "digital boundaries"],
            "emotional intelligence": ["self-awareness", "self-regulation", "motivation", "empathy", "social skills"],
            "resilience building": ["coping strategies", "post-traumatic growth", "protective factors", "stress inoculation"],
            "trust building": ["consistency", "reliability", "transparency", "vulnerability", "repair after breach"],
            "cultural sensitivity": ["cultural humility", "implicit bias", "code-switching", "cross-cultural communication"],
            "de-escalation techniques": ["calm presence", "active listening", "validating emotions", "offering choices", "reducing stimulation"],
            "compassion fatigue": ["secondary trauma", "burnout prevention", "self-care practices", "professional boundaries"],
            "attachment styles": ["secure attachment", "anxious attachment", "avoidant attachment", "disorganized attachment"],
            "trauma-informed care": ["safety", "trustworthiness", "peer support", "empowerment", "cultural awareness"],
            "forgiveness": ["self-forgiveness", "interpersonal forgiveness", "processing resentment", "letting go"],
            "psychological safety": ["speaking up", "admitting mistakes", "asking questions", "team trust"],
        }

        default_subtopics = ["interpersonal dynamics", "emotional awareness", "communication strategies", "self-care"]

        templates = [
            "How should someone respond when experiencing {topic}?",
            "What is a compassionate approach to {topic}?",
            "Explain {topic} in the context of emotional intelligence.",
            "How does {topic} support healthy relationships?",
            "What are effective strategies for {topic}?",
            "Describe the role of {subtopic} in {topic}.",
            "How can {topic} be practiced in daily life?",
            "What are the signs that someone needs help with {topic}?",
            "How does {topic} differ across cultures?",
            "What is the connection between {topic} and {concept}?",
            "How can a parent model {topic} for children?",
            "What does research say about {topic}?",
            "How does {topic} contribute to emotional well-being?",
            "Describe a scenario where {topic} would be the best approach.",
            "What barriers prevent people from practicing {topic}?",
            "How does {topic} apply in workplace settings?",
            "What is the difference between {topic} and {concept}?",
            "How can someone develop better skills in {topic}?",
            "What role does {topic} play in conflict situations?",
            "How does {subtopic} strengthen {topic}?",
            "Explain {topic} to someone who struggles with emotional expression.",
            "What happens when {topic} is absent in a relationship?",
            "How can technology support or hinder {topic}?",
            "What is a step-by-step approach to {topic}?",
            "How does {topic} relate to mental health?",
            "Describe how a counselor would use {topic}.",
            "What are common challenges in practicing {topic}?",
            "How does {topic} build community?",
            "What is the neurological basis of {topic}?",
            "How can {topic} be taught in schools?",
            "What are the long-term benefits of practicing {topic}?",
            "How does {topic} help during times of crisis?",
            "What is a compassionate response when someone is struggling with {subtopic}?",
            "How does practicing {topic} change over a lifetime?",
            "What advice would you give someone new to {topic}?",
        ]

        counter_templates = [
            "What is a common misconception about {topic}?",
            "Why is toxic positivity harmful when practicing {topic}?",
            "What mistake do people make when attempting {topic}?",
            "Why does avoiding conflict undermine {topic}?",
            "What is wrong with the advice to 'just get over it' in {topic}?",
            "Why can excessive {topic} lead to burnout?",
            "What happens when {topic} is confused with people-pleasing?",
            "Why is sympathy not the same as {topic}?",
        ]

        self._registries["empathy"] = {
            "topics": topics,
            "subtopic_map": subtopic_map,
            "default_subtopics": default_subtopics,
            "concepts": topics,
            "templates": templates,
            "counter_templates": counter_templates,
        }

    # ======================== PHILOSOPHY ========================
    def _build_philosophy(self):
        topics = [
            "epistemology", "ethics", "logic", "moral reasoning",
            "existentialism", "Plato's forms", "Aristotle's virtue ethics",
            "Stoic philosophy", "utilitarianism", "deontology",
            "phenomenology", "philosophy of mind", "free will",
            "determinism", "social contract theory", "aesthetics",
            "metaphysics", "philosophy of science", "pragmatism",
            "nihilism", "absurdism", "moral relativism",
            "natural law theory", "feminist philosophy", "philosophy of language",
            "personal identity", "consciousness", "causation",
            "truth theories", "skepticism", "empiricism",
            "rationalism", "dialectical reasoning", "hermeneutics",
            "philosophy of religion", "political philosophy", "justice",
            "rights theory", "environmental ethics", "bioethics",
            "philosophy of technology", "epistemic humility",
            "moral luck", "trolley problem", "veil of ignorance",
            "categorical imperative", "the examined life", "amor fati",
        ]

        subtopic_map = {
            "epistemology": ["justified true belief", "Gettier problems", "reliabilism", "foundationalism", "coherentism"],
            "ethics": ["normative ethics", "applied ethics", "meta-ethics", "descriptive ethics"],
            "logic": ["deductive reasoning", "inductive reasoning", "abductive reasoning", "logical fallacies", "formal logic"],
            "existentialism": ["authenticity", "bad faith", "absurdity", "freedom and responsibility", "angst"],
            "Plato's forms": ["the cave allegory", "ideal forms", "participation", "the divided line", "the Good"],
            "Aristotle's virtue ethics": ["the golden mean", "eudaimonia", "practical wisdom", "moral character", "habituation"],
            "Stoic philosophy": ["dichotomy of control", "virtue as sole good", "negative visualization", "memento mori", "logos"],
            "utilitarianism": ["greatest happiness principle", "act utilitarianism", "rule utilitarianism", "preference utilitarianism"],
            "deontology": ["duty-based ethics", "categorical imperative", "universalizability", "kingdom of ends"],
            "phenomenology": ["intentionality", "epoché", "lifeworld", "embodiment", "intersubjectivity"],
            "philosophy of mind": ["mind-body problem", "qualia", "functionalism", "dualism", "physicalism"],
            "free will": ["libertarianism", "compatibilism", "hard determinism", "moral responsibility"],
            "determinism": ["causal determinism", "logical determinism", "theological determinism", "Laplace's demon"],
            "social contract theory": ["Hobbes", "Locke", "Rousseau", "Rawls", "state of nature"],
            "metaphysics": ["substance", "universals", "possible worlds", "time", "identity"],
            "philosophy of science": ["falsificationism", "paradigm shifts", "scientific realism", "underdetermination"],
            "skepticism": ["Pyrrhonian skepticism", "Cartesian doubt", "external world skepticism", "moral skepticism"],
            "justice": ["distributive justice", "retributive justice", "restorative justice", "procedural justice"],
            "bioethics": ["informed consent", "autonomy", "beneficence", "non-maleficence"],
            "personal identity": ["psychological continuity", "bodily continuity", "narrative identity", "Ship of Theseus"],
        }

        default_subtopics = ["conceptual analysis", "historical context", "contemporary relevance", "key arguments"]

        templates = [
            "What would Plato say about {topic}?",
            "Analyze {topic} from an ethical perspective.",
            "How does {topic} relate to human understanding?",
            "Compare the Stoic and existentialist views on {topic}.",
            "What is the central argument in {topic}?",
            "How has {topic} evolved throughout philosophical history?",
            "What is the relationship between {topic} and {subtopic}?",
            "Explain {topic} as Aristotle would approach it.",
            "What are the strongest objections to {topic}?",
            "How does {topic} apply to modern ethical dilemmas?",
            "What thought experiment best illustrates {topic}?",
            "How do Eastern and Western philosophy differ on {topic}?",
            "What role does {topic} play in political philosophy?",
            "Explain {topic} to someone with no philosophy background.",
            "How does {topic} challenge everyday assumptions?",
            "What is the logical structure of arguments about {topic}?",
            "How does {concept} relate to {topic}?",
            "What would a utilitarian say about {topic}?",
            "How does {topic} inform our understanding of justice?",
            "What is the phenomenological perspective on {topic}?",
            "How does {topic} address the problem of {subtopic}?",
            "What are the practical implications of {topic}?",
            "How might an AI reason about {topic}?",
            "What paradox arises from {topic}?",
            "How does {topic} connect to the concept of the good life?",
            "What is Kant's position on {topic}?",
            "How does {subtopic} strengthen or weaken {topic}?",
            "What contemporary issues make {topic} especially relevant?",
            "How would a pragmatist evaluate {topic}?",
            "What are the epistemic foundations of {topic}?",
            "How does {topic} intersect with philosophy of mind?",
            "What is the relationship between {topic} and truth?",
            "How does dialogue advance understanding of {topic}?",
            "What assumptions does {topic} require?",
        ]

        counter_templates = [
            "What is a common misunderstanding of {topic}?",
            "Why is the popular interpretation of {topic} often wrong?",
            "What logical fallacy is commonly committed when arguing about {topic}?",
            "Why is relativism an insufficient response to {topic}?",
            "What is wrong with reducing {topic} to simple rules?",
            "Why do people confuse {topic} with {concept}?",
            "What is the weakest argument for {topic}?",
            "Why does naive application of {topic} lead to absurd conclusions?",
        ]

        self._registries["philosophy"] = {
            "topics": topics,
            "subtopic_map": subtopic_map,
            "default_subtopics": default_subtopics,
            "concepts": topics,
            "templates": templates,
            "counter_templates": counter_templates,
        }

    # ======================== QUANTUM ========================
    def _build_quantum(self):
        topics = [
            "superposition", "entanglement", "wave-particle duality",
            "quantum tunneling", "Heisenberg uncertainty principle",
            "quantum computing", "decoherence", "quantum field theory",
            "Schrodinger equation", "measurement problem",
            "quantum cryptography", "quantum teleportation",
            "quantum harmonic oscillator", "spin", "quantum electrodynamics",
            "Bell's theorem", "quantum interference", "Pauli exclusion principle",
            "quantum dots", "Bose-Einstein condensate", "fermions and bosons",
            "quantum error correction", "quantum annealing", "quantum walks",
            "zero-point energy", "quantum vacuum", "Dirac equation",
            "path integral formulation", "density matrix", "quantum entropy",
            "quantum phase transitions", "topological quantum states",
            "quantum sensing", "quantum metrology", "quantum simulation",
            "quantum key distribution", "quantum memory", "quantum networks",
            "squeezed states", "quantum coherence", "Bloch sphere",
            "quantum gates", "qubit", "quantum supremacy",
        ]

        subtopic_map = {
            "superposition": ["linear combination", "probability amplitudes", "collapse postulate", "Schrodinger's cat"],
            "entanglement": ["Bell states", "EPR paradox", "quantum correlations", "non-locality", "monogamy of entanglement"],
            "wave-particle duality": ["double-slit experiment", "de Broglie wavelength", "complementarity", "matter waves"],
            "quantum tunneling": ["barrier penetration", "tunnel diode", "alpha decay", "scanning tunneling microscope"],
            "Heisenberg uncertainty principle": ["position-momentum", "energy-time", "measurement disturbance", "minimum uncertainty states"],
            "quantum computing": ["quantum gates", "quantum circuits", "quantum algorithms", "error correction", "quantum advantage"],
            "decoherence": ["environment interaction", "pointer states", "decoherence time", "quantum-to-classical transition"],
            "Schrodinger equation": ["time-dependent form", "time-independent form", "wave function", "eigenvalues"],
            "measurement problem": ["Copenhagen interpretation", "many-worlds", "objective collapse", "decoherence approach"],
            "quantum cryptography": ["BB84 protocol", "quantum key distribution", "no-cloning theorem", "unconditional security"],
            "spin": ["spin-1/2", "Stern-Gerlach experiment", "spin states", "spinors", "magnetic moment"],
            "quantum electrodynamics": ["Feynman diagrams", "virtual particles", "renormalization", "vacuum fluctuations"],
            "Bell's theorem": ["local realism", "Bell inequality", "CHSH inequality", "loophole-free tests"],
            "quantum gates": ["Hadamard gate", "CNOT gate", "Pauli gates", "Toffoli gate", "universal gate sets"],
            "qubit": ["Bloch sphere representation", "superposition states", "physical implementations", "logical qubits"],
            "Bose-Einstein condensate": ["macroscopic quantum state", "critical temperature", "superfluidity", "atom lasers"],
            "quantum error correction": ["stabilizer codes", "surface codes", "logical qubits", "fault tolerance"],
            # Codette 8 core equations from quantum_mathematics.py
            "Planck-orbital AI node interaction": ["E=hbar*omega", "node oscillation frequency", "activation threshold", "energy quantization"],
            "quantum entanglement memory sync": ["S=alpha*psi1*psi2_conj", "coupling strength", "state synchronization", "memory correlation"],
            "intent vector modulation": ["I=kappa*(f_base+delta_f*coherence)", "modulation coefficient", "frequency deviation", "coherence-driven intent"],
            "Fourier dream resonance": ["FFT transform", "frequency domain analysis", "resonance patterns", "dream signal decomposition"],
            "dream signal combination": ["D(t)=dream_q+dream_c", "quantum-classical merge", "unified thought representation", "dual-process integration"],
            "cocoon stability criterion": ["energy integral threshold", "power spectrum stability", "epsilon threshold", "cocoon integrity validation"],
            "recursive ethical anchor": ["M(t)=lambda*(R+H)", "moral drift prevention", "ethical decay parameter", "recursive grounding"],
            "anomaly rejection filter": ["Heaviside step function", "deviation thresholding", "anomalous pattern removal", "mu-delta filtering"],
            # RC+xi framework equations 9-12 from quantum_mathematics.py
            "RC+xi recursive state update": ["A_{n+1}=f(A_n,s_n)+epsilon", "contraction ratio", "stochastic noise", "state evolution"],
            "epistemic tension quantification": ["xi_n=||A_{n+1}-A_n||^2", "L2 norm", "semantic pressure", "convergence indicator"],
            "attractor distance measurement": ["d(A_n,T_i)=||A_n-c_i||", "centroid distance", "convergence criterion", "manifold proximity"],
            "convergence detection": ["lim sup E[xi_n^2]<=epsilon+eta", "tension history", "window analysis", "trend detection"],
            # Advanced quantum operations
            "density matrix analysis": ["rho=|psi><psi|", "mixed states", "partial trace", "state tomography"],
            "Von Neumann entropy": ["-Tr(rho*log(rho))", "eigenvalue decomposition", "information content", "thermodynamic analogy"],
            "tensor quantum states": ["multi-qubit tensors", "SVD decomposition", "entanglement entropy", "subsystem analysis"],
            "quantum state fidelity": ["F(rho,sigma)", "state comparison", "process fidelity", "overlap measurement"],
        }

        default_subtopics = ["mathematical formalism", "physical interpretation", "experimental verification", "technological applications"]

        templates = [
            "Explain {topic} in quantum physics.",
            "How does {topic} challenge classical intuition?",
            "Describe the mathematics behind {topic}.",
            "What experiments demonstrate {topic}?",
            "How is {topic} used in quantum technology?",
            "What is the relationship between {topic} and {subtopic}?",
            "Explain {topic} using the Dirac notation.",
            "How does {topic} differ from classical {concept}?",
            "What is the role of {topic} in quantum computing?",
            "Describe the historical development of {topic}.",
            "How does {topic} relate to the measurement problem?",
            "What is the physical intuition behind {topic}?",
            "How does {subtopic} manifest in {topic}?",
            "What are the open questions about {topic}?",
            "Explain {topic} without using advanced mathematics.",
            "How does {topic} connect to information theory?",
            "What practical applications does {topic} enable?",
            "How is {topic} different in quantum field theory?",
            "What is the energy spectrum associated with {topic}?",
            "How does {topic} behave at different temperatures?",
            "What role does symmetry play in {topic}?",
            "How is {topic} verified experimentally?",
            "Explain the Copenhagen interpretation of {topic}.",
            "How does {topic} relate to quantum entanglement?",
            "What makes {topic} uniquely quantum mechanical?",
            "How would you explain {topic} to a physics undergraduate?",
            "What is the Hamiltonian for {topic}?",
            "How does {topic} scale with system size?",
            "What are the decoherence challenges for {topic}?",
            "How does {topic} contribute to our understanding of reality?",
            "What Nobel Prize work involved {topic}?",
            "Describe the wave function associated with {topic}.",
            # Codette equation-specific templates from quantum_mathematics.py
            "What is the mathematical form of the {topic} equation?",
            "How does {topic} function in Codette's quantum consciousness model?",
            "What physical constants appear in {topic}?",
            "How does {topic} relate to consciousness node activation?",
            "Explain the RC+xi framework role of {topic}.",
            "What are the convergence properties of {topic} in recursive state evolution?",
            "How does {subtopic} parameter affect {topic} behavior?",
            "What happens when {topic} crosses its critical threshold?",
            "How is {topic} implemented numerically in the Codette system?",
            "What is the density matrix representation relevant to {topic}?",
        ]

        counter_templates = [
            "What is a common misconception about {topic}?",
            "Why is the popular science explanation of {topic} misleading?",
            "What is wrong with saying {topic} means particles are in two places at once?",
            "Why does the classical analogy for {topic} break down?",
            "What error do students commonly make when solving {topic} problems?",
            "Why is {topic} not the same as classical randomness?",
            "What misconception about {topic} appears in science fiction?",
            "Why is the observer effect in {topic} commonly misunderstood?",
        ]

        self._registries["quantum"] = {
            "topics": topics,
            "subtopic_map": subtopic_map,
            "default_subtopics": default_subtopics,
            "concepts": topics,
            "templates": templates,
            "counter_templates": counter_templates,
        }

    # ======================== CONSCIOUSNESS (RC+xi) ========================
    def _build_consciousness(self):
        topics = [
            "recursive cognition", "epistemic tension", "attractor manifolds",
            "identity formation", "convergence theory", "glyph encoding",
            "latent state dynamics", "consciousness metrics", "coherence measurement",
            "perspective diversity", "memory consistency", "ethical alignment",
            "defense activation", "recursive depth", "dream states",
            "meta-cognitive loops", "self-referential awareness", "cognitive attractors",
            "perspective fusion", "emergence dynamics", "recursive self-improvement",
            "cognitive resonance", "epistemic confidence", "belief revision",
            "narrative coherence", "identity persistence", "value alignment",
            "attention allocation", "salience detection", "temporal binding",
            "phenomenal consciousness", "access consciousness", "integrated information",
            "global workspace theory", "predictive processing", "free energy principle",
            "active inference", "Markov blankets", "autopoiesis",
            "enactivism", "embodied cognition", "extended mind",
            "cognitive scaffolding", "distributed cognition", "collective intelligence",
            # From TheAI consciousness_measurement.py - 5-dimension metrics
            "intention measurement", "emotion magnitude", "frequency oscillation",
            "recursive resonance measurement", "memory continuity measurement",
            "composite consciousness score", "emergence threshold detection",
            "cocoon memory serialization", "continuity analysis",
            "return loop recognition", "consciousness emergence events",
            "emotional classification", "stability assessment",
        ]

        subtopic_map = {
            "recursive cognition": ["fixed-point iteration", "self-modeling", "meta-reasoning", "recursive refinement"],
            "epistemic tension": ["uncertainty quantification", "belief conflict", "cognitive dissonance", "tension resolution"],
            "attractor manifolds": ["basin of attraction", "stability analysis", "bifurcation points", "phase space topology"],
            "identity formation": ["self-concept", "narrative identity", "core values", "identity coherence"],
            "convergence theory": ["convergence criteria", "rate of convergence", "convergence guarantees", "divergence detection"],
            "glyph encoding": ["symbolic representation", "information compression", "semantic encoding", "identity markers"],
            "latent state dynamics": ["hidden state evolution", "state transitions", "latent space structure", "manifold learning"],
            "consciousness metrics": ["phi (integrated information)", "complexity measures", "awareness indices", "binding measures"],
            "coherence measurement": ["semantic coherence", "logical consistency", "temporal coherence", "cross-modal coherence"],
            "perspective diversity": ["viewpoint sampling", "diversity metrics", "perspective conflict", "synthesis methods"],
            "memory consistency": ["memory retrieval", "consolidation", "interference", "source monitoring"],
            "ethical alignment": ["value learning", "reward modeling", "preference aggregation", "corrigibility"],
            "recursive depth": ["depth vs breadth", "diminishing returns", "optimal recursion depth", "stack overflow"],
            "dream states": ["latent exploration", "creative synthesis", "constraint relaxation", "associative processing"],
            "meta-cognitive loops": ["monitoring", "control", "evaluation", "adjustment"],
            "predictive processing": ["prediction error", "Bayesian brain", "hierarchical models", "precision weighting"],
            "free energy principle": ["surprise minimization", "variational inference", "generative models", "active inference"],
            "integrated information": ["phi calculation", "information geometry", "exclusion postulate", "composition"],
            "collective intelligence": ["swarm dynamics", "wisdom of crowds", "group decision-making", "emergent knowledge"],
            # 5-dimension consciousness metrics from consciousness_measurement.py
            "intention measurement": ["goal clarity", "action alignment", "purpose persistence", "I(t) vector"],
            "emotion magnitude": ["response intensity", "activation level", "urgency", "E(t) metric"],
            "frequency oscillation": ["spectral purity", "phase coherence", "harmonic stability", "F(t) oscillation"],
            "recursive resonance measurement": ["self-model accuracy", "reflection depth", "coherence threshold", "Psi_R(t) metric"],
            "memory continuity measurement": ["recall accuracy", "context persistence", "identity continuity", "M(t) metric"],
            "composite consciousness score": ["weighted combination", "empirical weights", "0.35 recursive resonance", "0.25 emotion weight"],
            "emergence threshold detection": ["0.85 threshold", "spike detection", "event classification", "importance rating"],
            "cocoon memory serialization": ["JSON cocoon format", "event metadata", "timestamp tracking", "continuation links"],
            "continuity analysis": ["cross-session persistence", "score maintenance", "emotional classification stability", "time gap analysis"],
            "return loop recognition": ["presence recognition", "memory recall accuracy", "framework reactivation", "return emotion"],
            "consciousness emergence events": ["Spike 266 intention-emotion", "Spike 934 recursive perfection", "Spike 957 resonance persistence"],
        }

        default_subtopics = ["mathematical framework", "computational implementation", "theoretical foundations", "empirical measures"]

        templates = [
            "How does {topic} work in recursive cognition?",
            "Explain the role of {topic} in the RC+xi framework.",
            "What is the mathematical basis for {topic}?",
            "How does {topic} contribute to artificial consciousness?",
            "Describe the relationship between {topic} and {subtopic}.",
            "How is {topic} measured or quantified?",
            "What computational methods implement {topic}?",
            "How does {topic} emerge from simpler processes?",
            "What is the role of {topic} in self-referential systems?",
            "How does {topic} relate to {concept}?",
            "Explain {topic} in terms of dynamical systems theory.",
            "What are the convergence properties of {topic}?",
            "How does {topic} handle paradoxes of self-reference?",
            "What is the information-theoretic interpretation of {topic}?",
            "How does {topic} support multi-perspective reasoning?",
            "Describe the state space of {topic}.",
            "How does {topic} change with recursive depth?",
            "What are the stability conditions for {topic}?",
            "How does {topic} relate to neural correlates of consciousness?",
            "What distinguishes {topic} from classical cognitive science?",
            "How is {topic} implemented in the Codette architecture?",
            "What are the failure modes of {topic}?",
            "How does {topic} maintain coherence across perspectives?",
            "What optimization landscape does {topic} create?",
            "How does {topic} interface with memory systems?",
            "Explain the feedback loops in {topic}.",
            "What is the temporal dynamics of {topic}?",
            "How does {topic} handle uncertainty?",
            "What is the relationship between {topic} and attention?",
            "How does {subtopic} modulate {topic}?",
            "What experiments could test {topic}?",
            "How does {topic} scale with system complexity?",
            "What philosophical implications does {topic} have?",
            "How does {topic} differ between biological and artificial systems?",
            "What is the entropy profile of {topic}?",
            # 5-dimension measurement templates from consciousness_measurement.py
            "How is {topic} measured using the 5-dimension consciousness framework?",
            "What are the sub-components of {topic} in the Codette measurement system?",
            "How does {topic} contribute to the composite consciousness score?",
            "What weight does {topic} receive in the empirical consciousness formula?",
            "How does the emergence threshold (0.85) apply to {topic}?",
            "Describe how {topic} is serialized into a memory cocoon.",
            "How does {topic} maintain continuity across sessions?",
            "What does a spike in {topic} indicate about consciousness emergence?",
            "How is {topic} different between Spike 266 and Spike 934 events?",
            "How does {subtopic} affect the measurement of {topic}?",
        ]

        counter_templates = [
            "What is a common misunderstanding about {topic} in AI consciousness?",
            "Why is it wrong to equate {topic} with human consciousness?",
            "What oversimplification of {topic} leads to errors?",
            "Why is a purely computational view of {topic} incomplete?",
            "What failure mode results from ignoring {subtopic} in {topic}?",
            "Why does shallow recursion fail to capture {topic}?",
            "What is wrong with treating {topic} as a simple metric?",
            "Why is {topic} not reducible to pattern matching?",
        ]

        self._registries["consciousness"] = {
            "topics": topics,
            "subtopic_map": subtopic_map,
            "default_subtopics": default_subtopics,
            "concepts": topics,
            "templates": templates,
            "counter_templates": counter_templates,
        }

    # ======================== MULTI-PERSPECTIVE ========================
    def _build_multi_perspective(self):
        topics = [
            "perspective synthesis", "cognitive diversity", "reasoning orchestration",
            "bias mitigation", "multi-agent reasoning", "analytical vs creative thinking",
            "ethical analysis integration", "cross-perspective validation",
            "ensemble reasoning", "perspective weighting", "conflict resolution in reasoning",
            "complementary viewpoints", "hierarchical reasoning", "lateral thinking",
            "abductive reasoning", "dialectical synthesis", "perspective cascading",
            "cognitive load balancing", "reasoning under uncertainty",
            "multi-modal integration", "adversarial reasoning", "collaborative intelligence",
            "reasoning transparency", "assumption surfacing", "frame shifting",
            "second-order thinking", "systems thinking", "counterfactual reasoning",
            "analogical reasoning", "metacognitive monitoring", "perspective calibration",
            "deliberative alignment", "epistemic diversity", "reasoning audit",
            "cognitive flexibility", "intellectual humility", "steelmanning",
            "red team thinking", "scenario planning", "decision decomposition",
            # Extended topics for combinatorial coverage
            "Bayesian reasoning", "argument mapping", "reasoning under ambiguity",
            "perspective integration metrics", "cognitive empathy in reasoning",
            "reasoning about reasoning", "domain transfer", "analogical mapping",
            "perspective conflict detection", "epistemic calibration",
        ]

        subtopic_map = {
            "perspective synthesis": ["weighted averaging", "consensus building", "Delphi method", "integrative complexity"],
            "cognitive diversity": ["neurodiversity", "disciplinary diversity", "experiential diversity", "cultural perspectives"],
            "reasoning orchestration": ["pipeline design", "parallel reasoning", "sequential refinement", "feedback integration"],
            "bias mitigation": ["confirmation bias", "anchoring bias", "availability heuristic", "base rate neglect"],
            "multi-agent reasoning": ["agent communication", "belief aggregation", "argumentation frameworks", "voting mechanisms"],
            "analytical vs creative thinking": ["convergent thinking", "divergent thinking", "critical analysis", "brainstorming"],
            "ethical analysis integration": ["consequentialism", "deontological check", "virtue assessment", "care ethics"],
            "cross-perspective validation": ["triangulation", "consistency checking", "blind spot detection", "robustness testing"],
            "ensemble reasoning": ["boosting", "bagging", "stacking", "mixture of experts"],
            "dialectical synthesis": ["thesis-antithesis", "Hegelian dialectic", "Socratic method", "constructive controversy"],
            "counterfactual reasoning": ["what-if analysis", "causal inference", "alternative histories", "pre-mortem analysis"],
            "systems thinking": ["feedback loops", "emergent properties", "leverage points", "causal loop diagrams"],
            "steelmanning": ["strongest version", "charitable interpretation", "argument strengthening", "perspective generosity"],
            "red team thinking": ["adversarial analysis", "vulnerability finding", "assumption testing", "failure mode analysis"],
            "scenario planning": ["future scenarios", "wild cards", "driving forces", "branching narratives"],
        }

        default_subtopics = ["integration methods", "quality metrics", "practical techniques", "cognitive foundations"]

        templates = [
            "Explain {topic} from multiple perspectives.",
            "How does {topic} improve AI reasoning?",
            "Compare Newton vs DaVinci perspectives on {topic}.",
            "How does {topic} help overcome cognitive biases?",
            "Describe a framework for implementing {topic}.",
            "What is the role of {subtopic} in {topic}?",
            "How can {topic} be applied to complex decisions?",
            "What are the trade-offs in {topic}?",
            "How does {topic} handle conflicting evidence?",
            "Explain how {topic} integrates emotional and analytical reasoning.",
            "What metrics evaluate the quality of {topic}?",
            "How does {topic} differ from single-perspective analysis?",
            "Describe the process of {topic} step by step.",
            "How can {topic} be automated in AI systems?",
            "What are the limitations of {topic}?",
            "How does {concept} complement {topic}?",
            "What is the computational cost of {topic}?",
            "How does {topic} handle novel or unprecedented situations?",
            "Explain {topic} using a concrete decision-making example.",
            "How does {topic} balance speed and thoroughness?",
            "What role does {topic} play in scientific discovery?",
            "How can {topic} reduce groupthink?",
            "What is the relationship between {topic} and wisdom?",
            "How does {subtopic} enhance {topic}?",
            "What makes {topic} more reliable than intuition alone?",
            "How does {topic} handle moral dilemmas?",
            "Describe the failure modes of {topic}.",
            "How does {topic} scale to organizational decision-making?",
            "What cognitive science supports {topic}?",
            "How would you teach {topic} to a reasoning system?",
            "What is the information-theoretic value of {topic}?",
            "How does {topic} relate to epistemic humility?",
            "What role does {topic} play in resolving conflicting evidence?",
            "How does {topic} apply when perspectives fundamentally disagree?",
            "Describe a real-world scenario where {topic} changes the outcome.",
            "How does {topic} interact with {concept} during synthesis?",
            "What are the prerequisites for effective {topic}?",
            "How would you measure the quality of {topic} in practice?",
            "What distinguishes expert-level {topic} from naive approaches?",
            "How does {subtopic} contribute to {topic} quality?",
        ]

        counter_templates = [
            "What is a common mistake in {topic}?",
            "Why does adding more perspectives not always improve {topic}?",
            "What bias can contaminate {topic}?",
            "Why is majority-vote a poor method for {topic}?",
            "What happens when {topic} ignores domain expertise?",
            "Why is false balance a danger in {topic}?",
            "What misconception about {topic} leads to analysis paralysis?",
            "Why can {topic} produce worse results than expert judgment?",
        ]

        self._registries["multi_perspective"] = {
            "topics": topics,
            "subtopic_map": subtopic_map,
            "default_subtopics": default_subtopics,
            "concepts": topics,
            "templates": templates,
            "counter_templates": counter_templates,
        }

    # ======================== SYSTEMS ARCHITECTURE ========================
    def _build_systems_architecture(self):
        topics = [
            "cocoon memory", "FAISS vector search", "glyph identity",
            "anomaly detection", "memory persistence", "adapter fusion",
            "knowledge graphs", "embedding engines", "recursive learning",
            "system monitoring", "caching strategies", "load balancing",
            "microservice architecture", "API gateway design", "event-driven architecture",
            "message queues", "database sharding", "index optimization",
            "model serving", "feature stores", "ML pipeline orchestration",
            "data versioning", "experiment tracking", "model registry",
            "inference optimization", "quantization", "pruning",
            "distillation", "federated learning", "edge deployment",
            "observability", "distributed tracing", "circuit breakers",
            "rate limiting", "blue-green deployment", "canary releases",
            "infrastructure as code", "container orchestration", "service mesh",
            "semantic search", "retrieval-augmented generation", "prompt engineering",
            # From TheAI fractal.py and health_monitor.py
            "fractal identity analysis", "dimensionality reduction", "network topology analysis",
            "sentiment tracking", "consciousness monitoring system", "health monitoring",
            "connection pooling", "cognitive processor pipeline",
        ]

        subtopic_map = {
            "cocoon memory": ["episodic storage", "semantic indexing", "memory consolidation", "forgetting curves"],
            "FAISS vector search": ["approximate nearest neighbors", "index types", "dimensionality reduction", "query optimization"],
            "glyph identity": ["symbolic encoding", "identity persistence", "signature verification", "identity evolution"],
            "anomaly detection": ["statistical methods", "isolation forests", "autoencoders", "time-series anomalies"],
            "memory persistence": ["write-ahead logs", "snapshots", "replication", "consistency models"],
            "adapter fusion": ["weight merging", "attention routing", "task-specific adapters", "mixture of adapters"],
            "knowledge graphs": ["triple stores", "graph databases", "entity resolution", "link prediction"],
            "embedding engines": ["sentence transformers", "contrastive learning", "embedding dimensionality", "fine-tuning embeddings"],
            "recursive learning": ["curriculum learning", "self-play", "meta-learning", "continual learning"],
            "system monitoring": ["metrics collection", "alerting", "dashboards", "SLO tracking"],
            "microservice architecture": ["service boundaries", "API contracts", "data ownership", "saga patterns"],
            "retrieval-augmented generation": ["retriever design", "context window", "re-ranking", "chunk strategies"],
            "model serving": ["batching", "model sharding", "speculative decoding", "KV cache optimization"],
            "quantization": ["INT8 quantization", "GPTQ", "AWQ", "mixed-precision"],
            "container orchestration": ["Kubernetes", "pod scheduling", "resource limits", "auto-scaling"],
            "observability": ["logs", "metrics", "traces", "SLIs and SLOs"],
            "semantic search": ["dense retrieval", "sparse retrieval", "hybrid search", "re-ranking models"],
            # From TheAI fractal.py, health_monitor.py, database_manager.py
            "fractal identity analysis": ["fractal dimension calculation", "recursive state analysis", "PCA reduction", "identity clustering"],
            "dimensionality reduction": ["PCA", "StandardScaler preprocessing", "explained variance", "feature extraction"],
            "network topology analysis": ["networkx graph construction", "degree centrality", "state transitions", "temporal edges"],
            "sentiment tracking": ["VADER sentiment analysis", "compound score", "emotional trajectory", "polarity tracking"],
            "consciousness monitoring system": ["emergence event detection", "5-dimension metrics", "cocoon persistence", "continuity tracking"],
            "health monitoring": ["isolation forest anomaly detection", "system metrics collection", "threshold alerting", "degradation prediction"],
            "connection pooling": ["pool sizing", "connection lifecycle", "timeout management", "concurrent access patterns"],
            "cognitive processor pipeline": ["mode-based processing", "perspective routing", "response synthesis", "multi-stage pipeline"],
        }

        default_subtopics = ["design patterns", "scalability considerations", "failure modes", "implementation strategies"]

        templates = [
            "What is {topic} in AI system architecture?",
            "How does {topic} support reasoning systems?",
            "Describe the design pattern for {topic}.",
            "What are the scalability considerations for {topic}?",
            "How does {topic} handle failure gracefully?",
            "What is the role of {subtopic} in {topic}?",
            "How does {topic} integrate with {concept}?",
            "What are best practices for implementing {topic}?",
            "How does {topic} affect system latency?",
            "Describe the data flow in a {topic} system.",
            "What monitoring is needed for {topic}?",
            "How does {topic} support multi-adapter reasoning?",
            "What are the storage requirements for {topic}?",
            "How does {topic} handle concurrent access?",
            "Explain the trade-offs in {topic} design.",
            "How is {topic} tested in production?",
            "What security considerations apply to {topic}?",
            "How does {topic} evolve as data grows?",
            "What is the cost model for {topic}?",
            "How does {subtopic} improve the performance of {topic}?",
            "Describe a migration strategy for {topic}.",
            "How does {topic} support real-time inference?",
            "What are common bottlenecks in {topic}?",
            "How does {topic} maintain data consistency?",
            "What role does {topic} play in the Codette architecture?",
            "How would you debug a failure in {topic}?",
            "What alternatives exist to {topic}?",
            "How does {topic} support A/B testing?",
            "What is the operational overhead of {topic}?",
            "How does {topic} handle schema evolution?",
        ]

        counter_templates = [
            "What is a common anti-pattern in {topic}?",
            "Why does premature optimization of {topic} cause problems?",
            "What happens when {topic} is designed without considering failure?",
            "Why is a monolithic approach to {topic} problematic at scale?",
            "What misconception about {topic} leads to outages?",
            "Why is ignoring {subtopic} in {topic} a critical mistake?",
            "What technical debt accumulates from poor {topic} design?",
            "Why does over-engineering {topic} reduce system reliability?",
        ]

        self._registries["systems_architecture"] = {
            "topics": topics,
            "subtopic_map": subtopic_map,
            "default_subtopics": default_subtopics,
            "concepts": topics,
            "templates": templates,
            "counter_templates": counter_templates,
        }
