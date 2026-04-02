#!/usr/bin/env python3
"""Codette Chat UI — Tkinter Desktop Interface

Dark-themed chat app that wraps the CodetteOrchestrator.
Launch: double-click codette_chat.bat or run this file directly.
No terminal needed — uses threaded inference so UI stays responsive.
"""

import os, sys, time, threading, queue, traceback, subprocess, tempfile, wave, struct
import tkinter as tk
from tkinter import scrolledtext, font as tkfont

from runtime_env import bootstrap_environment

# ── Environment bootstrap ───────────────────────────────────────
bootstrap_environment()

# ── Theme ────────────────────────────────────────────────────────
BG          = "#0f0f1a"
BG_PANEL    = "#1a1a2e"
BG_INPUT    = "#252540"
BG_BTN      = "#3a3a5c"
BG_BTN_ACT  = "#52527a"
FG          = "#e0e0e0"
FG_DIM      = "#808899"
FG_USER     = "#ffffff"
FG_CODETTE  = "#9ecfff"
FG_ERROR    = "#ff6b6b"
FG_SUCCESS  = "#6bffa0"
ACCENT      = "#6a9fff"
BORDER      = "#2a2a44"

ADAPTER_COLORS = {
    "newton":               "#ffa040",
    "davinci":              "#b07ce8",
    "empathy":              "#e85050",
    "philosophy":           "#40d080",
    "quantum":              "#40c8d0",
    "consciousness":        "#ff70b8",
    "multi_perspective":    "#ffd040",
    "systems_architecture": "#90a0b0",
    "base":                 "#808899",
}


# ═════════════════════════════════════════════════════════════════
# Voice Engine — STT via SpeechRecognition, TTS via PowerShell SAPI
# ═════════════════════════════════════════════════════════════════
class VoiceEngine:
    """Handles speech-to-text and text-to-speech without blocking the UI."""

    def __init__(self):
        self.stt_available = False
        self.tts_available = False
        self.is_recording = False
        self._mic = None
        self._recognizer = None
        self._tts_process = None

        # Probe STT (sounddevice + speech_recognition)
        try:
            import sounddevice as sd
            import speech_recognition as sr
            self._sd = sd
            self._sr = sr
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = 300
            self._recognizer.dynamic_energy_threshold = True
            # Find a working input device
            devices = sd.query_devices()
            self._input_device = None
            for i, d in enumerate(devices):
                if d['max_input_channels'] > 0:
                    self._input_device = i
                    break
            self.stt_available = self._input_device is not None
            self._sample_rate = 16000  # Good for speech recognition
        except Exception:
            pass

        # Probe TTS (PowerShell SAPI5)
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Add-Type -AssemblyName System.Speech; "
                 "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                 "$s.GetInstalledVoices() | Select -First 1 -Expand VoiceInfo | Select Name"],
                capture_output=True, text=True, timeout=5,
            )
            self.tts_available = result.returncode == 0
        except Exception:
            pass

    def record_audio(self, duration_seconds=8, callback=None):
        """Record audio from mic, transcribe, call callback(text) or callback(None) on error.
        Runs in a thread — do NOT call from main thread."""
        if not self.stt_available:
            if callback:
                callback(None, "Speech recognition not available")
            return

        try:
            import numpy as np
            self.is_recording = True
            # Record raw audio
            audio_data = self._sd.rec(
                int(duration_seconds * self._sample_rate),
                samplerate=self._sample_rate,
                channels=1,
                dtype='int16',
                device=self._input_device,
            )
            # Wait for recording to finish (or be stopped)
            while self.is_recording and self._sd.get_stream().active:
                time.sleep(0.1)

            self._sd.stop()
            self.is_recording = False

            # Trim silence from end (crude but effective)
            audio_np = audio_data.flatten()
            # Find last non-silent sample (threshold 500)
            nonsilent = np.where(np.abs(audio_np) > 500)[0]
            if len(nonsilent) == 0:
                if callback:
                    callback(None, "No speech detected")
                return
            end_idx = min(nonsilent[-1] + self._sample_rate, len(audio_np))
            audio_trimmed = audio_np[:end_idx]

            # Convert to WAV bytes for SpeechRecognition
            wav_buffer = self._numpy_to_wav_bytes(audio_trimmed, self._sample_rate)

            # Transcribe
            sr = self._sr
            audio = sr.AudioData(wav_buffer, self._sample_rate, 2)  # 2 bytes per sample (int16)
            try:
                text = self._recognizer.recognize_google(audio)
                if callback:
                    callback(text, None)
            except sr.UnknownValueError:
                if callback:
                    callback(None, "Could not understand speech")
            except sr.RequestError as e:
                if callback:
                    callback(None, f"Speech API error: {e}")

        except Exception as e:
            self.is_recording = False
            if callback:
                callback(None, f"Recording error: {e}")

    def stop_recording(self):
        """Signal the recording loop to stop early."""
        self.is_recording = False
        try:
            self._sd.stop()
        except Exception:
            pass

    def speak(self, text, callback=None):
        """Speak text via PowerShell SAPI5. Non-blocking (runs in thread).
        callback() called when done."""
        if not self.tts_available or not text:
            if callback:
                callback()
            return

        def _speak():
            try:
                # Escape text for PowerShell
                safe_text = text.replace("'", "''").replace('"', '`"')
                # Limit length for TTS (don't read entire essays)
                if len(safe_text) > 1000:
                    safe_text = safe_text[:1000] + "... and so on."

                self._tts_process = subprocess.Popen(
                    ["powershell", "-Command",
                     f"Add-Type -AssemblyName System.Speech; "
                     f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                     f"$s.Rate = 1; "
                     f"$s.Speak('{safe_text}')"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self._tts_process.wait()
                self._tts_process = None
            except Exception:
                self._tts_process = None
            finally:
                if callback:
                    callback()

        threading.Thread(target=_speak, daemon=True).start()

    def stop_speaking(self):
        """Kill any running TTS process."""
        if self._tts_process:
            try:
                self._tts_process.terminate()
            except Exception:
                pass
            self._tts_process = None

    @staticmethod
    def _numpy_to_wav_bytes(audio_np, sample_rate):
        """Convert int16 numpy array to raw PCM bytes for SpeechRecognition AudioData."""
        return audio_np.astype('<i2').tobytes()


# ═════════════════════════════════════════════════════════════════
# Worker Thread — loads model and processes queries off-main-thread
# ═════════════════════════════════════════════════════════════════
def worker_main(cmd_q, res_q):
    """Background thread: load orchestrator, process queries."""
    try:
        res_q.put(("status", "Loading base model... (this takes ~60s)"))

        # Redirect stdout so orchestrator prints don't pop up
        import io
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        from codette_orchestrator import CodetteOrchestrator
        orch = CodetteOrchestrator(verbose=False)

        sys.stdout = old_stdout

        adapters = orch.available_adapters
        res_q.put(("ready", adapters))

    except Exception as e:
        try:
            sys.stdout = old_stdout
        except Exception:
            pass
        res_q.put(("error", f"Failed to load model:\n{e}\n{traceback.format_exc()}"))
        return

    # ── Command loop ────────────────────────────────────────────
    while True:
        try:
            cmd = cmd_q.get(timeout=0.5)
        except queue.Empty:
            continue

        if cmd is None or cmd == "quit":
            break

        action = cmd.get("action")

        if action == "generate":
            query = cmd["query"]
            adapter = cmd.get("adapter")       # None = auto
            max_adapters = cmd.get("max_adapters", 2)

            res_q.put(("thinking", adapter or "auto"))

            try:
                # Redirect stdout during generation
                old_stdout = sys.stdout
                sys.stdout = io.StringIO()

                if adapter and adapter != "auto":
                    force = adapter if adapter != "base" else None
                    result = orch.route_and_generate(
                        query,
                        max_adapters=1,
                        strategy="keyword",
                        force_adapter=force,
                    )
                else:
                    result = orch.route_and_generate(
                        query,
                        max_adapters=max_adapters,
                        strategy="keyword",
                    )

                sys.stdout = old_stdout
                res_q.put(("response", result))

            except Exception as e:
                try:
                    sys.stdout = old_stdout
                except Exception:
                    pass
                res_q.put(("error", f"Generation failed: {e}"))


# ═════════════════════════════════════════════════════════════════
# Main GUI
# ═════════════════════════════════════════════════════════════════
class CodetteChat:
    def __init__(self, root):
        self.root = root
        self.cmd_q = queue.Queue()
        self.res_q = queue.Queue()
        self.is_busy = False
        self.is_ready = False
        self.available_adapters = []
        self.thinking_dots = 0

        # Voice engine
        self.voice = VoiceEngine()
        self.tts_enabled = False
        self.is_recording = False

        self._setup_window()
        self._build_ui()
        self._start_worker()
        self._poll_results()

    # ── Window setup ────────────────────────────────────────────
    def _setup_window(self):
        self.root.title("Codette")
        self.root.geometry("800x700")
        self.root.minsize(600, 500)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Try to set a nice icon (won't fail if missing)
        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

    # ── Build all UI components ─────────────────────────────────
    def _build_ui(self):
        # Fonts
        self.font_title = tkfont.Font(family="Segoe UI", size=16, weight="bold")
        self.font_body  = tkfont.Font(family="Consolas", size=11)
        self.font_bold  = tkfont.Font(family="Consolas", size=11, weight="bold")
        self.font_small = tkfont.Font(family="Segoe UI", size=9)
        self.font_input = tkfont.Font(family="Consolas", size=12)
        self.font_btn   = tkfont.Font(family="Segoe UI", size=10, weight="bold")

        self._build_header()
        self._build_chat_area()
        self._build_controls()
        self._build_input_area()
        self._build_status_bar()

    # ── Header ──────────────────────────────────────────────────
    def _build_header(self):
        header = tk.Frame(self.root, bg=BG_PANEL, pady=8, padx=12)
        header.pack(fill=tk.X)

        tk.Label(
            header, text="Codette", font=self.font_title,
            bg=BG_PANEL, fg=ACCENT,
        ).pack(side=tk.LEFT)

        self.adapter_label = tk.Label(
            header, text="  Loading...", font=self.font_small,
            bg=BG_PANEL, fg=FG_DIM,
        )
        self.adapter_label.pack(side=tk.LEFT, padx=(12, 0))

        # Separator
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill=tk.X)

    # ── Chat area ───────────────────────────────────────────────
    def _build_chat_area(self):
        self.chat = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            bg=BG,
            fg=FG,
            font=self.font_body,
            insertbackground=FG,
            selectbackground="#3a3a5c",
            selectforeground=FG_USER,
            borderwidth=0,
            highlightthickness=0,
            padx=16,
            pady=12,
            state=tk.DISABLED,
            cursor="arrow",
        )
        self.chat.pack(fill=tk.BOTH, expand=True)

        # Configure text tags for coloring
        self.chat.tag_configure("user_label",   foreground=FG_USER,    font=self.font_bold)
        self.chat.tag_configure("user_text",    foreground=FG_USER,    font=self.font_body)
        self.chat.tag_configure("codette_label",foreground=FG_CODETTE, font=self.font_bold)
        self.chat.tag_configure("codette_text", foreground=FG_CODETTE, font=self.font_body,
                                lmargin1=8, lmargin2=8)
        self.chat.tag_configure("meta",         foreground=FG_DIM,     font=self.font_small)
        self.chat.tag_configure("error",        foreground=FG_ERROR,   font=self.font_body)
        self.chat.tag_configure("system",       foreground=FG_SUCCESS, font=self.font_small)
        self.chat.tag_configure("separator",    foreground="#2a2a44",   font=self.font_small)

        # Per-adapter color tags
        for name, color in ADAPTER_COLORS.items():
            self.chat.tag_configure(f"adapter_{name}", foreground=color, font=self.font_bold)

        # Show loading message
        self._append_system("Starting Codette... Loading base model (this takes ~60 seconds)")

    # ── Controls row ────────────────────────────────────────────
    def _build_controls(self):
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill=tk.X)

        controls = tk.Frame(self.root, bg=BG_PANEL, pady=6, padx=12)
        controls.pack(fill=tk.X)

        # Adapter selector
        tk.Label(
            controls, text="Adapter:", font=self.font_small,
            bg=BG_PANEL, fg=FG_DIM,
        ).pack(side=tk.LEFT)

        self.adapter_var = tk.StringVar(value="Auto")
        self.adapter_menu = tk.OptionMenu(
            controls, self.adapter_var, "Auto",
        )
        self.adapter_menu.configure(
            bg=BG_BTN, fg=FG, activebackground=BG_BTN_ACT,
            activeforeground=FG, font=self.font_small,
            highlightthickness=0, borderwidth=1, relief=tk.FLAT,
        )
        self.adapter_menu["menu"].configure(
            bg=BG_INPUT, fg=FG, activebackground=ACCENT,
            activeforeground="#000", font=self.font_small,
        )
        self.adapter_menu.pack(side=tk.LEFT, padx=(4, 16))

        # Max perspectives
        tk.Label(
            controls, text="Perspectives:", font=self.font_small,
            bg=BG_PANEL, fg=FG_DIM,
        ).pack(side=tk.LEFT)

        self.perspectives_var = tk.IntVar(value=2)
        for n in [1, 2, 3]:
            rb = tk.Radiobutton(
                controls, text=str(n), variable=self.perspectives_var, value=n,
                bg=BG_PANEL, fg=FG, selectcolor=BG_BTN,
                activebackground=BG_PANEL, activeforeground=ACCENT,
                font=self.font_small, highlightthickness=0,
            )
            rb.pack(side=tk.LEFT, padx=2)

        # Clear button
        tk.Button(
            controls, text="Clear", font=self.font_small,
            bg=BG_BTN, fg=FG_DIM, activebackground=BG_BTN_ACT,
            activeforeground=FG, relief=tk.FLAT, borderwidth=0,
            command=self._clear_chat, cursor="hand2",
        ).pack(side=tk.RIGHT)

        # TTS toggle
        if self.voice.tts_available:
            self.tts_var = tk.BooleanVar(value=False)
            self.tts_btn = tk.Checkbutton(
                controls, text="\U0001F50A TTS", variable=self.tts_var,
                font=self.font_small, bg=BG_PANEL, fg=FG_DIM,
                selectcolor=BG_BTN, activebackground=BG_PANEL,
                activeforeground=ACCENT, highlightthickness=0,
                command=self._toggle_tts, cursor="hand2",
            )
            self.tts_btn.pack(side=tk.RIGHT, padx=(0, 8))

    # ── Input area ──────────────────────────────────────────────
    def _build_input_area(self):
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill=tk.X)

        input_frame = tk.Frame(self.root, bg=BG_PANEL, padx=12, pady=8)
        input_frame.pack(fill=tk.X)

        self.input_box = tk.Text(
            input_frame,
            height=3,
            bg=BG_INPUT,
            fg=FG_USER,
            font=self.font_input,
            insertbackground=FG_USER,
            selectbackground=ACCENT,
            borderwidth=1,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightcolor=ACCENT,
            highlightbackground=BORDER,
            wrap=tk.WORD,
            padx=8,
            pady=6,
        )
        self.input_box.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.input_box.bind("<Return>", self._on_enter)
        self.input_box.insert("1.0", "")
        self.input_box.focus_set()

        # Button container (mic + send stacked vertically)
        btn_frame = tk.Frame(input_frame, bg=BG_PANEL)
        btn_frame.pack(side=tk.RIGHT)

        self.send_btn = tk.Button(
            btn_frame,
            text="Send",
            font=self.font_btn,
            bg=ACCENT,
            fg="#000000",
            activebackground="#8ab8ff",
            activeforeground="#000000",
            relief=tk.FLAT,
            borderwidth=0,
            width=8,
            height=1,
            command=self._send_message,
            cursor="hand2",
        )
        self.send_btn.pack(side=tk.TOP, pady=(0, 4))

        # Mic button (only if STT available)
        if self.voice.stt_available:
            self.mic_btn = tk.Button(
                btn_frame,
                text="\U0001F3A4 Mic",
                font=self.font_small,
                bg=BG_BTN,
                fg=FG,
                activebackground="#804040",
                activeforeground=FG_USER,
                relief=tk.FLAT,
                borderwidth=0,
                width=8,
                command=self._toggle_recording,
                cursor="hand2",
            )
            self.mic_btn.pack(side=tk.TOP)
        else:
            self.mic_btn = None

    # ── Status bar ──────────────────────────────────────────────
    def _build_status_bar(self):
        self.status_frame = tk.Frame(self.root, bg=BG, padx=12, pady=4)
        self.status_frame.pack(fill=tk.X)

        self.status_dot = tk.Label(
            self.status_frame, text="\u25cf", font=self.font_small,
            bg=BG, fg=FG_DIM,
        )
        self.status_dot.pack(side=tk.LEFT)

        self.status_label = tk.Label(
            self.status_frame, text=" Loading...", font=self.font_small,
            bg=BG, fg=FG_DIM, anchor=tk.W,
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # ── Worker management ───────────────────────────────────────
    def _start_worker(self):
        t = threading.Thread(target=worker_main, args=(self.cmd_q, self.res_q), daemon=True)
        t.start()

    def _poll_results(self):
        """Check result queue every 100ms."""
        try:
            while not self.res_q.empty():
                kind, data = self.res_q.get_nowait()
                self._handle_result(kind, data)
        except queue.Empty:
            pass

        # Animate thinking dots
        if self.is_busy:
            self.thinking_dots = (self.thinking_dots + 1) % 4
            dots = "." * self.thinking_dots
            adapter_hint = getattr(self, '_thinking_adapter', 'auto')
            self._set_status(f"Thinking{dots}  [{adapter_hint}]", ACCENT)

        self.root.after(100, self._poll_results)

    def _handle_result(self, kind, data):
        if kind == "status":
            self._set_status(data, FG_DIM)

        elif kind == "ready":
            self.is_ready = True
            self.available_adapters = data
            self._set_status(
                f"Ready | adapters: {', '.join(data) if data else 'base only'}",
                FG_SUCCESS,
            )
            self._update_adapter_menu(data)
            self.adapter_label.configure(
                text=f"  [{', '.join(data)}]" if data else "  [base]",
                fg=FG_DIM,
            )
            self._append_system(
                f"Model loaded! Available adapters: {', '.join(data) if data else 'base only'}\n"
                f"Type a question below. The router will pick the best perspective automatically."
            )
            self._set_busy(False)

        elif kind == "thinking":
            self._thinking_adapter = data

        elif kind == "response":
            self._append_response(data)
            self._set_busy(False)

            # Speak response if TTS enabled
            response_text = data.get("response", "")
            if response_text:
                self._speak_response(response_text)

            route = data.get("route")
            adapter = data.get("adapter", "?")
            tokens = data.get("tokens", 0)
            elapsed = data.get("time", 0)
            tps = tokens / elapsed if elapsed > 0 else 0
            conf = route.confidence if route else 0

            if "perspectives" in data and len(data.get("perspectives", {})) > 1:
                adapters_used = ", ".join(data["perspectives"].keys())
                self._set_status(
                    f"Done | {adapters_used} | {tokens} tok | {tps:.1f} tok/s",
                    FG_SUCCESS,
                )
            else:
                self._set_status(
                    f"Done | {adapter} (conf={conf:.2f}) | {tokens} tok | {tps:.1f} tok/s",
                    FG_SUCCESS,
                )

        elif kind == "error":
            self._append_error(str(data))
            self._set_busy(False)
            self._set_status(f"Error", FG_ERROR)

    # ── Adapter dropdown update ─────────────────────────────────
    def _update_adapter_menu(self, adapters):
        menu = self.adapter_menu["menu"]
        menu.delete(0, tk.END)

        choices = ["Auto"] + [a.capitalize() for a in adapters] + ["Base"]
        for choice in choices:
            menu.add_command(
                label=choice,
                command=lambda v=choice: self.adapter_var.set(v),
            )

    # ── Input handling ──────────────────────────────────────────
    def _on_enter(self, event):
        if event.state & 0x1:  # Shift+Enter → newline
            return None
        self._send_message()
        return "break"

    def _send_message(self):
        if self.is_busy or not self.is_ready:
            return

        text = self.input_box.get("1.0", tk.END).strip()
        if not text:
            return

        self.input_box.delete("1.0", tk.END)
        self._append_user(text)
        self._set_busy(True)

        # Determine adapter
        adapter_choice = self.adapter_var.get()
        if adapter_choice == "Auto":
            adapter = None  # Let router decide
        elif adapter_choice == "Base":
            adapter = "base"
        else:
            adapter = adapter_choice.lower()

        self.cmd_q.put({
            "action": "generate",
            "query": text,
            "adapter": adapter,
            "max_adapters": self.perspectives_var.get(),
        })

    # ── Chat display helpers ────────────────────────────────────
    def _append_user(self, text):
        self.chat.configure(state=tk.NORMAL)
        self.chat.insert(tk.END, "\n You\n", "user_label")
        self.chat.insert(tk.END, f" {text}\n", "user_text")
        self.chat.configure(state=tk.DISABLED)
        self.chat.see(tk.END)

    def _append_response(self, result):
        self.chat.configure(state=tk.NORMAL)

        # Multi-perspective response
        if "perspectives" in result and len(result.get("perspectives", {})) > 1:
            self.chat.insert(tk.END, "\n")

            # Show each perspective
            for name, text in result["perspectives"].items():
                color_tag = f"adapter_{name}"
                if not self.chat.tag_names().__contains__(color_tag):
                    color = ADAPTER_COLORS.get(name, FG_CODETTE)
                    self.chat.tag_configure(color_tag, foreground=color, font=self.font_bold)

                self.chat.insert(tk.END, f" Codette [{name}]\n", color_tag)
                self.chat.insert(tk.END, f" {text}\n\n", "codette_text")

            # Show synthesis
            self.chat.insert(
                tk.END,
                " \u2500\u2500\u2500 Synthesized \u2500\u2500\u2500\n",
                "separator",
            )
            self.chat.insert(tk.END, f" {result['response']}\n", "codette_text")

        else:
            # Single adapter response
            route = result.get("route")
            adapter = result.get("adapter", "base")
            conf = route.confidence if route else 0
            color_tag = f"adapter_{adapter}"
            if not self.chat.tag_names().__contains__(color_tag):
                color = ADAPTER_COLORS.get(adapter, FG_CODETTE)
                self.chat.tag_configure(color_tag, foreground=color, font=self.font_bold)

            self.chat.insert(tk.END, "\n")
            self.chat.insert(tk.END, f" Codette [{adapter}]", color_tag)
            self.chat.insert(tk.END, f"  conf={conf:.2f}\n", "meta")
            self.chat.insert(tk.END, f" {result['response']}\n", "codette_text")

        self.chat.configure(state=tk.DISABLED)
        self.chat.see(tk.END)

    def _append_system(self, text):
        self.chat.configure(state=tk.NORMAL)
        self.chat.insert(tk.END, f"\n {text}\n", "system")
        self.chat.configure(state=tk.DISABLED)
        self.chat.see(tk.END)

    def _append_error(self, text):
        self.chat.configure(state=tk.NORMAL)
        self.chat.insert(tk.END, f"\n Error: {text}\n", "error")
        self.chat.configure(state=tk.DISABLED)
        self.chat.see(tk.END)

    def _clear_chat(self):
        self.chat.configure(state=tk.NORMAL)
        self.chat.delete("1.0", tk.END)
        self.chat.configure(state=tk.DISABLED)

    # ── Status bar ──────────────────────────────────────────────
    def _set_status(self, text, color=FG_DIM):
        self.status_label.configure(text=f" {text}", fg=color)
        dot_color = FG_SUCCESS if "Ready" in text or "Done" in text else (
            ACCENT if "Thinking" in text else (FG_ERROR if "Error" in text else FG_DIM)
        )
        self.status_dot.configure(fg=dot_color)

    def _set_busy(self, busy):
        self.is_busy = busy
        state = tk.DISABLED if busy else tk.NORMAL
        self.send_btn.configure(state=state)
        if busy:
            self.input_box.configure(bg="#1e1e30")
        else:
            self.input_box.configure(bg=BG_INPUT)
            self.input_box.focus_set()

    # ── Voice: Recording (STT) ───────────────────────────────────
    def _toggle_recording(self):
        """Toggle mic recording on/off."""
        if not self.voice.stt_available or not self.is_ready:
            return

        if self.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        """Begin recording from mic."""
        self.is_recording = True
        if self.mic_btn:
            self.mic_btn.configure(bg="#cc3333", fg=FG_USER, text="\u23F9 Stop")
        self._set_status("Recording... click Stop or wait 8s", "#cc3333")

        def on_result(text, error):
            # Called from recording thread — schedule UI update
            self.root.after(0, self._handle_stt_result, text, error)

        threading.Thread(
            target=self.voice.record_audio,
            kwargs={"duration_seconds": 8, "callback": on_result},
            daemon=True,
        ).start()

    def _stop_recording(self):
        """Stop recording early."""
        self.is_recording = False
        self.voice.stop_recording()
        if self.mic_btn:
            self.mic_btn.configure(bg=BG_BTN, fg=FG, text="\U0001F3A4 Mic")

    def _handle_stt_result(self, text, error):
        """Process STT result on the main thread."""
        self.is_recording = False
        if self.mic_btn:
            self.mic_btn.configure(bg=BG_BTN, fg=FG, text="\U0001F3A4 Mic")

        if error:
            self._set_status(f"Voice: {error}", FG_ERROR)
            return

        if text:
            # Insert transcribed text into input box
            current = self.input_box.get("1.0", tk.END).strip()
            if current:
                self.input_box.insert(tk.END, " " + text)
            else:
                self.input_box.delete("1.0", tk.END)
                self.input_box.insert("1.0", text)
            self._set_status(f"Voice: \"{text}\"", FG_SUCCESS)
            self.input_box.focus_set()

    # ── Voice: TTS ────────────────────────────────────────────────
    def _toggle_tts(self):
        """Toggle text-to-speech on responses."""
        self.tts_enabled = self.tts_var.get()
        if self.tts_enabled:
            self._set_status("TTS enabled — responses will be spoken", FG_SUCCESS)
        else:
            self.voice.stop_speaking()
            self._set_status("TTS disabled", FG_DIM)

    def _speak_response(self, text):
        """Speak response text if TTS is enabled."""
        if self.tts_enabled and self.voice.tts_available:
            self.voice.speak(text)

    # ── Cleanup ─────────────────────────────────────────────────
    def _on_close(self):
        self.voice.stop_speaking()
        self.voice.stop_recording()
        self.cmd_q.put("quit")
        self.root.after(300, self.root.destroy)


# ═════════════════════════════════════════════════════════════════
# Entry point
# ═════════════════════════════════════════════════════════════════
def main():
    root = tk.Tk()
    app = CodetteChat(root)
    root.mainloop()


if __name__ == "__main__":
    main()
