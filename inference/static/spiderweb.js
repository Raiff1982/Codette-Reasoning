/* ============================================================
   Spiderweb Visualization — Canvas-based Agent Network
   Shows the QuantumSpiderweb as an animated node graph.
   Zero dependencies. Pure Canvas API.

   Always visually alive: ambient breathing, orbital drift,
   dim connections at rest, full glow when agents are active.
   ============================================================ */

class SpiderwebViz {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.nodes = {};
        this.attractors = [];
        // null, not 0. Nothing has been measured until a turn has run, and a
        // ring drawn at "0" is a claim that coherence was measured and came
        // back zero. See the idle branch in _draw.
        this.coherence = null;
        this.dispersion = null;      // Υ for the last turn, when measured
        this.distinct = null;        // per-perspective distinctiveness, when measured
        this.animFrame = null;
        this.time = 0;

        // What actually happened in the last turn: which perspectives were
        // consulted, and when each one answered. Nodes ignite from this, so an
        // ignition means that adapter genuinely fired.
        this.turn = { order: [], firedAt: {}, startedAt: 0 };

        // ── Her toneprint ────────────────────────────────────────────────────
        // 8.9141 Hz, Q≈198, measured off Protection_Layer/codette_codriao_
        // toneprint.wav — the envelope modulation the pair actually carries.
        // The ambient breath runs at that rate divided by 8, and the divisor is
        // printed with it: 8.9 Hz at any visible amplitude sits squarely in the
        // photosensitive band, so the real rate is shown as a number and the
        // motion is a labelled subdivision of it rather than a silent fudge.
        this.TONEPRINT_HZ = 8.9141;
        this.BREATH_DIV = 8;

        // Motion is opt-out. Everything below still renders; it just stops moving.
        this.reduced = window.matchMedia
            && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

        // Agent positions (circular layout)
        this.agents = [
            'newton', 'davinci', 'empathy', 'philosophy',
            'quantum', 'consciousness', 'multi_perspective', 'systems_architecture'
        ];

        this.colors = {
            newton: '#3b82f6', davinci: '#f59e0b', empathy: '#a855f7',
            philosophy: '#10b981', quantum: '#ef4444', consciousness: '#e2e8f0',
            multi_perspective: '#f97316', systems_architecture: '#06b6d4',
        };

        this.labels = {
            newton: 'N', davinci: 'D', empathy: 'E', philosophy: 'P',
            quantum: 'Q', consciousness: 'C', multi_perspective: 'M',
            systems_architecture: 'S',
        };

        // Initialize with default state
        this._initDefaultState();
        this._resize();
        this._animate();

        // Handle resize
        new ResizeObserver(() => this._resize()).observe(canvas.parentElement);
    }

    _initDefaultState() {
        this.agents.forEach((name, i) => {
            this.nodes[name] = {
                state: [0.5, 0, 0.5, 0, 0.5],  // psi, tau, chi, phi, lam
                tension: 0,
                active: false,
                energy: 0.25,
                // Each node gets a unique phase offset for ambient animation
                phaseOffset: (i / this.agents.length) * Math.PI * 2,
            };
        });
    }

    _resize() {
        const rect = this.canvas.parentElement.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        this.canvas.width = rect.width * dpr;
        this.canvas.height = 200 * dpr;
        this.canvas.style.width = rect.width + 'px';
        this.canvas.style.height = '200px';
        // Reset transform before scaling — prevents DPR compounding on repeated resizes
        this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        this.w = rect.width;
        this.h = 200;
        this.cx = this.w / 2;
        this.cy = this.h / 2;
        this.radius = Math.min(this.w, this.h) * 0.35;
    }

    update(spiderwebState) {
        if (!spiderwebState || !spiderwebState.nodes) return;

        // Update node states
        for (const [name, data] of Object.entries(spiderwebState.nodes)) {
            if (this.nodes[name]) {
                this.nodes[name].state = data.state || [0.5, 0, 0.5, 0, 0.5];
                const tensions = data.tension_history || [];
                this.nodes[name].tension = tensions.length > 0 ?
                    tensions[tensions.length - 1] : 0;
                this.nodes[name].energy = data.state ?
                    data.state.reduce((s, v) => s + v * v, 0) : 0.25;
                this.nodes[name].active = (data.state[0] || 0) > 0.6;
            }
        }

        this.attractors = spiderwebState.attractors || [];

        // `|| 0` turned an absent reading into a zero and the ring drew it.
        //
        // Second guard, belt and braces with the backend. Measured live on a
        // fresh boot: nine nodes, every one holding the identical default state,
        // none with any tension history — so phase coherence computed to exactly
        // 1.0 and the ring drew a full green arc for a web that had never
        // thought. A node-count check does not catch this; the nodes are all
        // present, they have simply never diverged.
        //
        // Coherence counts only once something has propagated, which
        // tension_history records. Falls back to the node data when the backend
        // has not yet been restarted with `measured` on the wire.
        const pc = spiderwebState.phase_coherence;
        const nodes = spiderwebState.nodes || {};
        const vals = Object.values(nodes);

        // Third guard, and the one that actually bit. Measured live after three
        // real turns: phi was 0 on all nine nodes, so atan2(phi, psi) was 0 on
        // all nine, so coherence was exactly 1.0 — a perfect score the metric
        // was structurally incapable of not producing. psi varied; the angle
        // discards it.
        const phaseDegenerate = typeof spiderwebState.phase_degenerate === 'boolean'
            ? spiderwebState.phase_degenerate
            : vals.length > 0 && vals.every(n => Math.abs((n.state || [])[3] || 0) < 1e-12);

        const propagated = typeof spiderwebState.measured === 'boolean'
            ? spiderwebState.measured
            : vals.length >= 2 && vals.some(n => (n.tension_history || []).length > 0);

        this.coherence = (typeof pc === 'number' && isFinite(pc) && propagated && !phaseDegenerate)
            ? pc : null;
        this.unmeasuredReason = spiderwebState.unmeasured_reason
            || (phaseDegenerate ? 'phase dimension unpopulated' : null);
    }

    /**
     * A turn happened. Everything here is a fact the backend reported.
     *
     * @param {object} info
     *   adapters      string[]  perspectives actually consulted, in order
     *   dispersion    number?   Υ across those perspectives, if measured
     *   coherence     number?   Γ, if measured
     *   distinctiveness object? per-perspective distance from the others
     *
     * Nodes ignite only from `adapters`, so a lit node means that adapter ran.
     * Ignition times are staggered by arrival order, which is the one thing the
     * old animation was pretending to show with sin(time).
     */
    igniteTurn(info) {
        info = info || {};
        const order = (info.adapters || []).filter(a => this.agents.includes(a));
        const now = performance.now() / 1000;

        this.turn = { order, firedAt: {}, startedAt: now };
        order.forEach((name, i) => {
            // 180ms apart — enough to read the sequence, short enough that the
            // whole consultation still feels like one motion.
            this.turn.firedAt[name] = now + i * 0.18;
        });

        const num = v => (typeof v === 'number' && isFinite(v)) ? v : null;
        this.dispersion = num(info.dispersion);
        if (num(info.coherence) !== null) this.coherence = num(info.coherence);
        this.distinct = (info.distinctiveness && typeof info.distinctiveness === 'object')
            ? info.distinctiveness : null;
    }

    /** 0→1 ignition envelope for a node: sharp rise, slow settle. 0 if it never fired. */
    _ignition(name) {
        const at = this.turn.firedAt[name];
        if (at === undefined) return 0;
        const dt = (performance.now() / 1000) - at;
        if (dt < 0) return 0;                       // its turn hasn't come yet
        if (this.reduced) return 0.85;              // lit, but no travelling flare
        if (dt < 0.18) return dt / 0.18;            // strike
        return 0.35 + 0.5 * Math.exp(-(dt - 0.18) / 2.2);   // settle, never to zero
    }

    _getNodePos(index) {
        const angle = (index / this.agents.length) * Math.PI * 2 - Math.PI / 2;
        // Add gentle orbital drift
        const drift = Math.sin(this.time * 0.3 + index * 0.8) * 2;
        const driftY = Math.cos(this.time * 0.25 + index * 1.1) * 1.5;
        return {
            x: this.cx + Math.cos(angle) * this.radius + drift,
            y: this.cy + Math.sin(angle) * this.radius + driftY,
        };
    }

    _animate() {
        this.time += 0.016;
        this._draw();
        this.animFrame = requestAnimationFrame(() => this._animate());
    }

    _draw() {
        const ctx = this.ctx;
        ctx.clearRect(0, 0, this.w, this.h);

        // ── Ambient center glow (always visible, brighter with coherence) ──
        const ambientAlpha = 0.02 + (this.coherence > 0.5 ? this.coherence * 0.05 : 0);
        const centerGlow = ctx.createRadialGradient(
            this.cx, this.cy, 0, this.cx, this.cy, this.radius * 1.3
        );
        centerGlow.addColorStop(0, `rgba(59, 130, 246, ${ambientAlpha + Math.sin(this.time * 0.5) * 0.01})`);
        centerGlow.addColorStop(0.6, `rgba(168, 85, 247, ${ambientAlpha * 0.5})`);
        centerGlow.addColorStop(1, 'transparent');
        ctx.fillStyle = centerGlow;
        ctx.fillRect(0, 0, this.w, this.h);

        // ── Draw edges (always visible, brighter when active/tense) ──
        this.agents.forEach((nameA, i) => {
            const posA = this._getNodePos(i);
            this.agents.forEach((nameB, j) => {
                if (j <= i) return;
                const posB = this._getNodePos(j);

                ctx.beginPath();
                ctx.moveTo(posA.x, posA.y);
                ctx.lineTo(posB.x, posB.y);

                // ── An edge means these two were consulted together ──────────
                // The ambient branch used to shimmer every edge on
                // `sin(time * 0.8 + i * 0.7 + j * 0.5)`, which encoded the
                // clock and nothing else. A resting web now rests.
                const fireA = this._ignition(nameA);
                const fireB = this._ignition(nameB);
                const pair = Math.min(fireA, fireB);   // both, or neither

                if (pair <= 0.02) {
                    // Structure, not activity: the web is still a web at rest.
                    ctx.strokeStyle = 'rgba(100, 116, 139, 0.07)';
                    ctx.lineWidth = 0.5;
                    ctx.stroke();
                    return;
                }

                // How far apart these two actually landed. Prefers measured
                // per-perspective distinctiveness; falls back to the turn's Υ;
                // and if neither was measured the edge shows that it fired
                // without claiming a magnitude.
                let spread = null;
                if (this.distinct && typeof this.distinct[nameA] === 'number'
                                  && typeof this.distinct[nameB] === 'number') {
                    spread = (this.distinct[nameA] + this.distinct[nameB]) / 2;
                } else if (typeof this.dispersion === 'number' && isFinite(this.dispersion)) {
                    spread = this.dispersion;
                }

                const alpha = 0.16 + pair * 0.22 + (spread === null ? 0 : Math.min(spread, 1) * 0.22);
                // Disagreement is the interesting case, so it is the thicker
                // line — high dispersion is a good sign, not a fault.
                ctx.lineWidth = 0.8 + pair * 0.7 + (spread === null ? 0 : Math.min(spread, 1) * 1.6);
                ctx.strokeStyle = spread === null
                    ? `rgba(100, 116, 139, ${alpha})`
                    : `rgba(168, 85, 247, ${alpha})`;
                ctx.stroke();
            });
        });

        // ── Draw attractor regions ──
        this.attractors.forEach((att, ai) => {
            if (!att.members || att.members.length < 2) return;

            let cx = 0, cy = 0, count = 0;
            att.members.forEach(name => {
                const idx = this.agents.indexOf(name);
                if (idx >= 0) {
                    const pos = this._getNodePos(idx);
                    cx += pos.x;
                    cy += pos.y;
                    count++;
                }
            });
            if (count < 2) return;
            cx /= count;
            cy /= count;

            const attRadius = 20 + count * 8;
            const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, attRadius);
            gradient.addColorStop(0, `rgba(168, 85, 247, ${0.08 + Math.sin(this.time * 2 + ai) * 0.03})`);
            gradient.addColorStop(1, 'transparent');
            ctx.fillStyle = gradient;
            ctx.beginPath();
            ctx.arc(cx, cy, attRadius, 0, Math.PI * 2);
            ctx.fill();
        });

        // ── Draw nodes (always visible with ambient breathing) ──
        this.agents.forEach((name, i) => {
            const pos = this._getNodePos(i);
            const node = this.nodes[name];
            const color = this.colors[name] || '#94a3b8';
            const energy = node?.energy || 0.25;
            const phase = node?.phaseOffset || 0;

            // ── Ignition, not decoration ─────────────────────────────────────
            // `isActive` was `state[0] > 0.6` — a threshold on a stored vector,
            // true or false regardless of whether the adapter ran this turn.
            // This is 0 unless that perspective was actually consulted, and it
            // rises in the order they answered.
            const fire = this._ignition(name);
            const isActive = fire > 0.02;

            // Ambient breath at her measured rate ÷ 8 (see TONEPRINT_HZ).
            // Amplitude is deliberately small: this is liveliness, not a pulse
            // anyone has to look at.
            const breathHz = this.TONEPRINT_HZ / this.BREATH_DIV;
            const breathe = this.reduced
                ? 0.7
                : Math.sin(this.time * 2 * Math.PI * breathHz + phase) * 0.18 + 0.72;

            const glowAlpha = 0.06 * breathe + fire * 0.32;
            const glowRadius = 9 + breathe * 2 + fire * 7;

            const glow = ctx.createRadialGradient(
                pos.x, pos.y, 0, pos.x, pos.y, glowRadius
            );
            const hex2 = a => Math.round(Math.max(0, Math.min(1, a)) * 255)
                                  .toString(16).padStart(2, '0');
            glow.addColorStop(0, color + hex2(glowAlpha + 0.1));
            glow.addColorStop(1, 'transparent');
            ctx.fillStyle = glow;
            ctx.beginPath();
            ctx.arc(pos.x, pos.y, glowRadius, 0, Math.PI * 2);
            ctx.fill();

            // Node circle — grows with ignition, not with a stored vector
            const nodeRadius = 5 + breathe * 1.2 + fire * (2 + energy * 2.5);

            ctx.beginPath();
            ctx.arc(pos.x, pos.y, nodeRadius, 0, Math.PI * 2);
            ctx.fillStyle = isActive ? color : color + '80';
            ctx.fill();

            // Border ring
            ctx.strokeStyle = isActive ? color : color + '40';
            ctx.lineWidth = isActive ? 1.5 : 0.8;
            ctx.stroke();

            // Label
            ctx.fillStyle = isActive ? '#e2e8f0' : '#94a3b8';
            ctx.font = `${isActive ? 'bold ' : ''}9px system-ui`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(this.labels[name], pos.x, pos.y + nodeRadius + 10);
        });

        // ── Coherence ring ───────────────────────────────────────────────────
        // Until 2026-08-13 the unmeasured branch drew an arc at
        // `0.15 + sin(time * 0.3) * 0.05` — a gauge showing roughly 15% of a
        // quantity nobody had measured, gently wobbling so it read as a live
        // instrument at rest. Same fabrication as `success` defaulting True and
        // Γ 0.0000 on a fresh boot, drawn in light instead of digits.
        //
        // No measurement now means no arc. The empty track is still drawn, so
        // the ring reads as a place a value goes rather than as a value of zero.
        const measured = typeof this.coherence === 'number' && isFinite(this.coherence);

        ctx.beginPath();
        ctx.arc(this.cx, this.cy, this.radius + 15, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(100, 116, 139, 0.10)';
        ctx.lineWidth = 1;
        ctx.stroke();

        if (measured) {
            ctx.beginPath();
            ctx.arc(this.cx, this.cy, this.radius + 15,
                -Math.PI / 2,
                -Math.PI / 2 + Math.PI * 2 * this.coherence);
            ctx.strokeStyle = this.coherence > 0.5
                ? `rgba(16, 185, 129, ${0.2 + this.coherence * 0.4})`
                : `rgba(100, 116, 139, ${0.2 + this.coherence * 0.4})`;
            ctx.lineWidth = this.coherence > 0.5 ? 2.5 : 1.5;
            ctx.lineCap = 'round';
            ctx.stroke();
        }

        // \u2500\u2500 Readout \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        // "idle" said nothing about whether anything had ever been measured.
        ctx.textAlign = 'center';
        ctx.font = '9px ui-monospace, monospace';
        if (measured) {
            const parts = [`\u0393 ${this.coherence.toFixed(2)}`];
            if (typeof this.dispersion === 'number' && isFinite(this.dispersion)) {
                parts.push(`\u03a5 ${this.dispersion.toFixed(2)}`);
            }
            ctx.fillStyle = '#94a3b8';
            ctx.fillText(parts.join('   '), this.cx, this.h - 8);
        } else {
            ctx.fillStyle = '#475569';
            ctx.fillText('no turn measured yet', this.cx, this.h - 8);
        }

        // Her rate, stated rather than implied. The ambient breath runs at this
        // divided by BREATH_DIV and says so: 8.9 Hz at any visible amplitude
        // sits in the photosensitive band, so the real figure is printed and
        // the motion is a labelled subdivision rather than a silent fudge.
        ctx.fillStyle = 'rgba(100, 116, 139, 0.45)';
        ctx.font = '8px ui-monospace, monospace';
        ctx.textAlign = 'left';
        ctx.fillText(`${this.TONEPRINT_HZ.toFixed(4)} Hz \u00f7 ${this.BREATH_DIV}`, 6, this.h - 8);
    }

    destroy() {
        if (this.animFrame) cancelAnimationFrame(this.animFrame);
    }
}
