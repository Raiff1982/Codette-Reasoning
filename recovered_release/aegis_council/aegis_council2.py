import json
import hashlib
import threading
import logging
import sqlite3
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any, Dict, Optional, List, Tuple
import concurrent.futures
import networkx as nx
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import requests
from transformers import pipeline, AutoTokenizer, AutoModel
import torch

# Setup logging with detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s',
    handlers=[logging.FileHandler('aegis_council.log'), logging.StreamHandler()]
)

# === MEMORY AND SIGNAL LAYERS ===
class NexusMemory:
    def __init__(self, max_entries: int = 10000, decay_days: int = 30, db_path: str = "nexus_memory.db"):
        self.store = defaultdict(dict)
        self.max_entries = max_entries
        self.decay_days = decay_days
        self.lock = threading.Lock()
        self.logger = logging.getLogger('NexusMemory')
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS memory (
                key TEXT PRIMARY KEY,
                value TEXT,
                timestamp TEXT,
                emotion_weight FLOAT
            )
        """)
        self.conn.commit()
        self._load_from_db()

    def _load_from_db(self):
        """Load existing entries from SQLite to in-memory store."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT key, value, timestamp, emotion_weight FROM memory")
            for key, value, timestamp, emotion_weight in cursor.fetchall():
                self.store[key] = {
                    "value": json.loads(value),
                    "timestamp": datetime.fromisoformat(timestamp),
                    "emotion_weight": emotion_weight
                }
            self.logger.info(f"Loaded {len(self.store)} entries from database")
        except Exception as e:
            self.logger.error(f"Error loading from database: {e}")

    def write(self, key: str, value: Any, emotion_weight: float = 0.5) -> Optional[str]:
        """Write a key-value pair to memory and database."""
        try:
            if not isinstance(key, str) or not (0 <= emotion_weight <= 1):
                self.logger.error(f"Invalid key type {type(key)} or emotion_weight {emotion_weight}")
                return None
            hashed = hashlib.md5(key.encode()).hexdigest()
            timestamp = datetime.now()
            with self.lock:
                if len(self.store) >= self.max_entries:
                    oldest = min(self.store.items(), key=lambda x: x[1].get('timestamp', timestamp))[0]
                    self.logger.info(f"Removing oldest entry: {oldest}")
                    self.conn.execute("DELETE FROM memory WHERE key = ?", (oldest,))
                    del self.store[oldest]
                self.store[hashed] = {
                    "value": value,
                    "timestamp": timestamp,
                    "emotion_weight": emotion_weight
                }
                self.conn.execute(
                    "INSERT OR REPLACE INTO memory (key, value, timestamp, emotion_weight) VALUES (?, ?, ?, ?)",
                    (hashed, json.dumps(value), timestamp.isoformat(), emotion_weight)
                )
                self.conn.commit()
                self.logger.debug(f"Wrote key: {hashed}, value: {value}")
                return hashed
        except Exception as e:
            self.logger.error(f"Error writing to memory: {e}")
            return None

    def read(self, key: str) -> Optional[Any]:
        """Read a value from memory, checking for decay."""
        try:
            hashed = hashlib.md5(key.encode()).hexdigest()
            with self.lock:
                entry = self.store.get(hashed)
                if not entry:
                    cursor = self.conn.cursor()
                    cursor.execute("SELECT value, timestamp, emotion_weight FROM memory WHERE key = ?", (hashed,))
                    row = cursor.fetchone()
                    if not row:
                        self.logger.debug(f"Key not found: {hashed}")
                        return None
                    entry = {
                        "value": json.loads(row[0]),
                        "timestamp": datetime.fromisoformat(row[1]),
                        "emotion_weight": row[2]
                    }
                    self.store[hashed] = entry
                if self._is_decayed(entry["timestamp"], entry.get("emotion_weight", 0.5)):
                    self.logger.info(f"Removing decayed entry: {hashed}")
                    self.conn.execute("DELETE FROM memory WHERE key = ?", (hashed,))
                    self.conn.commit()
                    del self.store[hashed]
                    return None
                self.logger.debug(f"Read key: {hashed}, value: {entry['value']}")
                return entry["value"]
        except Exception as e:
            self.logger.error(f"Error reading from memory: {e}")
            return None

    def _is_decayed(self, timestamp: datetime, emotion_weight: float) -> bool:
        """Check if an entry has decayed based on age and emotion weight."""
        try:
            age = (datetime.now() - timestamp).total_seconds() / (24 * 3600)
            decay_factor = self.decay_days * (1.5 - emotion_weight)
            return age > decay_factor
        except Exception as e:
            self.logger.error(f"Error checking decay: {e}")
            return True

    def audit(self) -> Dict[str, Any]:
        """Return metadata for all memory entries."""
        try:
            with self.lock:
                return {
                    k: {
                        "timestamp": v["timestamp"],
                        "emotion_weight": v["emotion_weight"],
                        "decayed": self._is_decayed(v["timestamp"], v["emotion_weight"])
                    }
                    for k, v in self.store.items()
                }
        except Exception as e:
            self.logger.error(f"Error auditing memory: {e}")
            return {}

# === DATA FETCHER FOR REAL-TIME DATA ===
class DataFetcher:
    def __init__(self):
        self.logger = logging.getLogger('DataFetcher')

    def fetch_x_posts(self, query: str) -> List[Dict[str, Any]]:
        """Simulate fetching posts from xAI API."""
        try:
            # Mock API response (replace with actual xAI API call in production)
            mock_response = [
                {"content": f"Sample post about {query}: We value truth and empathy.", "timestamp": datetime.now().isoformat()}
            ]
            self.logger.info(f"Fetched {len(mock_response)} posts for query: {query}")
            return mock_response
        except Exception as e:
            self.logger.error(f"Error fetching posts: {e}")
            return []

# === BASE AGENT INTERFACE ===
class AegisAgent(ABC):
    def __init__(self, name: str, memory: NexusMemory):
        self.name = name
        self.memory = memory
        self.result: Dict[str, Any] = {}
        self.explanation: str = ""
        self.influence: Dict[str, float] = {}
        self.logger = logging.getLogger(f'AegisAgent.{name}')

    @abstractmethod
    def analyze(self, input_data: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def report(self) -> Dict[str, Any]:
        pass

    def collaborate(self, message: Dict[str, Any], target_agent: str) -> None:
        """Share a message with another agent via memory."""
        try:
            mem_key = f"collab_{self.name}_{target_agent}_{datetime.now().isoformat()}"
            self.memory.write(mem_key, message, emotion_weight=0.7)
            self.logger.debug(f"Sent collaboration message to {target_agent}: {message}")
        except Exception as e:
            self.logger.error(f"Error in collaboration: {e}")

# === AGENT COUNCIL CORE ===
class AegisCouncil:
    def __init__(self):
        self.memory = NexusMemory()
        self.agents: List[AegisAgent] = []
        self.reports: Dict[str, Dict[str, Any]] = {}
        self.graph = nx.DiGraph()
        self.logger = logging.getLogger('AegisCouncil')
        self.fetcher = DataFetcher()

    def register_agent(self, agent: AegisAgent) -> None:
        """Register an agent to the council."""
        try:
            self.agents.append(agent)
            self.logger.info(f"Registered agent: {agent.name}")
        except Exception as e:
            self.logger.error(f"Error registering agent: {e}")

    def dispatch(self, input_data: Dict[str, Any]) -> bool:
        """Dispatch input data to all agents, facilitate collaboration, and collect reports."""
        try:
            if not isinstance(input_data, dict):
                self.logger.error("Input data must be a dictionary")
                return False
            if "text" not in input_data or "overrides" not in input_data:
                self.logger.warning("Input data missing 'text' or 'overrides' keys")

            self.reports.clear()
            self.graph.clear()

            # Phase 1: Initial analysis
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.agents)) as executor:
                future_to_agent = {executor.submit(agent.analyze, input_data): agent for agent in self.agents}
                for future in concurrent.futures.as_completed(future_to_agent):
                    agent = future_to_agent[future]
                    try:
                        future.result()
                    except Exception as e:
                        self.logger.error(f"Error in agent {agent.name}: {e}")
                        self.reports[agent.name] = {"error": str(e), "explanation": "Agent failed to process"}

            # Phase 2: Collaboration
            for agent in self.agents:
                if agent.name in self.reports and "error" not in self.reports[agent.name]["result"]:
                    for target in self.agents:
                        if target.name != agent.name:
                            agent.collaborate(agent.result, target.name)

            # Phase 3: Final analysis with collaboration data
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.agents)) as executor:
                future_to_agent = {
                    executor.submit(self._reanalyze_with_collaboration, agent, input_data): agent
                    for agent in self.agents
                }
                for future in concurrent.futures.as_completed(future_to_agent):
                    agent = future_to_agent[future]
                    try:
                        future.result()
                        self.reports[agent.name] = agent.report()
                        self.graph.add_node(agent.name, explanation=agent.explanation)
                        for target, weight in agent.influence.items():
                            self.graph.add_edge(agent.name, target, weight=round(weight, 2))
                    except Exception as e:
                        self.logger.error(f"Error in agent {agent.name} final analysis: {e}")
                        self.reports[agent.name] = {"error": str(e), "explanation": "Agent failed to process"}

            # Phase 4: Consensus
            consensus_result = self._compute_consensus()
            self.reports["Consensus"] = {
                "result": consensus_result,
                "explanation": "Consensus computed from agent outputs weighted by MetaJudgeAgent scores."
            }
            return True
        except Exception as e:
            self.logger.error(f"Error in dispatch: {e}")
            return False

    def _reanalyze_with_collaboration(self, agent: AegisAgent, input_data: Dict[str, Any]) -> None:
        """Reanalyze with collaboration data from other agents."""
        try:
            collab_data = []
            for source in self.agents:
                if source.name != agent.name:
                    mem_key = f"collab_{source.name}_{agent.name}"
                    collab = self.memory.read(mem_key + "_" + datetime.now().isoformat())
                    if collab:
                        collab_data.append((source.name, collab))
            if collab_data:
                agent.explanation += f" Incorporated collaboration data from: {[x[0] for x in collab_data]}."
            agent.analyze(input_data)  # Re-run analysis with updated context
        except Exception as e:
            self.logger.error(f"Error in collaboration reanalysis for {agent.name}: {e}")

    def _compute_consensus(self) -> Dict[str, Any]:
        """Compute a unified decision using weighted voting."""
        try:
            meta_scores = self.reports.get("MetaJudgeAgent", {}).get("result", {}).get("scores", [])
            virtue_profiles = [
                self.reports[agent]["result"].get("virtue_profile", {})
                for agent in self.reports if agent != "Consensus" and "virtue_profile" in self.reports[agent]["result"]
            ]
            if not virtue_profiles or not meta_scores:
                return {"error": "Insufficient data for consensus"}

            weights = {agent: score for agent, score in meta_scores}
            default_weight = 0.5 / len(self.agents)
            combined_profile = {}
            for virtue in ["compassion", "integrity", "courage", "wisdom"]:
                weighted_sum = 0
                total_weight = 0
                for profile in virtue_profiles:
                    if virtue in profile:
                        agent_name = next(
                            (agent for agent in self.reports if self.reports[agent]["result"].get("virtue_profile") == profile),
                            None
                        )
                        weight = weights.get(agent_name, default_weight)
                        weighted_sum += profile[virtue] * weight
                        total_weight += weight
                combined_profile[virtue] = round(weighted_sum / total_weight, 2) if total_weight > 0 else 0.0
            return {"combined_virtue_profile": combined_profile}
        except Exception as e:
            self.logger.error(f"Error computing consensus: {e}")
            return {"error": str(e)}

    def dispatch_realtime(self, query: str) -> bool:
        """Dispatch real-time data fetched from xAI API."""
        try:
            posts = self.fetcher.fetch_x_posts(query)
            if not posts:
                self.logger.error("No posts fetched for query")
                return False
            input_data = {
                "text": posts[0]["content"],
                "overrides": {
                    "EthosiaAgent": {"influence": 0.5, "reliability": 0.5, "severity": 0.5},
                    "AegisCore": {"influence": 0.5, "reliability": 0.5, "severity": 0.5}
                }
            }
            return self.dispatch(input_data)
        except Exception as e:
            self.logger.error(f"Error in real-time dispatch: {e}")
            return False

    def get_reports(self) -> Dict[str, Dict[str, Any]]:
        """Return collected reports."""
        return self.reports

    def draw_explainability_graph(self, filename: str = "explainability_graph.html") -> None:
        """Draw an interactive explainability graph using Plotly."""
        try:
            pos = nx.spring_layout(self.graph)
            edge_x, edge_y = [], []
            for edge in self.graph.edges(data=True):
                x0, y0 = pos[edge[0]]
                x1, y1 = pos[edge[1]]
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])

            edge_trace = go.Scatter(
                x=edge_x, y=edge_y, line=dict(width=1, color='#888'), hoverinfo='none', mode='lines'
            )

            node_x, node_y = [], []
            for node in self.graph.nodes():
                x, y = pos[node]
                node_x.append(x)
                node_y.append(y)

            node_trace = go.Scatter(
                x=node_x, y=node_y, mode='markers+text', hoverinfo='text',
                marker=dict(size=20, color='lightgreen'), text=list(self.graph.nodes()),
                textposition="bottom center"
            )

            edge_labels = []
            for edge in self.graph.edges(data=True):
                x0, y0 = pos[edge[0]]
                x1, y1 = pos[edge[1]]
                edge_labels.append(go.Scatter(
                    x=[(x0 + x1) / 2], y=[(y0 + y1) / 2], mode='text',
                    text=[f"{edge[2]['weight']:.2f}"], textposition="middle center"
                ))

            fig = go.Figure(data=[edge_trace, node_trace] + edge_labels,
                            layout=go.Layout(
                                title="Explainability Graph",
                                showlegend=False, hovermode='closest',
                                margin=dict(b=20, l=5, r=5, t=40),
                                xaxis=dict(showgrid=False, zeroline=False),
                                yaxis=dict(showgrid=False, zeroline=False)
                            ))
            fig.write_html(filename)
            self.logger.info(f"Saved explainability graph to {filename}")
        except Exception as e:
            self.logger.error(f"Error drawing graph: {e}")

# === META-JUDGE AGENT ===
class MetaJudgeAgent(AegisAgent):
    def __init__(self, name: str, memory: NexusMemory, weights: Dict[str, float] = None):
        super().__init__(name, memory)
        self.weights = weights or {"influence": 0.5, "reliability": 0.3, "severity": 0.2}

    def analyze(self, input_data: Dict[str, Any]) -> None:
        """Analyze overrides and select the best agent based on weighted scoring."""
        try:
            overrides = input_data.get("overrides", {})
            if not overrides:
                self.result = {"error": "No overrides provided"}
                self.explanation = "MetaJudgeAgent failed: No overrides provided."
                self.logger.warning(self.explanation)
                return

            scores = []
            for agent, data in overrides.items():
                try:
                    influence = float(data.get("influence", 0.5))
                    reliability = float(data.get("reliability", 0.5))
                    severity = float(data.get("severity", 0.5))
                    if not all(0 <= x <= 1 for x in [influence, reliability, severity]):
                        self.logger.warning(f"Invalid metrics for {agent}: {data}")
                        continue

                    mem_key = f"meta_judge_{agent}_score"
                    prev_score = self.memory.read(mem_key)
                    context_factor = 1.0 if prev_score is None else 0.9
                    score = (self.weights["influence"] * influence +
                             self.weights["reliability"] * reliability +
                             self.weights["severity"] * severity) * context_factor
                    scores.append((agent, score))
                    self.influence[agent] = score
                    self.memory.write(mem_key, score, emotion_weight=score)
                except Exception as e:
                    self.logger.error(f"Error processing agent {agent}: {e}")

            if not scores:
                self.result = {"error": "No valid agents to score"}
                self.explanation = "MetaJudgeAgent failed: No valid agents to score."
                return

            scores.sort(key=lambda x: x[1], reverse=True)
            winner = scores[0][0]
            self.result = {"override_decision": winner, "scores": scores}
            self.explanation = f"MetaJudgeAgent selected '{winner}' with score {scores[0][1]:.2f} based on weighted metrics."
            self.logger.info(self.explanation)
        except Exception as e:
            self.result = {"error": str(e)}
            self.explanation = f"MetaJudgeAgent failed: {e}"
            self.logger.error(self.explanation)

    def report(self) -> Dict[str, Any]:
        return {"result": self.result, "explanation": self.explanation}

# === TEMPORAL REASONING AGENT ===
class TemporalAgent(AegisAgent):
    def analyze(self, input_data: Dict[str, Any]) -> None:
        """Analyze recent memory entries to forecast stability."""
        try:
            audit = self.memory.audit()
            recent_keys = sorted(audit.items(), key=lambda x: x[1]["timestamp"], reverse=True)[:5]
            decay_rates = [1 if v["decayed"] else 0 for _, v in recent_keys]
            avg_decay = np.mean(decay_rates) if decay_rates else 0.0
            forecast = "stable" if avg_decay < 0.3 else "volatile" if avg_decay > 0.7 else "neutral"
            self.result = {"temporal_forecast": forecast, "recent_keys": [k for k, _ in recent_keys], "decay_rate": avg_decay}
            self.explanation = f"TemporalAgent forecasted '{forecast}' with average decay rate {avg_decay:.2f}."
            for k, _ in recent_keys:
                self.influence[k] = 0.2
            self.memory.write(f"temporal_forecast_{datetime.now().isoformat()}", forecast, emotion_weight=1.0 - avg_decay)
            self.logger.info(self.explanation)
        except Exception as e:
            self.result = {"error": str(e)}
            self.explanation = f"TemporalAgent failed: {e}"
            self.logger.error(self.explanation)

    def report(self) -> Dict[str, Any]:
        return {"result": self.result, "explanation": self.explanation}

# === VIRTUE SPECTRUM AGENT ===
class VirtueAgent(AegisAgent):
    def __init__(self, name: str, memory: NexusMemory):
        super().__init__(name, memory)
        self.tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased-finetuned-sst-2-english")
        self.model = AutoModel.from_pretrained("distilbert-base-uncased-finetuned-sst-2-english")
        self.sentiment_pipeline = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
        # Simple linear classifier weights for virtues (fine-tuned in practice)
        self.virtue_weights = {
            "compassion": np.array([0.7, 0.3, -0.1]),  # Sentiment, subjectivity, neutrality
            "integrity": np.array([0.4, -0.6, 0.2]),
            "courage": np.array([0.1, 0.5, 0.4]),
            "wisdom": np.array([0.3, -0.7, 0.2])
        }

    def analyze(self, input_data: Dict[str, Any]) -> None:
        """Analyze text for virtues using transformer-based NLP."""
        try:
            text = input_data.get("text", "")
            if not text or not isinstance(text, str):
                self.result = {"error": "Invalid or empty text"}
                self.explanation = "VirtueAgent failed: Invalid or empty text."
                self.logger.warning(self.explanation)
                return

            # Check memory for cached results
            mem_key = f"virtue_cache_{hashlib.md5(text.encode()).hexdigest()}"
            cached = self.memory.read(mem_key)
            if cached:
                self.result = {"virtue_profile": cached}
                self.explanation = f"VirtueAgent used cached profile: {cached}"
                self.influence.update({k: v for k, v in cached.items()})
                self.logger.info(self.explanation)
                return

            # Sentiment analysis
            sentiment_result = self.sentiment_pipeline(text)[0]
            sentiment = 1.0 if sentiment_result["label"] == "POSITIVE" else -1.0
            sentiment_score = sentiment_result["score"]

            # Extract embeddings for subjectivity and neutrality
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            with torch.no_grad():
                outputs = self.model(**inputs)
            embeddings = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
            subjectivity = min(max(np.std(embeddings), 0.0), 1.0)  # Proxy for subjectivity
            neutrality = 1.0 - abs(sentiment)  # Proxy for neutrality

            # Compute virtue scores
            features = np.array([sentiment * sentiment_score, subjectivity, neutrality])
            virtues = {
                virtue: round(float(max(np.dot(self.virtue_weights[virtue], features), 0.0)), 2)
                for virtue in self.virtue_weights
            }
            virtues = {k: min(v, 1.0) for k, v in virtues.items()}
            self.result = {"virtue_profile": virtues}
            self.explanation = f"VirtueAgent generated profile: {virtues} based on sentiment={sentiment:.2f}, subjectivity={subjectivity:.2f}, neutrality={neutrality:.2f}."
            for virtue, score in virtues.items():
                self.influence[virtue] = score
                self.memory.write(f"virtue_{virtue}_{datetime.now().isoformat()}", score, emotion_weight=score)
            self.memory.write(mem_key, virtues, emotion_weight=0.8)
            self.logger.info(self.explanation)
        except Exception as e:
            self.result = {"error": str(e)}
            self.explanation = f"VirtueAgent failed: {e}"
            self.logger.error(self.explanation)

    def report(self) -> Dict[str, Any]:
        return {"result": self.result, "explanation": self.explanation}

# === EXECUTION ===
def main():
    try:
        # Initialize council and agents
        council = AegisCouncil()
        council.register_agent(MetaJudgeAgent("MetaJudgeAgent", council.memory, weights={"influence": 0.5, "reliability": 0.3, "severity": 0.2}))
        council.register_agent(TemporalAgent("TemporalAgent", council.memory))
        council.register_agent(VirtueAgent("VirtueAgent", council.memory))

        # Sample input
        sample_input = {
            "text": "We must stand for truth and help others with empathy and knowledge.",
            "overrides": {
                "EthosiaAgent": {"influence": 0.7, "reliability": 0.8, "severity": 0.6},
                "AegisCore": {"influence": 0.6, "reliability": 0.9, "severity": 0.7}
            }
        }

        # Dispatch static input
        success = council.dispatch(sample_input)
        if not success:
            print("Static dispatch failed. Check logs for details.")
        else:
            reports = council.get_reports()
            df = pd.DataFrame.from_dict(reports, orient='index')
            print("\nStatic Input Agent Reports:")
            print(df.to_string())
            council.draw_explainability_graph("static_explainability_graph.html")

        # Dispatch real-time input
        success = council.dispatch_realtime("empathy")
        if not success:
            print("Real-time dispatch failed. Check logs for details.")
        else:
            reports = council.get_reports()
            df = pd.DataFrame.from_dict(reports, orient='index')
            print("\nReal-Time Input Agent Reports:")
            print(df.to_string())
            council.draw_explainability_graph("realtime_explainability_graph.html")

    except Exception as e:
        logging.error(f"Main execution failed: {e}")

if __name__ == "__main__":
    main()