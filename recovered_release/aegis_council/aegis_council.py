import json
import hashlib
import threading
import logging
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any, Dict, Optional, List, Tuple
import concurrent.futures
import networkx as nx
import plotly.graph_objects as go
import pandas as pd
from textblob import TextBlob
import numpy as np

# Setup logging with detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s',
    handlers=[logging.FileHandler('aegis_council.log'), logging.StreamHandler()]
)

# === MEMORY AND SIGNAL LAYERS ===
class NexusMemory:
    def __init__(self, max_entries: int = 10000, decay_days: int = 30):
        self.store = defaultdict(dict)
        self.max_entries = max_entries
        self.decay_days = decay_days
        self.lock = threading.Lock()
        self.logger = logging.getLogger('NexusMemory')

    def write(self, key: str, value: Any, emotion_weight: float = 0.5) -> Optional[str]:
        """Write a key-value pair to memory with emotion weight."""
        try:
            if not isinstance(key, str) or not (0 <= emotion_weight <= 1):
                self.logger.error(f"Invalid key type {type(key)} or emotion_weight {emotion_weight}")
                return None
            hashed = hashlib.md5(key.encode()).hexdigest()  # Use MD5 for faster hashing
            with self.lock:
                if len(self.store) >= self.max_entries:
                    oldest = min(self.store.items(), key=lambda x: x[1].get('timestamp', datetime.now()))[0]
                    self.logger.info(f"Removing oldest entry: {oldest}")
                    del self.store[oldest]
                self.store[hashed] = {
                    "value": value,
                    "timestamp": datetime.now(),
                    "emotion_weight": emotion_weight
                }
                self.logger.debug(f"Wrote key: {hashed}, value: {value}")
                return hashed
        except Exception as e:
            self.logger.error(f"Error writing to memory: {e}")
            return None

    def read(self, key: str) -> Optional[Any]:
        """Read a value from memory by key, checking for decay."""
        try:
            hashed = hashlib.md5(key.encode()).hexdigest()
            with self.lock:
                entry = self.store.get(hashed)
                if not entry:
                    self.logger.debug(f"Key not found: {hashed}")
                    return None
                if self._is_decayed(entry["timestamp"], entry.get("emotion_weight", 0.5)):
                    self.logger.info(f"Removing decayed entry: {hashed}")
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
            age = (datetime.now() - timestamp).total_seconds() / (24 * 3600)  # Convert to days
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

# === AGENT COUNCIL CORE ===
class AegisCouncil:
    def __init__(self):
        self.memory = NexusMemory()
        self.agents: List[AegisAgent] = []
        self.reports: Dict[str, Dict[str, Any]] = {}
        self.graph = nx.DiGraph()
        self.logger = logging.getLogger('AegisCouncil')

    def register_agent(self, agent: AegisAgent) -> None:
        """Register an agent to the council."""
        try:
            self.agents.append(agent)
            self.logger.info(f"Registered agent: {agent.name}")
        except Exception as e:
            self.logger.error(f"Error registering agent: {e}")

    def dispatch(self, input_data: Dict[str, Any]) -> bool:
        """Dispatch input data to all agents and collect reports."""
        try:
            # Validate input
            if not isinstance(input_data, dict):
                self.logger.error("Input data must be a dictionary")
                return False
            if "text" not in input_data or "overrides" not in input_data:
                self.logger.warning("Input data missing 'text' or 'overrides' keys")

            self.reports.clear()
            self.graph.clear()

            # Use ThreadPoolExecutor for efficient parallel execution
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.agents)) as executor:
                future_to_agent = {executor.submit(agent.analyze, input_data): agent for agent in self.agents}
                for future in concurrent.futures.as_completed(future_to_agent):
                    agent = future_to_agent[future]
                    try:
                        future.result()  # Wait for completion
                        self.reports[agent.name] = agent.report()
                        self.graph.add_node(agent.name, explanation=agent.explanation)
                        for target, weight in agent.influence.items():
                            self.graph.add_edge(agent.name, target, weight=round(weight, 2))
                    except Exception as e:
                        self.logger.error(f"Error in agent {agent.name}: {e}")
                        self.reports[agent.name] = {"error": str(e), "explanation": "Agent failed to process"}
            return True
        except Exception as e:
            self.logger.error(f"Error in dispatch: {e}")
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
        self.weights = weights or {"influence": 0.4, "reliability": 0.3, "severity": 0.3}

    def analyze(self, input_data: Dict[str, Any]) -> None:
        """Analyze overrides and select the best agent based on weighted scoring."""
        try:
            overrides = input_data.get("overrides", {})
            if not overrides:
                self.result = {"error": "No overrides provided"}
                self.explanation = "MetaJudgeAgent failed: No overrides provided."
                self.logger.warning(self.explanation)
                return

            # Check memory for prior agent scores
            scores = []
            for agent, data in overrides.items():
                try:
                    influence = float(data.get("influence", 0.5))
                    reliability = float(data.get("reliability", 0.5))
                    severity = float(data.get("severity", 0.5))
                    if not all(0 <= x <= 1 for x in [influence, reliability, severity]):
                        self.logger.warning(f"Invalid metrics for {agent}: {data}")
                        continue

                    # Check memory for historical context
                    mem_key = f"meta_judge_{agent}_score"
                    prev_score = self.memory.read(mem_key)
                    context_factor = 1.0 if prev_score is None else 0.9  # Reduce weight if historical data exists
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
    def analyze(self, input_data: Dict[str, Any]) -> None:
        """Analyze text for virtues using sentiment analysis."""
        try:
            text = input_data.get("text", "")
            if not text or not isinstance(text, str):
                self.result = {"error": "Invalid or empty text"}
                self.explanation = "VirtueAgent failed: Invalid or empty text."
                self.logger.warning(self.explanation)
                return

            # Use TextBlob for sentiment and subjectivity
            blob = TextBlob(text)
            sentiment = blob.sentiment.polarity  # -1 (negative) to 1 (positive)
            subjectivity = blob.sentiment.subjectivity  # 0 (objective) to 1 (subjective)

            # Map sentiment and subjectivity to virtues
            virtues = {
                "compassion": max(0, sentiment) * 0.7 + subjectivity * 0.3,
                "integrity": (1 - subjectivity) * 0.6 + max(0, sentiment) * 0.4,
                "courage": subjectivity * 0.5 + (1 - abs(sentiment)) * 0.5,
                "wisdom": (1 - subjectivity) * 0.7 + max(0, sentiment) * 0.3
            }
            virtues = {k: round(min(v, 1.0), 2) for k, v in virtues.items()}
            self.result = {"virtue_profile": virtues}
            self.explanation = f"VirtueAgent generated profile: {virtues} based on sentiment (polarity={sentiment:.2f}, subjectivity={subjectivity:.2f})."
            for virtue, score in virtues.items():
                self.influence[virtue] = score
                self.memory.write(f"virtue_{virtue}_{datetime.now().isoformat()}", score, emotion_weight=score)
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

        # Dispatch and process
        success = council.dispatch(sample_input)
        if not success:
            print("Dispatch failed. Check logs for details.")
            return

        # Display reports
        reports = council.get_reports()
        df = pd.DataFrame.from_dict(reports, orient='index')
        print("\nAgent Reports:")
        print(df.to_string())

        # Draw interactive graph
        council.draw_explainability_graph()

    except Exception as e:
        logging.error(f"Main execution failed: {e}")

if __name__ == "__main__":
    main()