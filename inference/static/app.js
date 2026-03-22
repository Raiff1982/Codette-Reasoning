/* ============================================================
   Codette Chat UI — Frontend Logic
   Pure vanilla JS. Zero dependencies.
   ============================================================ */

// Adapter color map
const COLORS = {
    newton: '#3b82f6', davinci: '#f59e0b', empathy: '#a855f7',
    philosophy: '#10b981', quantum: '#ef4444', consciousness: '#e2e8f0',
    multi_perspective: '#f97316', systems_architecture: '#06b6d4',
    _base: '#94a3b8', auto: '#94a3b8',
};

const LABELS = {
    newton: 'N', davinci: 'D', empathy: 'E', philosophy: 'P',
    quantum: 'Q', consciousness: 'C', multi_perspective: 'M',
    systems_architecture: 'S',
};

// State
let isLoading = false;
let spiderwebViz = null;
let serverConnected = true;
let reconnectTimer = null;
let _totalEthicalChecks = 0;
let _startupCocoonCount = 0;
let _selectedVoice = null;

// ── Initialization ──
document.addEventListener('DOMContentLoaded', () => {
    initUI();
    pollStatus();
    loadSessions();
    initCoverageDots();
    initAdapterDots();

    // Initialize spiderweb canvas
    const canvas = document.getElementById('spiderweb-canvas');
    if (canvas) {
        spiderwebViz = new SpiderwebViz(canvas);
    }
});

function initUI() {
    const input = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const micBtn = document.getElementById('mic-btn');
    const newBtn = document.getElementById('btn-new-chat');
    const panelBtn = document.getElementById('btn-toggle-panel');
    const maxAdapters = document.getElementById('max-adapters');

    // Send on Enter (Shift+Enter for newline)
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Auto-resize textarea
    input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    });

    sendBtn.addEventListener('click', sendMessage);
    newBtn.addEventListener('click', newChat);

    const exportBtn = document.getElementById('btn-export');
    const importBtn = document.getElementById('btn-import');
    const importFile = document.getElementById('import-file');

    exportBtn.addEventListener('click', exportSession);
    importBtn.addEventListener('click', () => importFile.click());
    importFile.addEventListener('change', importSession);

    panelBtn.addEventListener('click', () => {
        const panel = document.getElementById('side-panel');
        panel.classList.toggle('collapsed');
        // Update button label
        panelBtn.textContent = panel.classList.contains('collapsed') ? 'Cocoon' : 'Close';
    });

    maxAdapters.addEventListener('input', () => {
        document.getElementById('max-adapters-value').textContent = maxAdapters.value;
    });

    // Voice input via Web Speech API
    initVoice(micBtn);

    // TTS — initialize voice selector with preference for natural voices
    initTTS();
}

// ── Voice Input ──
let _recognition = null;
let _isRecording = false;

function initVoice(micBtn) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        micBtn.title = 'Voice not supported in this browser';
        micBtn.style.opacity = '0.3';
        micBtn.style.cursor = 'not-allowed';
        return;
    }

    _recognition = new SpeechRecognition();
    _recognition.continuous = false;
    _recognition.interimResults = true;
    _recognition.lang = 'en-US';

    const input = document.getElementById('chat-input');

    _recognition.onstart = () => {
        _isRecording = true;
        micBtn.classList.add('recording');
        micBtn.title = 'Listening... click to stop';
    };

    _recognition.onresult = (event) => {
        let transcript = '';
        let isFinal = false;
        for (let i = event.resultIndex; i < event.results.length; i++) {
            transcript += event.results[i][0].transcript;
            if (event.results[i].isFinal) isFinal = true;
        }
        // Show interim results in the input box
        input.value = transcript;
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 120) + 'px';

        if (isFinal) {
            stopVoice(micBtn);
        }
    };

    _recognition.onerror = (event) => {
        console.log('Speech recognition error:', event.error);
        stopVoice(micBtn);
        if (event.error === 'not-allowed') {
            micBtn.title = 'Microphone access denied';
        }
    };

    _recognition.onend = () => {
        stopVoice(micBtn);
    };

    micBtn.addEventListener('click', () => {
        if (_isRecording) {
            _recognition.stop();
            stopVoice(micBtn);
        } else {
            try {
                _recognition.start();
            } catch (e) {
                console.log('Speech recognition start error:', e);
            }
        }
    });
}

function stopVoice(micBtn) {
    _isRecording = false;
    micBtn.classList.remove('recording');
    micBtn.title = 'Voice input';
}

// ── TTS Voice System ──
function initTTS() {
    if (!window.speechSynthesis) return;

    const voiceSelect = document.getElementById('voice-select');
    const ttsToggle = document.getElementById('tts-toggle');

    if (ttsToggle) {
        ttsToggle.addEventListener('change', () => {
            if (ttsToggle.checked && !window.speechSynthesis) {
                ttsToggle.checked = false;
            }
        });
    }

    function populateVoices() {
        const voices = speechSynthesis.getVoices();
        if (!voices.length) return;

        voiceSelect.innerHTML = '';

        // Filter to English voices and sort: natural/neural first
        const enVoices = voices.filter(v => v.lang.startsWith('en'));
        const allVoices = enVoices.length > 0 ? enVoices : voices;

        // Score voices — prefer natural/neural/online, then female names common in TTS
        const scored = allVoices.map(v => {
            let score = 0;
            const name = v.name.toLowerCase();
            if (name.includes('natural') || name.includes('neural')) score += 100;
            if (name.includes('online')) score += 50;
            // Prefer known high-quality voices
            if (name.includes('jenny')) score += 80;
            if (name.includes('aria')) score += 80;
            if (name.includes('sara')) score += 70;
            if (name.includes('zira')) score += 30;
            if (name.includes('samantha')) score += 60;
            if (name.includes('karen')) score += 50;
            if (name.includes('google') && name.includes('us')) score += 40;
            // Penalize David/Mark (male, more robotic on Windows)
            if (name.includes('david') || name.includes('mark')) score -= 20;
            return { voice: v, score };
        });

        scored.sort((a, b) => b.score - a.score);

        scored.forEach(({ voice }, i) => {
            const opt = document.createElement('option');
            const tag = voice.name.toLowerCase().includes('natural') ? ' *' : '';
            opt.value = i;
            opt.textContent = voice.name.replace('Microsoft ', '').replace(' Online (Natural)', ' *').substring(0, 22) + tag;
            opt.title = voice.name;
            voiceSelect.appendChild(opt);
        });

        // Auto-select best voice
        _selectedVoice = scored[0]?.voice || null;

        voiceSelect.addEventListener('change', () => {
            const idx = parseInt(voiceSelect.value);
            _selectedVoice = scored[idx]?.voice || null;
        });
    }

    // Voices load asynchronously in most browsers
    populateVoices();
    speechSynthesis.addEventListener('voiceschanged', populateVoices);
}

function speakText(text) {
    if (!window.speechSynthesis || !text) return;

    // Cancel any ongoing speech
    speechSynthesis.cancel();

    // Clean text for speech — strip markdown artifacts
    let clean = text
        .replace(/\*\*([^*]+)\*\*/g, '$1')   // bold
        .replace(/\*([^*]+)\*/g, '$1')         // italic
        .replace(/__([^_]+)__/g, '$1')
        .replace(/`([^`]+)`/g, '$1')           // code
        .replace(/```[\s\S]*?```/g, '')        // code blocks
        .replace(/^#+\s/gm, '')                // headers
        .replace(/^[\-\*]\s/gm, '')            // bullets
        .replace(/\n{2,}/g, '. ')              // paragraph breaks → pauses
        .replace(/\n/g, ' ')
        .trim();

    const utter = new SpeechSynthesisUtterance(clean);

    if (_selectedVoice) {
        utter.voice = _selectedVoice;
    }

    // Slightly slower and warmer than default
    utter.rate = 0.95;
    utter.pitch = 1.05;
    utter.volume = 1.0;

    speechSynthesis.speak(utter);
}

// ── Status Polling ──
function pollStatus() {
    fetch('/api/status')
        .then(r => r.json())
        .then(status => {
            setConnected();
            updateStatus(status);
            if (status.state === 'loading') {
                setTimeout(pollStatus, 2000);
            } else if (status.state === 'ready') {
                hideLoadingScreen();
                // Fetch initial session state to populate cocoon metrics panel
                fetch('/api/session')
                    .then(r => r.json())
                    .then(sessionState => {
                        if (sessionState && Object.keys(sessionState).length > 0) {
                            updateCocoonUI(sessionState);
                        }
                    })
                    .catch(() => {});
                // Load session list for sidebar
                loadSessions();
                // Populate welcome cocoon hint
                if (status.memory_count !== undefined) {
                    _startupCocoonCount = status.memory_count;
                    _updateStatusChips();
                }
                const hint = document.getElementById('welcome-cocoon-hint');
                if (hint && status.memory_count > 0) {
                    hint.innerHTML = `<span>&#128190; ${status.memory_count} memories loaded</span>`;
                }
                // Keep heartbeat running to detect disconnects
                setTimeout(pollStatus, 15000);
            } else if (status.state === 'error') {
                // Model failed to load — show error and dismiss loading screen
                hideLoadingScreen();
                updateStatus({ state: 'error', message: status.message || 'Model failed to load' });
            } else if (status.state === 'idle') {
                // Model not loaded yet, keep polling
                setTimeout(pollStatus, 3000);
            }
        })
        .catch(() => {
            setDisconnected();
            setTimeout(pollStatus, 5000);
        });
}

function setDisconnected() {
    if (serverConnected) {
        serverConnected = false;
        updateStatus({ state: 'error', message: 'Server disconnected' });
    }
}

function setConnected() {
    if (!serverConnected) {
        serverConnected = true;
        if (reconnectTimer) {
            clearInterval(reconnectTimer);
            reconnectTimer = null;
        }
    }
}

function updateStatus(status) {
    const dot = document.getElementById('status-dot');
    const text = document.getElementById('status-text');

    dot.className = 'status-dot ' + (status.state || 'loading');
    text.textContent = status.message || status.state;

    // Update loading screen
    const loadingStatus = document.getElementById('loading-status');
    if (loadingStatus) {
        loadingStatus.textContent = status.message || 'Loading...';
    }

    // Update adapter dots if available
    if (status.adapters) {
        updateAdapterDots(status.adapters);
    }
}

function _updateStatusChips() {
    const right = document.getElementById('status-right');
    if (!right) return;
    let html = '';
    if (_startupCocoonCount > 0) {
        html += `<span class="status-chip cocoon-active" title="Cocoon memories loaded">&#128190; ${_startupCocoonCount} cocoons</span>`;
    }
    if (_totalEthicalChecks > 0) {
        html += `<span class="status-chip ethical-pass" title="AEGIS ethical evaluations passed">&#10003; ${_totalEthicalChecks} checks</span>`;
    }
    right.innerHTML = html;
}

function hideLoadingScreen() {
    const screen = document.getElementById('loading-screen');
    if (screen) {
        screen.classList.add('hidden');
        setTimeout(() => screen.remove(), 500);
    }
}

// ── Adapter Dots ──
function initAdapterDots() {
    const container = document.getElementById('adapter-dots');
    Object.keys(LABELS).forEach(name => {
        const dot = document.createElement('span');
        dot.className = 'adapter-dot';
        dot.style.backgroundColor = COLORS[name];
        dot.title = name;
        dot.id = `dot-${name}`;
        container.appendChild(dot);
    });
}

function updateAdapterDots(available) {
    Object.keys(LABELS).forEach(name => {
        const dot = document.getElementById(`dot-${name}`);
        if (dot) {
            dot.classList.toggle('available', available.includes(name));
        }
    });
}

function setActiveAdapter(name) {
    // Remove previous active
    document.querySelectorAll('.adapter-dot').forEach(d => d.classList.remove('active'));
    // Set new active
    const dot = document.getElementById(`dot-${name}`);
    if (dot) dot.classList.add('active');

    // Update CSS accent color
    const color = COLORS[name] || COLORS._base;
    document.documentElement.style.setProperty('--accent', color);
    document.documentElement.style.setProperty('--accent-glow', color + '25');
}

// ── Coverage Dots ──
function initCoverageDots() {
    const container = document.getElementById('coverage-dots');
    Object.entries(LABELS).forEach(([name, label]) => {
        const dot = document.createElement('span');
        dot.className = 'coverage-dot';
        dot.style.color = COLORS[name];
        dot.textContent = label;
        dot.title = name;
        dot.id = `cov-${name}`;
        container.appendChild(dot);
    });
}

function updateCoverage(usage) {
    Object.keys(LABELS).forEach(name => {
        const dot = document.getElementById(`cov-${name}`);
        if (dot) {
            dot.classList.toggle('active', (usage[name] || 0) > 0);
        }
    });
}

// ── Chat ──
function sendMessage() {
    const input = document.getElementById('chat-input');
    const query = input.value.trim();
    if (!query || isLoading) return;

    // Hide welcome
    const welcome = document.getElementById('welcome');
    if (welcome) welcome.style.display = 'none';

    // Add user message
    addMessage('user', query);

    // Clear input
    input.value = '';
    input.style.height = 'auto';

    // Get settings
    const adapter = document.getElementById('adapter-select').value;
    const maxAdapters = parseInt(document.getElementById('max-adapters').value);

    // Show thinking
    const thinkingEl = showThinking(adapter);
    isLoading = true;
    document.getElementById('send-btn').disabled = true;

    // Send request with timeout (20 min for multi-perspective CPU inference)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 1200000);

    fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            query: query,
            adapter: adapter === 'auto' ? null : adapter,
            max_adapters: maxAdapters,
        }),
        signal: controller.signal,
    })
    .then(r => r.json())
    .then(data => {
        clearTimeout(timeoutId);
        thinkingEl.remove();

        if (data.error) {
            addMessage('error', data.error);
            return;
        }

        // Add assistant message
        const adapterUsed = data.adapter || '_base';
        setActiveAdapter(adapterUsed);

        addMessage('assistant', data.response, {
            adapter: adapterUsed,
            confidence: data.confidence,
            reasoning: data.reasoning,
            tokens: data.tokens,
            time: data.time,
            perspectives: data.perspectives,
            multi_perspective: data.multi_perspective,
            tools_used: data.tools_used,
            complexity: data.complexity,
            domain: data.domain,
            ethical_checks: data.ethical_checks || null,
        });

        // Update memory count from response
        if (data.memory_count) {
            _startupCocoonCount = data.memory_count;
            _updateStatusChips();
        }

        // Update ethical checks counter
        if (data.ethical_checks) {
            _totalEthicalChecks = data.ethical_checks;
            _updateStatusChips();
        }

        // Speak response if TTS is enabled
        const ttsOn = document.getElementById('tts-toggle');
        if (ttsOn && ttsOn.checked) {
            speakText(data.response);
        }

        // Update cocoon state
        if (data.cocoon) {
            updateCocoonUI(data.cocoon);
        }

        // Update epistemic metrics
        if (data.epistemic) {
            updateEpistemicUI(data.epistemic);
        }
    })
    .catch(err => {
        clearTimeout(timeoutId);
        thinkingEl.remove();
        if (err.name === 'AbortError') {
            addMessage('error', 'Request timed out. The model may be processing a complex query — try again or reduce perspectives.');
        } else if (err.message === 'Failed to fetch' || err.name === 'TypeError') {
            setDisconnected();
            addMessage('error', 'Server disconnected. Attempting to reconnect...');
            startReconnectPolling();
        } else {
            addMessage('error', `Request failed: ${err.message}`);
        }
    })
    .finally(() => {
        isLoading = false;
        document.getElementById('send-btn').disabled = false;
        document.getElementById('chat-input').focus();
    });
}

function askQuestion(query) {
    document.getElementById('chat-input').value = query;
    sendMessage();
}

function addMessage(role, content, meta = {}) {
    const area = document.getElementById('chat-area');
    const msg = document.createElement('div');
    msg.className = `message message-${role}`;

    if (role === 'user') {
        msg.innerHTML = `<div class="bubble"><div class="message-text">${escapeHtml(content)}</div></div>`;
    } else if (role === 'assistant') {
        const adapter = meta.adapter || '_base';
        const color = COLORS[adapter] || COLORS._base;
        const conf = meta.confidence || 0;
        const tps = meta.tokens && meta.time ? (meta.tokens / meta.time).toFixed(1) : '?';

        let html = `<div class="bubble" style="border-left-color:${color}">`;
        html += `<div class="message-header">`;
        html += `<span class="adapter-badge" style="color:${color}">${adapter}</span>`;
        html += `<div class="confidence-bar"><div class="confidence-fill" style="width:${conf*100}%;background:${color}"></div></div>`;
        html += `<span>${(conf*100).toFixed(0)}%</span>`;
        // Complexity badge
        if (meta.complexity && meta.complexity !== 'undefined') {
            const cxLevel = meta.complexity.toLowerCase().replace('querycomplexity.', '');
            html += `<span class="complexity-badge ${cxLevel}">${cxLevel}</span>`;
        }
        // Domain badge
        if (meta.domain && meta.domain !== 'general') {
            html += `<span class="domain-badge">${meta.domain}</span>`;
        }
        // Ethical check indicator
        if (meta.ethical_checks !== null && meta.ethical_checks !== undefined) {
            html += `<span class="ethical-check" title="${meta.ethical_checks} ethical evaluation(s) passed">&#10003; ethical</span>`;
        }
        html += `</div>`;
        html += `<div class="message-text">${renderMarkdown(content)}</div>`;
        html += `<div class="message-meta">${meta.tokens || '?'} tokens | ${tps} tok/s | ${(meta.time||0).toFixed(1)}s</div>`;

        // Tool usage indicator
        if (meta.tools_used && meta.tools_used.length > 0) {
            const toolNames = meta.tools_used.map(t => t.tool).join(', ');
            html += `<div class="tools-badge">🔧 Tools: ${toolNames}</div>`;
        }

        // Multi-perspective expandable
        if (meta.perspectives && Object.keys(meta.perspectives).length > 1) {
            const perspId = 'persp-' + Date.now();
            html += `<button class="perspectives-toggle" onclick="togglePerspectives('${perspId}')">`;
            html += `Show ${Object.keys(meta.perspectives).length} perspectives</button>`;
            html += `<div class="perspectives-panel" id="${perspId}">`;
            for (const [name, text] of Object.entries(meta.perspectives)) {
                const pc = COLORS[name] || COLORS._base;
                html += `<div class="perspective-card" style="border-left-color:${pc}">`;
                html += `<div class="perspective-card-header" style="color:${pc}">${name}</div>`;
                html += `<div>${renderMarkdown(text)}</div></div>`;
            }
            html += `</div>`;
        }

        html += `</div>`;
        msg.innerHTML = html;
    } else if (role === 'error') {
        msg.innerHTML = `<div class="bubble" style="border-left-color:var(--quantum)">
            <div class="message-text" style="color:var(--quantum)">${escapeHtml(content)}</div></div>`;
    }

    area.appendChild(msg);
    area.scrollTop = area.scrollHeight;
}

function showThinking(adapter) {
    const area = document.getElementById('chat-area');
    const el = document.createElement('div');
    el.className = 'thinking';

    const stages = [
        'Classifying query complexity\u2026',
        'Routing to best perspective\u2026',
        'Running ethical validation\u2026',
        'Synthesizing perspectives\u2026',
        'Encoding thought cocoon\u2026',
    ];

    const adapterHint = adapter && adapter !== 'auto' ? ` \u2014 ${adapter}` : '';

    el.innerHTML = `
        <div class="thinking-dots"><span></span><span></span><span></span></div>
        <span>Thinking${adapterHint}</span>
        <span class="thinking-stage">${stages[0]}</span>
    `;
    area.appendChild(el);
    area.scrollTop = area.scrollHeight;

    let stageIdx = 0;
    el._stageTimer = setInterval(() => {
        stageIdx = (stageIdx + 1) % stages.length;
        const stageEl = el.querySelector('.thinking-stage');
        if (stageEl) {
            stageEl.style.opacity = '0';
            setTimeout(() => {
                stageEl.textContent = stages[stageIdx];
                stageEl.style.opacity = '1';
            }, 150);
        }
    }, 2800);

    const originalRemove = el.remove.bind(el);
    el.remove = () => {
        clearInterval(el._stageTimer);
        originalRemove();
    };

    return el;
}

function togglePerspectives(id) {
    document.getElementById(id).classList.toggle('open');
}

// ── Cocoon UI Updates ──
function updateCocoonUI(state) {
    // Metrics
    const metrics = state.metrics || {};
    const coherence = metrics.current_coherence || 0;
    const tension = metrics.current_tension || 0;

    document.getElementById('metric-coherence').textContent = coherence.toFixed(4);
    document.getElementById('bar-coherence').style.width = (coherence * 100) + '%';

    document.getElementById('metric-tension').textContent = tension.toFixed(4);
    document.getElementById('bar-tension').style.width = Math.min(tension * 100, 100) + '%';

    document.getElementById('cocoon-attractors').textContent = metrics.attractor_count || 0;
    document.getElementById('cocoon-glyphs').textContent = metrics.glyph_count || 0;

    // Cocoon status
    const cocoon = state.cocoon || {};
    document.getElementById('cocoon-encryption').textContent =
        cocoon.has_sync ? 'Active' : 'Available';

    // AEGIS eta feeds the main eta metric when available
    if (state.aegis && state.aegis.eta !== undefined) {
        document.getElementById('metric-eta').textContent = state.aegis.eta.toFixed(4);
    }

    // Coverage
    updateCoverage(state.perspective_usage || {});

    // Spiderweb
    if (spiderwebViz && state.spiderweb) {
        spiderwebViz.update(state.spiderweb);
    }

    // New subsystem panels (AEGIS, Nexus, Memory, Resonance, Guardian)
    updateSubsystemUI(state);

    // Update status bar chips
    if (state.memory && state.memory.total_memories) {
        _startupCocoonCount = state.memory.total_memories;
    }
    if (state.aegis && state.aegis.total_evaluations) {
        _totalEthicalChecks = state.aegis.total_evaluations;
    }
    _updateStatusChips();
}

function updateEpistemicUI(epistemic) {
    if (epistemic.ensemble_coherence !== undefined) {
        const val = epistemic.ensemble_coherence;
        document.getElementById('metric-coherence').textContent = val.toFixed(4);
        document.getElementById('bar-coherence').style.width = (val * 100) + '%';
    }
    if (epistemic.tension_magnitude !== undefined) {
        const val = epistemic.tension_magnitude;
        document.getElementById('metric-tension').textContent = val.toFixed(4);
        document.getElementById('bar-tension').style.width = Math.min(val * 100, 100) + '%';
    }
    // Update ethical alignment if available
    if (epistemic.ethical_alignment !== undefined) {
        document.getElementById('metric-eta').textContent =
            epistemic.ethical_alignment.toFixed(3);
    } else if (epistemic.mean_coherence !== undefined) {
        // Fall back: derive eta from mean coherence as a proxy
        document.getElementById('metric-eta').textContent =
            epistemic.mean_coherence.toFixed(3);
    }
}

// ── Session Management ──
function newChat() {
    fetch('/api/session/new', { method: 'POST' })
        .then(r => r.json())
        .then(() => {
            // Clear chat
            const area = document.getElementById('chat-area');
            area.innerHTML = '';
            // Show welcome with starter cards
            const welcome = document.createElement('div');
            welcome.className = 'welcome';
            welcome.id = 'welcome';
            welcome.innerHTML = `
                <div class="welcome-avatar">
                    <div class="welcome-avatar-glyph">&#9775;</div>
                </div>
                <h2>Hello. I'm Codette.</h2>
                <p class="welcome-subtext">I'm curious, warm, and built to think from multiple angles at once. Ask me anything — I'll bring the right perspectives to it.</p>
                <div class="welcome-cocoon-hint" id="welcome-cocoon-hint">${_startupCocoonCount > 0 ? '<span>&#128190; ' + _startupCocoonCount + ' memories loaded</span>' : ''}</div>
                <div class="welcome-grid">
                    <div class="welcome-card" onclick="askQuestion('Explain why objects fall to the ground')">
                        <div class="welcome-card-title" style="color:var(--newton)">&#9883; Physics</div>
                        <div class="welcome-card-desc">Explain why objects fall to the ground</div>
                    </div>
                    <div class="welcome-card" onclick="askQuestion('Design a creative solution for sustainable cities')">
                        <div class="welcome-card-title" style="color:var(--davinci)">&#9784; Creativity</div>
                        <div class="welcome-card-desc">Design a creative solution for sustainable cities</div>
                    </div>
                    <div class="welcome-card" onclick="askQuestion('I\\'m feeling overwhelmed — can you help me think through it?')">
                        <div class="welcome-card-title" style="color:var(--empathy)">&#9825; Support</div>
                        <div class="welcome-card-desc">I'm feeling overwhelmed — can you help me think through it?</div>
                    </div>
                    <div class="welcome-card" onclick="askQuestion('What is consciousness and can AI have it?')">
                        <div class="welcome-card-title" style="color:var(--consciousness)">&#9670; Consciousness</div>
                        <div class="welcome-card-desc">What is consciousness and can AI have it?</div>
                    </div>
                </div>
            `;
            area.appendChild(welcome);
            // Reset metrics
            document.getElementById('metric-coherence').textContent = '0.00';
            document.getElementById('metric-tension').textContent = '0.00';
            document.getElementById('metric-eta').textContent = '--';
            document.getElementById('bar-coherence').style.width = '0%';
            document.getElementById('bar-tension').style.width = '0%';
            document.getElementById('cocoon-attractors').textContent = '0';
            document.getElementById('cocoon-glyphs').textContent = '0';
            // Reset subsystem panels
            ['section-aegis','section-nexus','section-resonance','section-memory','section-guardian'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.style.display = 'none';
            });
            // Reset spiderweb
            if (spiderwebViz) {
                spiderwebViz._initDefaultState();
                spiderwebViz.coherence = 0;
                spiderwebViz.attractors = [];
            }
            // Reset status chips
            _totalEthicalChecks = 0;
            _updateStatusChips();
            loadSessions();
        });
}

function loadSessions() {
    fetch('/api/sessions')
        .then(r => r.json())
        .then(data => {
            const list = document.getElementById('session-list');
            const sessions = data.sessions || [];
            document.getElementById('cocoon-sessions').textContent = sessions.length;

            list.innerHTML = sessions.map(s => `
                <div class="session-item" onclick="loadSession('${s.session_id}')"
                     title="${s.title}">
                    ${s.title || 'Untitled'}
                </div>
            `).join('');
        })
        .catch(() => {});
}

function loadSession(sessionId) {
    fetch('/api/session/load', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) return;

        // Clear and rebuild chat
        const area = document.getElementById('chat-area');
        area.innerHTML = '';

        (data.messages || []).forEach(msg => {
            addMessage(msg.role, msg.content, msg.metadata || {});
        });

        if (data.state) {
            updateCocoonUI(data.state);
        }
    })
    .catch(err => {
        console.log('Failed to load session:', err);
    });
}

// ── Session Export/Import ──
function exportSession() {
    fetch('/api/session/export', { method: 'POST' })
        .then(r => {
            if (!r.ok) throw new Error('Export failed');
            const disposition = r.headers.get('Content-Disposition') || '';
            const match = disposition.match(/filename="(.+)"/);
            const filename = match ? match[1] : 'codette_session.json';
            return r.blob().then(blob => ({ blob, filename }));
        })
        .then(({ blob, filename }) => {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            a.click();
            URL.revokeObjectURL(url);
        })
        .catch(err => {
            console.log('Export failed:', err);
        });
}

function importSession(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
        try {
            const data = JSON.parse(e.target.result);
            fetch('/api/session/import', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            })
            .then(r => r.json())
            .then(result => {
                if (result.error) {
                    addMessage('error', `Import failed: ${result.error}`);
                    return;
                }
                // Rebuild chat from imported session
                const area = document.getElementById('chat-area');
                area.innerHTML = '';
                (result.messages || []).forEach(msg => {
                    addMessage(msg.role, msg.content, msg.metadata || {});
                });
                if (result.state) {
                    updateCocoonUI(result.state);
                }
                loadSessions();
            })
            .catch(err => {
                addMessage('error', `Import failed: ${err.message}`);
            });
        } catch (parseErr) {
            addMessage('error', 'Invalid JSON file');
        }
    };
    reader.readAsText(file);
    // Reset file input so same file can be imported again
    event.target.value = '';
}

// ── Reconnection ──
function startReconnectPolling() {
    if (reconnectTimer) return; // Already polling
    reconnectTimer = setInterval(() => {
        fetch('/api/status')
            .then(r => r.json())
            .then(status => {
                setConnected();
                updateStatus(status);
                addMessage('error', 'Server reconnected!');
            })
            .catch(() => {
                // Still disconnected, keep polling
            });
    }, 5000);
}

// ── Subsystem UI Updates ──
function updateSubsystemUI(state) {
    updateAegisUI(state.aegis);
    updateNexusUI(state.nexus);
    updateResonanceUI(state.resonance);
    updateMemoryUI(state.memory);
    updateGuardianUI(state.guardian);
}

function updateAegisUI(aegis) {
    const section = document.getElementById('section-aegis');
    if (!aegis) { section.style.display = 'none'; return; }
    section.style.display = '';

    const eta = aegis.eta || 0;
    document.getElementById('aegis-eta').textContent = eta.toFixed(4);
    document.getElementById('bar-aegis-eta').style.width = (eta * 100) + '%';
    document.getElementById('aegis-evals').textContent = aegis.total_evaluations || 0;
    document.getElementById('aegis-vetoes').textContent = aegis.veto_count || 0;

    const trendEl = document.getElementById('aegis-trend');
    const trend = aegis.alignment_trend || '--';
    trendEl.textContent = trend;
    trendEl.className = 'metric-value';
    if (trend === 'improving') trendEl.classList.add('trend-improving');
    else if (trend === 'declining') trendEl.classList.add('trend-declining');
    else if (trend === 'stable') trendEl.classList.add('trend-stable');
}

function updateNexusUI(nexus) {
    const section = document.getElementById('section-nexus');
    if (!nexus) { section.style.display = 'none'; return; }
    section.style.display = '';

    document.getElementById('nexus-processed').textContent = nexus.total_processed || 0;
    document.getElementById('nexus-interventions').textContent = nexus.interventions || 0;
    const rate = (nexus.intervention_rate || 0) * 100;
    document.getElementById('nexus-rate').textContent = rate.toFixed(1) + '%';

    // Risk dots for recent signals
    const risksEl = document.getElementById('nexus-risks');
    const risks = nexus.recent_risks || [];
    risksEl.innerHTML = risks.map(r =>
        `<span class="risk-dot ${r}" title="${r} risk"></span>`
    ).join('');
}

function updateResonanceUI(resonance) {
    const section = document.getElementById('section-resonance');
    if (!resonance) { section.style.display = 'none'; return; }
    section.style.display = '';

    const psi = resonance.psi_r || 0;
    document.getElementById('resonance-psi').textContent = psi.toFixed(4);
    // Normalize psi_r to 0-100% bar (clamp between -2 and 2)
    const psiNorm = Math.min(100, Math.max(0, (psi + 2) / 4 * 100));
    document.getElementById('bar-resonance-psi').style.width = psiNorm + '%';

    document.getElementById('resonance-quality').textContent =
        (resonance.resonance_quality || 0).toFixed(4);
    document.getElementById('resonance-convergence').textContent =
        (resonance.convergence_rate || 0).toFixed(4);
    document.getElementById('resonance-stability').textContent =
        resonance.stability || '--';

    const peakEl = document.getElementById('resonance-peak');
    const atPeak = resonance.at_peak || false;
    peakEl.textContent = atPeak ? 'ACTIVE' : 'dormant';
    peakEl.className = 'metric-value' + (atPeak ? ' peak-active' : '');
}

function updateMemoryUI(memory) {
    const section = document.getElementById('section-memory');
    if (!memory) { section.style.display = 'none'; return; }
    section.style.display = '';

    document.getElementById('memory-count').textContent = memory.total_memories || 0;

    // Emotional profile tags
    const emotionsEl = document.getElementById('memory-emotions');
    const profile = memory.emotional_profile || {};
    const sorted = Object.entries(profile).sort((a, b) => b[1] - a[1]);
    emotionsEl.innerHTML = sorted.slice(0, 8).map(([emotion, count]) =>
        `<span class="emotion-tag${count > 0 ? ' active' : ''}" title="${count} memories">${emotion} ${count}</span>`
    ).join('');
}

function updateGuardianUI(guardian) {
    const section = document.getElementById('section-guardian');
    if (!guardian) { section.style.display = 'none'; return; }
    section.style.display = '';

    const ethics = guardian.ethics || {};
    document.getElementById('guardian-ethics').textContent =
        (ethics.ethical_score !== undefined) ? ethics.ethical_score.toFixed(4) : '--';
    const trust = guardian.trust || {};
    document.getElementById('guardian-trust').textContent =
        trust.total_interactions || 0;
}

// ── Utilities ──
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function renderMarkdown(text) {
    // Lightweight markdown renderer — no dependencies
    let html = escapeHtml(text);

    // Code blocks: ```lang\n...\n```
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g,
        '<pre class="code-block"><code>$2</code></pre>');

    // Inline code: `code`
    html = html.replace(/`([^`\n]+)`/g, '<code class="inline-code">$1</code>');

    // Bold: **text** or __text__
    html = html.replace(/\*\*([^*\n]+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/__([^_\n]+?)__/g, '<strong>$1</strong>');

    // Headers: ### text (on its own line) — before bullets to avoid conflict
    html = html.replace(/^### (.+)$/gm, '<div class="md-h3">$1</div>');
    html = html.replace(/^## (.+)$/gm, '<div class="md-h2">$1</div>');
    html = html.replace(/^# (.+)$/gm, '<div class="md-h1">$1</div>');

    // Bullet lists: - item or * item — before italic to prevent * conflicts
    html = html.replace(/^[\-\*] (.+)$/gm, '<div class="md-li">$1</div>');

    // Numbered lists: 1. item
    html = html.replace(/^\d+\. (.+)$/gm, '<div class="md-li md-oli">$1</div>');

    // Italic: *text* or _text_ — AFTER bullets, restricted to single line
    html = html.replace(/(?<!\w)\*([^*\n]+?)\*(?!\w)/g, '<em>$1</em>');
    html = html.replace(/(?<!\w)_([^_\n]+?)_(?!\w)/g, '<em>$1</em>');

    // Line breaks (preserve double newlines as paragraph breaks)
    html = html.replace(/\n\n/g, '<br><br>');
    html = html.replace(/\n/g, '<br>');

    return html;
}
