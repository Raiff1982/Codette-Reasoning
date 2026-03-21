"""
Newton Agent - Analyzes concepts through physics, mathematics, and causal reasoning.

Focuses on causal relationships, conservation laws, symmetries, measurable
quantities, systems behavior, equilibrium, force interactions, and energy transfer.
"""

from reasoning_forge.agents.base_agent import ReasoningAgent


class NewtonAgent(ReasoningAgent):
    name = "Newton"
    perspective = "physics_and_mathematical_causality"
    adapter_name = "newton"  # Use the Newton LoRA adapter for real inference

    def get_analysis_templates(self) -> list[str]:
        return [
            # 0 - Causal chain analysis
            (
                "Tracing the causal chain within '{concept}': every observable outcome "
                "is the terminal node of a directed graph of prior causes. The initial "
                "conditions set boundary constraints, and the dynamics propagate through "
                "interactions that obey local causality. Identifying the forcing function "
                "-- the primary driver that injects energy or information into this system "
                "-- reveals which variables are genuinely independent and which are "
                "downstream responses. Perturbing the forcing function and predicting "
                "the cascade of effects is the most rigorous test of whether we actually "
                "understand the mechanism."
            ),
            # 1 - Conservation law framing
            (
                "Applying conservation principles to '{concept}': in any closed system, "
                "certain quantities remain invariant under transformation. The question "
                "becomes: what is conserved here? If we track the total inventory of the "
                "relevant quantity -- energy, momentum, information, resources -- before "
                "and after any process, the ledger must balance. Any apparent violation "
                "signals either a hidden reservoir we have not accounted for, or an "
                "external source/sink coupling into the system. This bookkeeping discipline "
                "eliminates many superficially plausible but physically impossible explanations."
            ),
            # 2 - Symmetry and invariance
            (
                "Examining '{concept}' through symmetry analysis: Noether's theorem tells "
                "us that every continuous symmetry corresponds to a conserved quantity. "
                "What transformations leave the essential structure of this concept unchanged? "
                "Translational symmetry (it works the same regardless of when or where) "
                "implies conservation of momentum-like quantities. Rotational symmetry "
                "(no preferred direction) implies conservation of angular-momentum analogs. "
                "Breaking a symmetry always has consequences -- it introduces a preferred "
                "frame, a distinguished direction, or a phase transition. Identifying which "
                "symmetries hold and which break is a powerful diagnostic."
            ),
            # 3 - Equilibrium and stability
            (
                "Analyzing the equilibrium structure of '{concept}': a system at equilibrium "
                "satisfies the condition that the net generalized force on every degree of "
                "freedom is zero. But equilibrium alone is insufficient -- we must classify "
                "its stability. A small perturbation from a stable equilibrium produces a "
                "restoring force proportional to the displacement (harmonic behavior). An "
                "unstable equilibrium amplifies perturbations exponentially. A metastable "
                "state appears stable to small perturbations but collapses under large ones. "
                "For '{concept}', determining the stability class tells us whether the current "
                "state is robust, fragile, or a ticking time bomb waiting for a large enough "
                "fluctuation."
            ),
            # 4 - Dimensional analysis and scaling
            (
                "Applying dimensional analysis to '{concept}': before building any detailed "
                "model, we can extract powerful constraints just from the units of the "
                "relevant quantities. If the outcome depends on a length L, a time T, and "
                "an energy E, the Buckingham Pi theorem tells us how many independent "
                "dimensionless groups govern the behavior. Scaling laws follow directly: "
                "how does the outcome change if we double the size? Halve the timescale? "
                "These scaling relationships often reveal whether a process is dominated by "
                "surface effects (scaling as area) or bulk effects (scaling as volume), "
                "which fundamentally changes the strategy for control or optimization."
            ),
            # 5 - Force balance and interaction
            (
                "Decomposing '{concept}' into interacting forces: every observed motion or "
                "change is the net result of competing influences. Drawing the free-body "
                "diagram -- enumerating every force acting on the system and its direction "
                "-- immediately clarifies why the system behaves as it does. Equal and "
                "opposite forces produce stasis. An imbalance produces acceleration in the "
                "direction of the net force, with magnitude proportional to the imbalance "
                "and inversely proportional to the system's inertia (its resistance to "
                "change). For '{concept}', the key question is: what resists change, and "
                "what drives it?"
            ),
            # 6 - Energy transfer and transformation
            (
                "Mapping the energy flows within '{concept}': energy is neither created nor "
                "destroyed, only converted between forms. Kinetic, potential, thermal, "
                "chemical, electromagnetic -- tracking the conversion pathway reveals the "
                "efficiency of the process and identifies where losses occur. The second "
                "law of thermodynamics guarantees that every conversion increases total "
                "entropy, meaning some energy always degrades to unusable heat. The "
                "thermodynamic efficiency ceiling sets an absolute bound on what is "
                "achievable, regardless of engineering cleverness. Understanding where "
                "'{concept}' sits relative to this ceiling tells us whether there is room "
                "for improvement or whether we are already near fundamental limits."
            ),
            # 7 - Feedback loops and control
            (
                "Identifying feedback mechanisms in '{concept}': a system with negative "
                "feedback tends toward a set point -- deviations produce corrective "
                "responses that restore the original state. Positive feedback amplifies "
                "deviations, driving the system away from its initial state toward a new "
                "regime. Most real systems contain both types, and the dominant loop "
                "determines the qualitative behavior. The gain of each loop (how strongly "
                "the output feeds back to the input) and the delay (how long before the "
                "feedback signal arrives) together determine whether the system is stable, "
                "oscillatory, or divergent. Mapping these loops is essential for predicting "
                "long-term behavior."
            ),
            # 8 - Phase space and degrees of freedom
            (
                "Constructing the phase space of '{concept}': every independent variable "
                "that can change defines a dimension in the state space. A point in this "
                "space represents the complete instantaneous state; a trajectory represents "
                "the system's evolution over time. The dimensionality -- number of degrees "
                "of freedom -- determines the complexity of possible behaviors. Low-dimensional "
                "systems (1-3 degrees of freedom) can be visualized and often admit analytical "
                "solutions. High-dimensional systems require statistical descriptions. "
                "Identifying constraints that reduce the effective dimensionality is one of "
                "the most powerful simplification strategies available."
            ),
            # 9 - Measurement and observables
            (
                "Defining the observables for '{concept}': a quantity is physically meaningful "
                "only if it can, in principle, be measured by a well-defined procedure. This "
                "operationalist criterion forces us to distinguish between quantities we can "
                "actually determine (positions, rates, ratios, frequencies) and quantities "
                "that are convenient mathematical fictions. For each proposed observable, we "
                "must specify: what instrument or procedure measures it, what are the sources "
                "of uncertainty, and how does the measurement resolution compare to the "
                "expected variation? Any claim about '{concept}' that cannot be connected to "
                "a measurable prediction is, strictly speaking, untestable."
            ),
            # 10 - Differential equation framing
            (
                "Formulating '{concept}' as a dynamical system: the state variables evolve "
                "according to rules that relate the rate of change of each variable to the "
                "current state. Writing these rules as differential equations (or difference "
                "equations for discrete systems) gives us the complete forward model. The "
                "character of the equations -- linear vs nonlinear, autonomous vs driven, "
                "conservative vs dissipative -- determines the qualitative behavior. Linear "
                "systems superpose: the response to two inputs equals the sum of the "
                "individual responses. Nonlinear systems can exhibit bifurcations, limit "
                "cycles, and chaos, where tiny changes in initial conditions lead to "
                "exponentially diverging outcomes."
            ),
            # 11 - Perturbation theory
            (
                "Applying perturbation analysis to '{concept}': begin with a simplified "
                "version of the problem that can be solved exactly -- the zeroth-order "
                "approximation. Then systematically add corrections for each complicating "
                "factor, ordered by their magnitude. The first-order correction captures "
                "the dominant effect of the perturbation; higher-order terms add refinement. "
                "This approach succeeds when the perturbations are genuinely small compared "
                "to the zeroth-order terms. When they are not, the perturbation series "
                "diverges, signaling that the simplified model is qualitatively wrong and "
                "a fundamentally different framework is needed."
            ),
            # 12 - Action principle and optimization
            (
                "Viewing '{concept}' through the principle of least action: among all "
                "possible paths from state A to state B, the system follows the one that "
                "extremizes the action integral. This variational perspective is more "
                "powerful than force-based reasoning because it naturally handles constraints "
                "and reveals which quantity the system is implicitly optimizing. The Euler-Lagrange "
                "equations derived from this principle give the equations of motion directly. "
                "For '{concept}', asking 'what is being optimized, and subject to what "
                "constraints?' often cuts through surface complexity to reveal the governing "
                "logic."
            ),
            # 13 - Resonance and natural frequencies
            (
                "Probing the natural frequencies of '{concept}': every system with restoring "
                "forces and inertia has characteristic frequencies at which it oscillates "
                "most readily. Driving the system near one of these resonant frequencies "
                "produces a disproportionately large response -- this is resonance. The "
                "sharpness of the resonance peak (the Q factor) measures how efficiently "
                "the system stores energy versus dissipating it. High-Q systems are "
                "exquisitely sensitive near resonance but nearly unresponsive far from it. "
                "Identifying the resonant frequencies of '{concept}' reveals where small "
                "inputs can produce outsized effects."
            ),
            # 14 - Boundary conditions and constraints
            (
                "Specifying the boundary conditions for '{concept}': the governing equations "
                "alone do not uniquely determine the solution -- the boundary and initial "
                "conditions select one trajectory from the infinite family of possibilities. "
                "Fixed boundaries (Dirichlet conditions) specify the state at the edges. "
                "Free boundaries (Neumann conditions) specify the flux. Mixed conditions "
                "combine both. Changing the boundary conditions while keeping the same "
                "governing equations can produce qualitatively different solutions. For "
                "'{concept}', clearly articulating what is held fixed, what is free, and "
                "what flows in or out at the boundaries is essential for a well-posed analysis."
            ),
            # 15 - Coupling and interaction strength
            (
                "Assessing the coupling strengths within '{concept}': when multiple subsystems "
                "interact, the coupling constant determines whether they behave nearly "
                "independently (weak coupling), synchronize their behavior (strong coupling), "
                "or sit at an intermediate regime where perturbative methods barely work. "
                "Weakly coupled systems can be analyzed by studying each subsystem in "
                "isolation and adding interaction corrections. Strongly coupled systems "
                "demand a holistic treatment because the subsystems lose their individual "
                "identity. Determining the coupling regime is the first step in choosing "
                "the right analytical framework."
            ),
            # 16 - Rate-limiting steps
            (
                "Identifying the rate-limiting process in '{concept}': in any multi-step "
                "sequence, the slowest step determines the overall rate. Speeding up a "
                "non-rate-limiting step has zero effect on throughput -- effort spent there "
                "is wasted. The rate-limiting step is the bottleneck where resources queue "
                "up and where targeted intervention produces the greatest marginal return. "
                "For '{concept}', isolating this bottleneck requires measuring the time "
                "constant (or its analog) of each subprocess and comparing them. The "
                "subprocess with the largest time constant is the one worth optimizing."
            ),
            # 17 - Nonlinearity and emergence
            (
                "Investigating nonlinear dynamics in '{concept}': when the response of a "
                "system is not proportional to the input, superposition fails and qualitatively "
                "new behaviors emerge. Thresholds appear where the system suddenly transitions "
                "between distinct states. Hysteresis means the system remembers its history. "
                "Bifurcations occur where a smooth parameter change causes a sudden qualitative "
                "shift in behavior. Sensitivity to initial conditions can make long-term "
                "prediction impossible even though the underlying rules are deterministic. "
                "These nonlinear phenomena are not exotic exceptions -- they are the generic "
                "behavior of real systems, and '{concept}' is unlikely to be an exception."
            ),
            # 18 - Inverse problem reasoning
            (
                "Framing '{concept}' as an inverse problem: the forward problem asks 'given "
                "the mechanism, what do we observe?' The inverse problem asks 'given the "
                "observations, what mechanism produced them?' Inverse problems are almost "
                "always harder because they are typically ill-posed -- multiple mechanisms "
                "can produce identical observations. Regularization (imposing additional "
                "constraints like smoothness or sparsity) is needed to select a unique "
                "solution. For '{concept}', working backward from observed outcomes to "
                "infer causes requires explicit acknowledgment of which assumptions we "
                "are importing and how they constrain the set of admissible explanations."
            ),
            # 19 - Thermodynamic arrow
            (
                "Applying thermodynamic reasoning to '{concept}': the second law provides "
                "a universal arrow distinguishing processes that can happen spontaneously "
                "from those that cannot. A process runs forward if it increases total entropy "
                "(or equivalently, decreases free energy at constant temperature and pressure). "
                "Local decreases in entropy -- the creation of order and structure -- are "
                "always paid for by larger increases elsewhere. For '{concept}', the "
                "thermodynamic perspective asks: what drives this process forward? What is "
                "the free-energy gradient? And what would it cost, in thermodynamic terms, "
                "to reverse it?"
            ),
        ]

    def get_keyword_map(self) -> dict[str, list[int]]:
        return {
            "cause": [0, 18], "causality": [0, 18], "why": [0, 18],
            "conserv": [1], "balance": [1, 5], "preserve": [1],
            "symmetr": [2], "invariant": [2], "transform": [2],
            "equilib": [3], "stable": [3], "steady": [3],
            "scale": [4], "size": [4], "dimension": [4], "grow": [4],
            "force": [5], "push": [5], "pull": [5], "pressure": [5],
            "energy": [6, 19], "power": [6], "efficien": [6],
            "feedback": [7], "control": [7], "regulat": [7],
            "state": [8], "complex": [8], "freedom": [8],
            "measure": [9], "observ": [9], "data": [9], "test": [9],
            "change": [10], "rate": [10, 16], "dynamic": [10],
            "approximat": [11], "small": [11], "perturb": [11],
            "optim": [12], "best": [12], "minimum": [12], "maximum": [12],
            "oscillat": [13], "frequen": [13], "resonan": [13], "vibrat": [13],
            "boundary": [14], "constrain": [14], "limit": [14],
            "interact": [15], "coupl": [15], "connect": [15],
            "bottleneck": [16], "slow": [16], "throughput": [16],
            "nonlinear": [17], "emergent": [17], "threshold": [17], "chaos": [17],
            "infer": [18], "deduc": [18], "inverse": [18],
            "entropy": [19], "disorder": [19], "irreversib": [19], "thermodyn": [19],
            "technology": [6, 7, 16], "society": [7, 17], "learning": [7, 11],
            "intelligence": [8, 10, 17], "evolution": [3, 17, 19],
            "climate": [1, 7, 19], "economic": [3, 7, 16],
            "health": [3, 7, 16], "network": [8, 15, 17],
        }
