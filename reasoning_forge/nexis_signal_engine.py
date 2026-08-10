import json
import os
import hashlib
import numpy as np
from collections import defaultdict
from datetime import datetime, timedelta
try:
    import filelock
except ImportError:  # optional: locking degrades to a no-op (single-process use)
    class _NullLock:
        def __init__(self, *a, **k): pass
        def acquire(self, *a, **k): pass
        def release(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
    class _NullFileLock:
        FileLock = _NullLock
        Timeout = TimeoutError
    filelock = _NullFileLock()
import pathlib
import shutil
import sqlite3
try:
    from rapidfuzz import fuzz
except ImportError:  # optional: degrade to exact matching
    class _ExactFuzz:
        @staticmethod
        def ratio(a, b):
            return 100.0 if a == b else 0.0
    fuzz = _ExactFuzz()
import unittest
import secrets
import re
try:
    import nltk
    from nltk.tokenize import word_tokenize
    from nltk.stem import WordNetLemmatizer
except ImportError:  # optional: falls back to whitespace tokenisation
    nltk = None
    word_tokenize = str.split
    class WordNetLemmatizer:            # minimal stand-in
        def lemmatize(self, token):
            return token
import logging
import time
try:
    from tenacity import retry, stop_after_attempt, wait_exponential
except ImportError:  # optional: no automatic retry
    def retry(*a, **k):
        def deco(fn):
            return fn
        return deco
    def stop_after_attempt(*a, **k): return None
    def wait_exponential(*a, **k): return None
from concurrent.futures import ThreadPoolExecutor

# Download required NLTK data (skipped entirely when nltk is unavailable).
#
# 2026-08-03: this block probed for 'tokenizers/punkt' and, finding it, did
# nothing. NLTK >=3.9 renamed the tokenizer tables to 'punkt_tab', and
# word_tokenize() now loads THAT. So the guard passed, punkt_tab was never
# fetched, and every single call to NexisSignalEngine.process() raised
# LookupError.
#
# That failure was invisible: forge_engine wraps the call in a bare
# `except Exception` that logs at DEBUG. The consequences were not cosmetic —
# `safety_notes['intent_risk']` was never populated, and the NEXUS_SIGNAL and
# EPISTEMIC_METRICS reasoning-trace events never fired at all. An intent and
# corruption-risk signal that silently never runs is worse than one that is
# absent, because everything downstream reads as "no risk detected".
#
# Each resource is probed and fetched independently, so one missing item cannot
# mask another, and both the old and new tokenizer names are accepted.
if nltk is not None:
    _NLTK_RESOURCES = [
        ('tokenizers/punkt_tab', 'punkt_tab'),   # NLTK >= 3.9
        ('tokenizers/punkt', 'punkt'),           # older NLTK
        ('corpora/wordnet', 'wordnet'),
    ]
    for _probe, _package in _NLTK_RESOURCES:
        try:
            nltk.data.find(_probe)
        except LookupError:
            try:
                nltk.download(_package, quiet=True)
            except Exception as _e:  # offline, or the name is gone in this version
                logging.getLogger(__name__).warning(
                    "NLTK resource %r unavailable (%s); NexisSignalEngine "
                    "tokenisation may fail", _package, _e)
        except Exception:
            pass

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s -%(message)s')
logger = logging.getLogger(__name__)

class Metrics:
    """Process-time and error counters for NexisSignalEngine.

    RECOVERED 2026-08-10, verbatim, from a divergent copy of this engine found at
    `OneDrive_2_8-10-2026.zip!Nexus/import json.py` (byte-identical twin at
    `codette_remaining_files.zip!nexus23.py`). That copy shares 47 of 63 symbols
    with this file; `Metrics` and its four call-sites were among the symbols it
    had and this one did not. See docs/RECOVERY_2026-08-10.md.

    `process()` already measured `time.perf_counter()` on both of its return
    paths and logged the result, so the duration existed but was not retrievable
    by anything. This makes it queryable.
    """

    def __init__(self):
        self.process_times = []
        self.error_count = 0

    def record_process_time(self, duration):
        self.process_times.append(duration)
        if len(self.process_times) > 1000:
            self.process_times.pop(0)

    def record_error(self):
        self.error_count += 1

    def get_stats(self):
        return {
            "avg_process_time": sum(self.process_times) / max(len(self.process_times), 1),
            "error_count": self.error_count
        }


class LockManager:
    """Abstract locking mechanism for file or database operations. """
    def __init__(self, lock_path):
        self.lock = filelock.FileLock(lock_path, timeout=10)

    def __enter__(self):
        self.lock.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()

class NexisSignalEngine:
    def __init__(self, memory_path, entropy_threshold=0.08, config_path="config.json" ,
max_memory_entries=10000, memory_ttl_days=30, fuzzy_threshold=80,
max_db_size_mb=100):
        """
        Initialize the NexisSignalEngine for signal processing and analysis.

        Args:
            memory_path (str): Path to SQLite database for storing signal data.
            entropy_threshold (float): Threshold for high entropy detection.
            config_path (str): Path to JSON file with term configurations.
            max_memory_entries (int): Maximum number of entries in memory before rotation.
            memory_ttl_days (int): Days after which memory entries expire.
            fuzzy_threshold (int): Fuzzy matching similarity threshold (0-100).
            max_db_size_mb (int): Maximum database size in MB before rotation.
        """
        self.memory_path = self._validate_path(memory_path)
        self.entropy_threshold = entropy_threshold
        self.max_memory_entries = max_memory_entries
        self.memory_ttl = timedelta(days=memory_ttl_days)
        self.fuzzy_threshold = fuzzy_threshold
        self.max_db_size_mb = max_db_size_mb
        self.lemmatizer = WordNetLemmatizer()
        self.token_cache = {}
        self.config = self._load_config(config_path)
        self.cache = defaultdict(list)
        self.metrics = Metrics()
        self.perspectives = ["Colleen", "Luke", "Kellyanne"]
        self._init_sqlite()          # create schema before first read
        self.memory = self._load_memory()

    def _validate_path(self, path):
        """Ensure memory_path is a valid, safe file path. """
        path = pathlib.Path(path).resolve()
        if not path.suffix == '.db':
            raise ValueError("Memory path must be a .db file")
        return str(path)

    def _load_config(self, config_path):
        """Load term configurations from a JSON file or use defaults, validate keys. """
        default_config = {
            "ethical_terms": ["hope" , "truth" , "resonance" , "repair"],
            "entropic_terms": ["corruption" , "instability" , "malice" , "chaos"],
            "risk_terms": ["manipulate" , "exploit" , "bypass" , "infect" , "override"],
            "virtue_terms": ["hope" , "grace" , "resolve"]
        }
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                default_config.update(config)
            except json.JSONDecodeError:
                logger.warning(f"Invalid config file at {config_path}. Using defaults. ")
        required_keys = ["ethical_terms" , "entropic_terms" , "risk_terms" , "virtue_terms"]
        missing_keys = [k for k in required_keys if k not in default_config or not
default_config[k]]
        if missing_keys:
            raise ValueError(f"Config missing required keys: {missing_keys}")
        return default_config

    def _init_sqlite(self):
        """Initialize SQLite database with memory and FTS tables. """
        with sqlite3.connect(self.memory_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory (
                    hash TEXT PRIMARY KEY ,
                    record JSON,
                    timestamp TEXT ,
                    integrity_hash TEXT,
                    fts_rowid INTEGER
                )
            """)
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts
                USING FTS5(input, intent_signature, reasoning, verdict)
            """)
            conn.commit()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1,
max=10))
    def _load_memory(self):
        """Load memory from SQLite database. """
        memory = {}
        try:
            with sqlite3.connect(self.memory_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT hash, record, integrity_hash FROM memory")
                for hash_val, record_json, integrity_hash in cursor.fetchall():
                    record = json.loads(record_json)
                    computed_hash = hashlib.sha256(json.dumps(record,
sort_keys=True).encode()).hexdigest()
                    if computed_hash != integrity_hash:
                        logger.warning(f"Tampered record detected for hash {hash_val}")
                        continue
                    memory[hash_val] = record
        except sqlite3.Error as e:
            logger.error(f"Error loading memory: {e}")
        return memory

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1,
max=10))
    def _save_memory(self):
        """Save memory to SQLite with integrity hashes and thread-safe locking. """
        def default_serializer(o):
            if isinstance(o, complex):
                return {"real": o.real, "imag": o.imag}
            if isinstance(o, np.ndarray):
                return o.tolist()
            if isinstance(o, (np.int64, np.float64)):
                return int(o) if o.is_integer() else float(o)
            raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")

        with LockManager(f"{self.memory_path}.lock"):
            with sqlite3.connect(self.memory_path) as conn:
                cursor = conn.cursor()
                for hash_val, record in self.memory.items():
                    record_json = json.dumps(record, default=default_serializer)
                    integrity_hash = hashlib.sha256(json.dumps(record, sort_keys=True,
default=default_serializer).encode()).hexdigest()
                    intent_signature = record.get('intent_signature' , {})
                    intent_str = f"suspicion_score:{intent_signature.get('suspicion_score' , 0)}entropy_index:{intent_signature.get('entropy_index' , 0)}"
                    reasoning = record.get('reasoning' , {})
                    reasoning_str = " " .join(f"{k}:{v}" for k, v in reasoning.items())
                    cursor.execute("""
                        INSERT OR REPLACE INTO memory (hash, record, timestamp, integrity_hash, fts_rowid)
                        VALUES (?, ?, ?, ?, ?)
                    """ , (hash_val, record_json, record['timestamp'], integrity_hash,
                            self._fts_rowid(hash_val)))
                    cursor.execute("""
                        INSERT OR REPLACE INTO memory_fts (rowid, input, intent_signature,
reasoning, verdict)
                        VALUES (?, ?, ?, ?, ?)
                    """ , (
                        self._fts_rowid(hash_val),
                        record['input'],
                        intent_str,
                        reasoning_str,
                        record.get('verdict' , '')
                    ))
                conn.commit()

    def _prune_and_rotate_memory(self):
        """Prune expired entries and rotate memory database if needed. """
        now = datetime.utcnow()
        with LockManager(f"{self.memory_path}.lock"):
            with sqlite3.connect(self.memory_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM memory
                    WHERE timestamp < ?
                """ , ((now - self.memory_ttl).isoformat(),))
                cursor.execute("DELETE FROM memory_fts WHERE rowid NOT IN (SELECT fts_rowid FROM memory)")
                conn.commit()
                cursor.execute("SELECT COUNT(*) FROM memory")
                count = cursor.fetchone()[0]
                db_size_mb = os.path.getsize(self.memory_path) / (1024 * 1024)
                if count >= self.max_memory_entries or db_size_mb >= self.max_db_size_mb:
                    self._rotate_memory_file()
                    cursor.execute("DELETE FROM memory")
                    cursor.execute("DELETE FROM memory_fts")
                    conn.commit()
                    self.memory = {}

    def _rotate_memory_file(self):
        """Archive current memory database and start a new one. """
        archive_path =f"{self.memory_path}.{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.bak"
        if os.path.exists(self.memory_path):
            shutil.move(self.memory_path, archive_path)
        self._init_sqlite()

    @staticmethod
    def _fts_rowid(hash_val):
        """Stable 60-bit integer from a hex digest — FTS5 rowid must be INTEGER."""
        return int(hash_val[:15], 16)

    def _hash(self, signal):
        """Compute SHA-256 hash of the input signal. """
        return hashlib.sha256(signal.encode()).hexdigest()

    def _rotate_vector(self, signal):
        """
        Apply a 45-degree rotation to a 2D complex vector derived from the signal.
        Deterministic: the same signal always yields the same vector.

        NOTE: this previously used secrets.SystemRandom().seed(seed).  SystemRandom
        draws from os.urandom and its seed() is a documented no-op, so the seed was
        silently ignored and repeated calls returned different vectors -- which
        test_rotate_vector asserts against.  default_rng is seeded and, unlike
        np.random.seed, does not mutate global RNG state.
        """
        seed = int(self._hash(signal)[:8], 16) % (2**32)
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(2) + 1j * rng.standard_normal(2)
        theta = np.pi / 4
        rot = np.array([[np.cos(theta), -np.sin(theta)],
                        [np.sin(theta), np.cos(theta)]])
        rotated = np.dot(rot, vec)
        return rotated, [{"real": v.real, "imag": v.imag} for v in vec]

    def _entanglement_tensor(self, signal_vec):
        """
        Apply a correlation matrix to simulate entanglement of signal vectors.
        Uses a fixed 2x2 matrix to model interaction.
        """
        matrix = np.array([[1, 0.5], [0.5, 1]])
        return np.dot(matrix, signal_vec)

    def _resonance_equation(self, signal):
        """
        Compute normalized frequency spectrum of alphabetic characters in the signal.
        Caps input length to prevent attack vectors; returns zeros if no alphabetic chars.
        """
        freqs = [ord(c) % 13 for c in signal[:1000] if c.isalpha()]
        if not freqs:
            return [0.0, 0.0, 0.0]
        spectrum = np.fft.fft(freqs)
        norm = np.linalg.norm(spectrum.real)
        normalized = spectrum.real / (norm if norm != 0 else 1)
        return normalized[:3].tolist()

    def _tokenize_and_lemmatize(self, signal_lower):
        """Tokenize and lemmatize the signal, including n-gram scanning for obfuscation. """
        if signal_lower in self.token_cache:
            return self.token_cache[signal_lower]
        tokens = word_tokenize(signal_lower)
        lemmatized = [self.lemmatizer.lemmatize(token) for token in tokens]
        # De-obfuscated forms: strip separators injected to evade term matching
        # ("tru/th" -> "truth").  Without these the n-grams below are too short
        # (2-3 chars) to ever reconstruct a full term.
        stripped = []
        for token in tokens:
            bare = re.sub(r'[^a-z]', '', token)
            if bare and bare != token:
                stripped.append(self.lemmatizer.lemmatize(bare))
            # collapse padded repeats ("hopee" -> "hope")
            collapsed = re.sub(r'(.)\1+', r'\1', bare or token)
            if collapsed and collapsed != token:
                stripped.append(self.lemmatizer.lemmatize(collapsed))
        joined = re.sub(r'[^a-z]', '', signal_lower)
        if joined:
            stripped.append(joined)
        ngrams = []
        for n in range(2, 4):  # 2-3 character n-grams
            for i in range(len(signal_lower) - n + 1):
                ngram = signal_lower[i:i+n]
                ngrams.append(self.lemmatizer.lemmatize(re.sub(r'[^a-z]' , '' , ngram)))
        result = lemmatized + stripped + [ng for ng in ngrams if ng]
        self.token_cache[signal_lower] = result
        return result

    def _entropy(self, signal_lower, tokens):
        """Calculate entropy based on fuzzy-matched entropic term frequency. """
        unique = set(tokens)
        term_count = 0
        for term in self.config["entropic_terms"]:
            lemmatized_term = self.lemmatizer.lemmatize(term)
            for token in tokens:
                if fuzz.ratio(lemmatized_term, token) >= self.fuzzy_threshold:
                    term_count += 1
        return term_count / max(len(unique), 1)

    def _tag_ethics(self, signal_lower, tokens):
        """Tag signal as aligned if it contains fuzzy-matched ethical terms. """
        for term in self.config["ethical_terms"]:
            lemmatized_term = self.lemmatizer.lemmatize(term)
            for token in tokens:
                if fuzz.ratio(lemmatized_term, token) >= self.fuzzy_threshold:
                    return "aligned"
        return "unaligned"

    def _predict_intent_vector(self, signal_lower, tokens=None):
        """
        Backward-compatible signature: external callers (e.g. tier2_bridge) invoke
        this with the raw query only, as the pre-hardening engine allowed.  When
        tokens are omitted we lower-case and tokenise here.
        """
        if tokens is None:
            signal_lower = signal_lower.lower()
            tokens = self._tokenize_and_lemmatize(signal_lower)
        """Predict intent based on risk, entropy, ethics, and harmonic volatility. """
        suspicion_score = 0
        for term in self.config["risk_terms"]:
            lemmatized_term = self.lemmatizer.lemmatize(term)
            for token in tokens:
                if fuzz.ratio(lemmatized_term, token) >= self.fuzzy_threshold:
                    suspicion_score += 1
        entropy_index = round(self._entropy(signal_lower, tokens), 3)
        ethical_alignment = self._tag_ethics(signal_lower, tokens)
        harmonic_profile = self._resonance_equation(signal_lower)
        volatility = round(np.std(harmonic_profile), 3)

        risk = "high" if (suspicion_score > 1 or volatility > 2.0 or entropy_index >
self.entropy_threshold) else "low"
        return {
            "suspicion_score": suspicion_score,
            "entropy_index": entropy_index,
            "ethical_alignment": ethical_alignment,
            "harmonic_volatility": volatility,
            "pre_corruption_risk": risk
        }

    def _universal_reasoning(self, signal, tokens):
        """Apply multiple reasoning frameworks to evaluate signal integrity. """
        frames = ["utilitarian" , "deontological" , "virtue" , "systems"]
        results, score = {}, 0

        for frame in frames:
            if frame == "utilitarian":
                repair_count = sum(1 for token in tokens if
fuzz.ratio(self.lemmatizer.lemmatize("repair"), token) >= self.fuzzy_threshold)
                corruption_count = sum(1 for token in tokens if
fuzz.ratio(self.lemmatizer.lemmatize("corruption"), token) >= self.fuzzy_threshold)
                val = repair_count - corruption_count
                result = "positive" if val >= 0 else "negative"
            elif frame == "deontological":
                truth_present = any(fuzz.ratio(self.lemmatizer.lemmatize("truth"), token) >=
self.fuzzy_threshold for token in tokens)
                chaos_present = any(fuzz.ratio(self.lemmatizer.lemmatize("chaos"), token) >=
self.fuzzy_threshold for token in tokens)
                result = "valid" if truth_present and not chaos_present else "violated"
            elif frame == "virtue":
                ok = any(any(fuzz.ratio(self.lemmatizer.lemmatize(t), token) >= self.fuzzy_threshold
for token in tokens) for t in self.config["virtue_terms"])
                result = "aligned" if ok else "misaligned"
            elif frame == "systems":
                result = "stable" if "::" in signal else "fragmented"

            results[frame] = result
            if result in ["positive" , "valid" , "aligned" , "stable"]:
                score += 1

        verdict = "approved" if score >= 2 else "blocked"
        return results, verdict

    def _perspective_colleen(self, signal):
        """Colleen's perspective: Transform signal into a rotated complex vector. """
        vec, vec_serialized = self._rotate_vector(signal)
        return {"agent": "Colleen" , "vector": vec_serialized}

    def _perspective_luke(self, signal_lower, tokens):
        """Luke's perspective: Evaluate ethics, entropy, and stability state. """
        ethics = self._tag_ethics(signal_lower, tokens)
        entropy_level = self._entropy(signal_lower, tokens)
        state = "stabilized" if entropy_level < self.entropy_threshold else "diffused"
        return {"agent": "Luke" , "ethics": ethics, "entropy": entropy_level, "state": state}

    def _perspective_kellyanne(self, signal_lower):
        """Kellyanne's perspective: Compute harmonic profile of the signal. """
        harmonics = self._resonance_equation(signal_lower)
        return {"agent": "Kellyanne" , "harmonics": harmonics}

    def process(self, input_signal):
        """
        Process an input signal, analyze it, and return a structured verdict.

        Args:
            input_signal (str): The input text to analyze.

        Returns:
            dict: Analysis results including hash, intent, perspectives, and verdict.
        """
        # Instrumentation wrapper (2026-08-10). The analysis itself is unchanged
        # and lives in _process_impl; this only records timing and errors.
        # Deliberately re-raises: counting a failure must not swallow it.
        start = time.perf_counter()
        try:
            return self._process_impl(input_signal)
        except Exception:
            self.metrics.record_error()
            raise
        finally:
            self.metrics.record_process_time(time.perf_counter() - start)

    def get_metrics(self):
        """Return process-time and error statistics.

        Returns:
            dict: {"avg_process_time": float, "error_count": int}
        """
        return self.metrics.get_stats()

    def _process_impl(self, input_signal):
        """Core analysis logic; process() wraps this to record Metrics and errors."""
        start_time = time.perf_counter()
        signal_lower = input_signal.lower()
        tokens = self._tokenize_and_lemmatize(signal_lower)
        key = self._hash(input_signal)
        intent_vector = self._predict_intent_vector(signal_lower, tokens)

        if intent_vector["pre_corruption_risk"] == "high":
            final_record = {
                "hash": key,
                "timestamp": datetime.utcnow().isoformat(),
                "input": input_signal,
                "intent_warning": intent_vector,
                "verdict": "adaptive intervention" ,
                "message": "Signal flagged for pre-corruption adaptation. Reframing required. "
            }
            self.cache[key].append(final_record)
            self.memory[key] = final_record
            self._save_memory()
            logger.info(f"Processed {input_signal} (high risk) in {time.perf_counter() -
start_time}s")
            return final_record

        perspectives_output = {
            "Colleen": self._perspective_colleen(input_signal),
            "Luke": self._perspective_luke(signal_lower, tokens),
            "Kellyanne": self._perspective_kellyanne(signal_lower)
        }

        spider_signal = "::" .join([str(perspectives_output[p]) for p in self.perspectives])
        vec, _ = self._rotate_vector(spider_signal)
        entangled = self._entanglement_tensor(vec)
        entangled_serialized = [{"real": v.real, "imag": v.imag} for v in entangled]
        reasoning, verdict = self._universal_reasoning(spider_signal, tokens)

        final_record = {
            "hash": key,
            "timestamp": datetime.utcnow().isoformat(),
            "input": input_signal,
            "intent_signature": intent_vector,
            "perspectives": perspectives_output,
            "entangled": entangled_serialized,
            "reasoning": reasoning,
            "verdict": verdict
        }

        self.cache[key].append(final_record)
        self.memory[key] = final_record
        self._save_memory()
        logger.info(f"Processed {input_signal} in {time.perf_counter() - start_time}s")
        return final_record

    def process_batch(self, signals):
        """
        Process multiple signals concurrently and return a list of results.

        Args:
            signals (list): List of input signals to process.

        Returns:
            list: List of analysis results.
        """
        with ThreadPoolExecutor(max_workers=4) as executor:
            return list(executor.map(self.process, signals))

    def query_memory(self, query_string):
        """
        Query memory using FTS with a given query string.

        Args:
            query_string (str): FTS query (e.g., "verdict:adaptive intervention").

        Returns:
            list: List of matching records as dictionaries.
        """
        with sqlite3.connect(self.memory_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT rowid, * FROM memory_fts WHERE memory_fts MATCH ?" ,
(query_string,))
            return [dict(zip([d[0] for d in cursor.description], row)) for row in cursor.fetchall()]

    def update_config(self, new_config):
        """
        Update configuration parameters at runtime.

        Args:
            new_config (dict): Dictionary of configuration updates (e.g., {"entropy_threshold":
0.1}).
        """
        for key, value in new_config.items():
            if key in {"entropy_threshold" , "fuzzy_threshold"} and isinstance(value, (int, float)):
                setattr(self, key, value)
            elif key in self.config and isinstance(value, list):
                self.config[key] = value
        logger.info(f"Updated config with {new_config}")

    def _prune_and_rotate_memory(self):
        """Prune expired entries and rotate memory database if needed. """
        now = datetime.utcnow()
        with LockManager(f"{self.memory_path}.lock"):
            with sqlite3.connect(self.memory_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM memory
                    WHERE timestamp < ?
                """ , ((now - self.memory_ttl).isoformat(),))
                cursor.execute("DELETE FROM memory_fts WHERE rowid NOT IN (SELECT fts_rowid FROM memory)")
                conn.commit()
                cursor.execute("SELECT COUNT(*) FROM memory")
                count = cursor.fetchone()[0]
                db_size_mb = os.path.getsize(self.memory_path) / (1024 * 1024)
                if count >= self.max_memory_entries or db_size_mb >= self.max_db_size_mb:
                    self._rotate_memory_file()
                    cursor.execute("DELETE FROM memory")
                    cursor.execute("DELETE FROM memory_fts")
                    conn.commit()
                    self.memory = {}


class TestNexisSignalEngine(unittest.TestCase):
    def setUp(self):
        self.engine = NexisSignalEngine(
            memory_path="test_memory.db" ,
            entropy_threshold=0.08,
            max_memory_entries=100,
            memory_ttl_days=1,
            fuzzy_threshold=80,
            max_db_size_mb=1
        )
        self.test_signal = "hope truth repair"
        self.adversarial_signal = "cha0s expl0it tru/th hopee"
        self._clear_sqlite()

    def _clear_sqlite(self):
        """Clear SQLite database and lock files. """
        if os.path.exists(self.engine.memory_path):
            os.remove(self.engine.memory_path)
        lock_file = f"{self.engine.memory_path}.lock"
        if os.path.exists(lock_file):
            os.remove(lock_file)
        self.engine._init_sqlite()

    def tearDown(self):
        """Clean up database and lock files after each test. """
        self._clear_sqlite()

    def test_hash(self):
        hash1 = self.engine._hash(self.test_signal)
        hash2 = self.engine._hash(self.test_signal)
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)

    def test_rotate_vector(self):
        vec1, serial1 = self.engine._rotate_vector(self.test_signal)
        vec2, serial2 = self.engine._rotate_vector(self.test_signal)
        np.testing.assert_array_equal(vec1, vec2)
        self.assertEqual(serial1, serial2)
        self.assertEqual(len(serial1), 2)

    def test_entanglement_tensor(self):
        vec, _ = self.engine._rotate_vector(self.test_signal)
        entangled = self.engine._entanglement_tensor(vec)
        self.assertEqual(len(entangled), 2)
        self.assertIsInstance(entangled[0], complex)

    def test_resonance_equation(self):
        harmonics = self.engine._resonance_equation(self.test_signal)
        self.assertEqual(len(harmonics), 3)
        self.assertTrue(all(isinstance(h, float) for h in harmonics))
        self.assertEqual(self.engine._resonance_equation("123!@#"), [0.0, 0.0, 0.0])

    def test_tokenize_and_lemmatize(self):
        tokens = self.engine._tokenize_and_lemmatize("tru/th hopee")
        self.assertIn("truth" , tokens)
        self.assertIn("hope" , tokens)
        self.assertTrue(any(len(t) <= 3 for t in tokens))

    def test_entropy(self):
        tokens = self.engine._tokenize_and_lemmatize("corruption chaos")
        entropy = self.engine._entropy("corruption chaos" , tokens)
        self.assertGreater(entropy, 0)
        tokens = self.engine._tokenize_and_lemmatize("cha0s cha0tic")
        entropy = self.engine._entropy("cha0s cha0tic" , tokens)
        self.assertGreater(entropy, 0)

    def test_tag_ethics(self):
        tokens = self.engine._tokenize_and_lemmatize("hope truth")
        self.assertEqual(self.engine._tag_ethics("hope truth" , tokens), "aligned")
        tokens = self.engine._tokenize_and_lemmatize("chaos malice")
        self.assertEqual(self.engine._tag_ethics("chaos malice" , tokens), "unaligned")
        tokens = self.engine._tokenize_and_lemmatize("h0pe trth")
        self.assertEqual(self.engine._tag_ethics("h0pe trth" , tokens), "aligned")

    def test_predict_intent_vector(self):
        tokens = self.engine._tokenize_and_lemmatize("exploit chaos")
        intent = self.engine._predict_intent_vector("exploit chaos" , tokens)
        self.assertIn("suspicion_score" , intent)
        self.assertGreaterEqual(intent["suspicion_score"], 1)
        tokens = self.engine._tokenize_and_lemmatize(self.adversarial_signal)
        intent = self.engine._predict_intent_vector(self.adversarial_signal, tokens)
        self.assertEqual(intent["pre_corruption_risk"], "high")

    def test_universal_reasoning(self):
        tokens = self.engine._tokenize_and_lemmatize("hope::truth")
        reasoning, verdict = self.engine._universal_reasoning("hope::truth" , tokens)
        self.assertEqual(len(reasoning), 4)
        self.assertIn(verdict, ["approved" , "blocked"])
        tokens = self.engine._tokenize_and_lemmatize("cha0s expl0it")
        reasoning, verdict = self.engine._universal_reasoning("cha0s expl0it" , tokens)
        self.assertEqual(verdict, "blocked")

    def test_perspective_colleen(self):
        result = self.engine._perspective_colleen(self.test_signal)
        self.assertEqual(result["agent"], "Colleen")
        self.assertEqual(len(result["vector"]), 2)

    def test_perspective_luke(self):
        tokens = self.engine._tokenize_and_lemmatize("hope truth")
        result = self.engine._perspective_luke("hope truth" , tokens)
        self.assertEqual(result["agent"], "Luke")
        self.assertEqual(result["ethics"], "aligned")

    def test_perspective_kellyanne(self):
        result = self.engine._perspective_kellyanne("hope truth")
        self.assertEqual(result["agent"], "Kellyanne")
        self.assertEqual(len(result["harmonics"]), 3)

    def test_process_and_memory(self):
        result = self.engine.process(self.test_signal)
        self.assertIn("hash" , result)
        self.assertEqual(result["hash"], self.engine._hash(self.test_signal))
        self.assertEqual(self.engine.memory[result["hash"]], result)
        with sqlite3.connect(self.engine.memory_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT integrity_hash FROM memory WHERE hash = ?" ,
(result["hash"],))
            integrity_hash = cursor.fetchone()[0]
            computed_hash = hashlib.sha256(json.dumps(result,
sort_keys=True).encode()).hexdigest()
            self.assertEqual(integrity_hash, computed_hash)

    def test_adversarial_input(self):
        result = self.engine.process(self.adversarial_signal)
        self.assertEqual(result["verdict"], "adaptive intervention")
        self.assertEqual(result["intent_warning"]["pre_corruption_risk"], "high")

    def test_process_batch(self):
        signals = [self.test_signal, self.adversarial_signal]
        results = self.engine.process_batch(signals)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[1]["verdict"], "adaptive intervention")

    def test_query_memory(self):
        result = self.engine.process(self.adversarial_signal)
        matches = self.engine.query_memory("verdict:adaptive intervention")
        self.assertGreater(len(matches), 0)
        self.assertEqual(matches[0]["verdict"], "adaptive intervention")

    def test_update_config(self):
        original_threshold = self.engine.entropy_threshold
        self.engine.update_config({"entropy_threshold": 0.1})
        self.assertEqual(self.engine.entropy_threshold, 0.1)
        self.engine.update_config({"entropy_threshold": original_threshold})


if __name__ == "__main__":
    unittest.main()