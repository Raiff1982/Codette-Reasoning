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
import psutil
import argparse
from flask import Flask, request, render_template, send_file
import os
import importlib.util
import syft as sy
from copy import deepcopy

# Setup logging with configurable level
def setup_logging(log_level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s',
        handlers=[logging.FileHandler('aegis_council.log'), logging.StreamHandler()]
    )

# === CONFIGURATION LOADER ===
def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    default_config = {
        "meta_judge_weights": {"influence": 0.5, "reliability": 0.3, "severity": 0.2},
        "temporal_decay_thresholds": {"stable": 0.3, "volatile": 0.7},
        "virtue_weights": {
            "compassion": [0.7, 0.3, -0.1],
            "integrity": [0.4, -0.6, 0.2],
            "courage": [0.1, 0.5, 0.4],
            "wisdom": [0.3, -0.7, 0.2]
        },
        "memory_decay_days": 30,
        "memory_max_entries": 10000,
        "log_level": "INFO",
        "federated_learning": {"num_clients": 2, "aggregation_rounds": 1}
    }
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            for key in default_config:
                if key not in config:
                    config[key] = default_config[key]
                elif isinstance(default_config[key], dict):
                    config[key].update({k: v for k, v in default_config[key].items() if k not in config[key]})
            return config
        logging.warning(f"Config file {config_path} not found, using defaults")
        return default_config
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        return default_config

# === BLOCKCHAIN FOR AUDITABILITY ===
class Blockchain:
    def __init__(self):
        self.chain = [{"index": 0, "timestamp": datetime.now().isoformat(), "data": "Genesis Block", "prev_hash": "0"}]
        self.logger = logging.getLogger('Blockchain')

    def add_block(self, data: Dict[str, Any]) -> None:
        try:
            prev_block = self.chain[-1]
            block = {
                "index": len(self.chain),
                "timestamp": datetime.now().isoformat(),
                "data": json.dumps(data),
                "prev_hash": self._hash_block(prev_block)
            }
            block["hash"] = self._hash_block(block)
            self.chain.append(block)
            self.logger.info(f"Added block {block['index']} with hash {block['hash']}")
        except Exception as e:
            self.logger.error(f"Error adding block: {e}")

    def _hash_block(self, block: Dict[str, Any]) -> str:
        try:
            block_str = json.dumps(block, sort_keys=True)
            return hashlib.sha256(block_str.encode()).hexdigest()
        except Exception as e:
            self.logger.error(f"Error hashing block: {e}")
            return ""

    def verify(self) -> bool:
        try:
            for i in range(1, len(self.chain)):
                current = self.chain[i]
                prev = self.chain[i-1]
                if current["prev_hash"] != self._hash_block(prev):
                    self.logger.error(f"Blockchain verification failed at block {i}")
                    return False
            self.logger.info("Blockchain verified successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error verifying blockchain: {e}")
            return False

# === MEMORY AND SIGNAL LAYERS ===
class NexusMemory:
    def __init__(self, max_entries: int = 10000, decay_days: int = 30, db_path: str = "nexus_memory.db"):
        self.store = defaultdict(dict)
        self.max_entries = max_entries
        self.decay_days = decay_days
        self.lock = threading.Lock()
        self.logger = logging.getLogger('NexusMemory')
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.blockchain = Blockchain()
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
                self.blockchain.add_block({"key": hashed, "value": value, "timestamp": timestamp.isoformat()})
                self.logger.debug(f"Wrote key: {hashed}, value: {value}")
                return hashed
        except Exception as e:
            self.logger.error(f"Error writing to memory: {e}")
            return None

    def read(self, key: str) -> Optional[Any]:
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
        try:
            age = (datetime.now() - timestamp).total_seconds() / (24 * 3600)
            decay_factor = np.exp(-age / (self.decay_days * (1.5 - emotion_weight)))
            return decay_factor < 0.1
        except Exception as e:
            self.logger.error(f"Error checking decay: {e}")
            return True

    def audit(self) -> Dict[str, Any]:
        try:
            with self.lock:
                audit_data = {
                    k: {
                        "timestamp": v["timestamp"],
                        "emotion_weight": v["emotion_weight"],
                        "decayed": self._is_decayed(v["timestamp"], v["emotion_weight"])
                    }
                    for k, v in self.store.items()
                }
                self.blockchain.add_block({"audit": audit_data})
                return audit_data
        except Exception as e:
            self.logger.error(f"Error auditing memory: {e}")
            return {}

# === DATA FETCHER FOR REAL-TIME DATA ===
class DataFetcher:
    def __init__(self):
        self.logger = logging.getLogger('DataFetcher')

    def fetch_x_posts(self, query: str) -> List[Dict[str, Any]]:
        try:
            mock_response = [
                {"content": f"Sample post about {query}: We value truth and empathy.", "timestamp": datetime.now().isoformat()}
            ]
            self.logger.info(f"Fetched {len(mock_response)} posts for query: {query}")
            return mock_response
        except Exception as e:
            self.logger.error(f"Error fetching posts: {e}")
            return []

# === PERFORMANCE MONITOR ===
def monitor_performance() -> Dict[str, float]:
    try:
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "process_memory_mb": psutil.Process().memory_info().rss / 1024 / 1024
        }
    except Exception as e:
        logging.error(f"Error monitoring performance: {e}")
        return {"cpu_percent": 0.0, "memory_percent": 0.0, "process_memory_mb": 0.0}

# === FEDERATED LEARNING ===
class FederatedTrainer:
    def __init__(self, num_clients: int):
        self.num_clients = num_clients
        self.logger = logging.getLogger('FederatedTrainer')
        self.clients = [sy.VirtualWorker(sy.torch.hook.TorchHook(torch), id=f"client_{i}") for i in range(num_clients)]

    def train(self, weights: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        try:
            client_updates = []
            for client in self.clients:
                client_weights = deepcopy(weights)
                for virtue in client_weights:
                    client_weights[virtue] += np.random.normal(0, 0.01, size=client_weights[virtue].shape)
                client_updates.append(client_weights)
            aggregated = {}
            for virtue in weights:
                aggregated[virtue] = np.mean([update[virtue] for update in client_updates], axis=0)
            self.logger.info("Federated training completed")
            return aggregated
        except Exception as e:
            self.logger.error(f"Error in federated training: {e}")
            return weights

# === QUANTUM-INSPIRED OPTIMIZATION ===
def anneal_layout(graph: nx.DiGraph, iterations: int = 1000, temp: float = 10.0) -> Dict[str, Tuple[float, float]]:
    try:
        nodes = list(graph.nodes())
        pos = {node: (np.random.uniform(-1, 1), np.random.uniform(-1, 1)) for node in nodes}
        temp_min = 0.01
        alpha = 0.99

        def energy(positions):
            e = 0
            for u, v in graph.edges():
                d = np.linalg.norm(np.array(positions[u]) - np.array(positions[v]))
                e += 1 / (d + 1e-6)
            for u in nodes:
                for v in nodes:
                    if u != v:
                        d = np.linalg.norm(np.array(positions[u]) - np.array(positions[v]))
                        e += d
            return e

        best_pos = pos
        best_energy = energy(pos)
        for _ in range(iterations):
            new_pos = deepcopy(pos)
            for node in nodes:
                new_pos[node] = (new_pos[node][0] + np.random.uniform(-0.1, 0.1) * temp,
                                 new_pos[node][1] + np.random.uniform(-0.1, 0.1) * temp)
            new_energy = energy(new_pos)
            if new_energy < best_energy or np.random.random() < np.exp((best_energy - new_energy) / temp):
                pos = new_pos
                best_energy = new_energy
                best_pos = pos
            temp *= alpha
            if temp < temp_min:
                break
        return best_pos
    except Exception as e:
        logging.error(f"Error in anneal_layout: {e}")
        return nx.spring_layout(graph)

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
        try:
            mem_key = f"collab_{self.name}_{target_agent}_{datetime.now().isoformat()}"
            self.memory.write(mem_key, message, emotion_weight=0.7)
            self.logger.debug(f"Sent collaboration message to {target_agent}: {message}")
        except Exception as e:
            self.logger.error(f"Error in collaboration: {e}")

# === AGENT COUNCIL CORE ===
class AegisCouncil:
    def __init__(self, config: Dict[str, Any]):
        self.memory = NexusMemory(max_entries=config["memory_max_entries"], decay_days=config["memory_decay_days"])
        self.agents: List[AegisAgent] = []
        self.reports: Dict[str, Dict[str, Any]] = {}
        self.graph = nx.DiGraph()
        self.logger = logging.getLogger('AegisCouncil')
        self.fetcher = DataFetcher()
        self.config = config
        self.federated_trainer = FederatedTrainer(config["federated_learning"]["num_clients"])

    def register_agent(self, agent: AegisAgent) -> None:
        try:
            self.agents.append(agent)
            self.logger.info(f"Registered agent: {agent.name}")
        except Exception as e:
            self.logger.error(f"Error registering agent: {e}")

    def register_dynamic_agent(self, module_path: str, class_name: str) -> None:
        try:
            spec = importlib.util.spec_from_file_location("custom_agent", module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            agent_class = getattr(module, class_name)
            if not issubclass(agent_class, AegisAgent):
                raise ValueError(f"{class_name} is not a subclass of AegisAgent")
            agent = agent_class(f"Dynamic_{class_name}", self.memory)
            self.register_agent(agent)
            self.logger.info(f"Dynamically registered agent: {agent.name}")
        except Exception as e:
            self.logger.error(f"Error registering dynamic agent {class_name}: {e}")

    def dispatch(self, input_data: Dict[str, Any], max_retries: int = 3) -> bool:
        try:
            if not isinstance(input_data, dict):
                self.logger.error("Input data must be a dictionary")
                return False
            if "text" not in input_data or "overrides" not in input_data:
                self.logger.warning("Input data missing 'text' or 'overrides' keys")

            self.reports.clear()
            self.graph.clear()
            performance = monitor_performance()
            self.logger.info(f"Dispatch started. Performance: {performance}")

            for attempt in range(max_retries):
                try:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.agents)) as executor:
                        future_to_agent = {executor.submit(agent.analyze, input_data): agent for agent in self.agents}
                        for future in concurrent.futures.as_completed(future_to_agent):
                            agent = future_to_agent[future]
                            try:
                                future.result()
                            except Exception as e:
                                self.logger.error(f"Attempt {attempt + 1}: Error in agent {agent.name}: {e}")
                                self.reports[agent.name] = {"error": str(e), "explanation": "Agent failed to process"}

                    for agent in self.agents:
                        if agent.name in self.reports and "error" not in self.reports[agent.name]["result"]:
                            for target in self.agents:
                                if target.name != agent.name:
                                    agent.collaborate(agent.result, target.name)

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
                                self.logger.error(f"Attempt {attempt + 1}: Error in agent {agent.name} final analysis: {e}")
                                self.reports[agent.name] = {"error": str(e), "explanation": "Agent failed to process"}

                    consensus_result = self._compute_consensus()
                    self.reports["Consensus"] = {
                        "result": consensus_result,
                        "explanation": "Consensus computed from agent outputs weighted by MetaJudgeAgent scores."
                    }
                    self.memory.blockchain.add_block(self.reports)
                    performance = monitor_performance()
                    self.logger.info(f"Dispatch completed successfully. Performance: {performance}")
                    return True
                except Exception as e:
                    self.logger.warning(f"Retry {attempt + 1} after error: {e}")
            self.logger.error(f"Dispatch failed after {max_retries} retries")
            return False
        except Exception as e:
            self.logger.error(f"Error in dispatch: {e}")
            return False

    def _reanalyze_with_collaboration(self, agent: AegisAgent, input_data: Dict[str, Any]) -> None:
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
            agent.analyze(input_data)
        except Exception as e:
            self.logger.error(f"Error in collaboration reanalysis for {agent.name}: {e}")

    def _compute_consensus(self) -> Dict[str, Any]:
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
        return self.reports

    def draw_explainability_graph(self, filename: str = "explainability_graph.html") -> None:
        try:
            pos = anneal_layout(self.graph)
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
    def __init__(self, name: str, memory: NexusMemory, weights: Dict[str, float]):
        super().__init__(name, memory)
        self.weights = weights

    def analyze(self, input_data: Dict[str, Any]) -> None:
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
    def __init__(self, name: str, memory: NexusMemory, decay_thresholds: Dict[str, float]):
        super().__init__(name, memory)
        self.decay_thresholds = decay_thresholds

    def analyze(self, input_data: Dict[str, Any]) -> None:
        try:
            audit = self.memory.audit()
            recent_keys = sorted(audit.items(), key=lambda x: x[1]["timestamp"], reverse=True)[:5]
            decay_rates = [1 if v["decayed"] else 0 for _, v in recent_keys]
            avg_decay = np.mean(decay_rates) if decay_rates else 0.0
            forecast = ("stable" if avg_decay < self.decay_thresholds["stable"] else
                       "volatile" if avg_decay > self.decay_thresholds["volatile"] else "neutral")
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
    def __init__(self, name: str, memory: NexusMemory, virtue_weights: Dict[str, List[float]]):
        super().__init__(name, memory)
        self.tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased-finetuned-sst-2-english")
        self.model = AutoModel.from_pretrained("distilbert-base-uncased-finetuned-sst-2-english")
        self.sentiment_pipeline = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
        self.virtue_weights = {k: np.array(v) for k, v in virtue_weights.items()}
        self.federated_trainer = None

    def set_federated_trainer(self, trainer: FederatedTrainer):
        self.federated_trainer = trainer

    def analyze(self, input_data: Dict[str, Any]) -> None:
        try:
            text = input_data.get("text", "")
            if not text or not isinstance(text, str):
                self.result = {"error": "Invalid or empty text"}
                self.explanation = "VirtueAgent failed: Invalid or empty text."
                self.logger.warning(self.explanation)
                return

            mem_key = f"virtue_cache_{hashlib.md5(text.encode()).hexdigest()}"
            cached = self.memory.read(mem_key)
            if cached:
                self.result = {"virtue_profile": cached}
                self.explanation = f"VirtueAgent used cached profile: {cached}"
                self.influence.update({k: v for k, v in cached.items()})
                self.logger.info(self.explanation)
                return

            sentiment_result = self.sentiment_pipeline(text)[0]
            sentiment = 1.0 if sentiment_result["label"] == "POSITIVE" else -1.0
            sentiment_score = sentiment_result["score"]

            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            with torch.no_grad():
                outputs = self.model(**inputs)
            embeddings = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
            subjectivity = min(max(np.std(embeddings), 0.0), 1.0)
            neutrality = 1.0 - abs(sentiment)

            if self.federated_trainer:
                self.virtue_weights = self.federated_trainer.train(self.virtue_weights)
                self.memory.write("virtue_weights", {k: v.tolist() for k, v in self.virtue_weights.items()}, emotion_weight=0.9)

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

# === FLASK WEB UI ===
app = Flask(__name__, template_folder='templates')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            input_data = {
                "text": request.form.get("text", ""),
                "overrides": json.loads(request.form.get("overrides", "{}"))
            }
            council.dispatch(input_data)
            return render_template('reports.html', reports=council.get_reports())
        except Exception as e:
            logging.error(f"Error processing form: {e}")
            return render_template('index.html', error=str(e))
    return render_template('index.html', error=None)

@app.route('/reports')
def show_reports():
    return render_template('reports.html', reports=council.get_reports())

@app.route('/graph')
def show_graph():
    graph_file = "explainability_graph.html"
    council.draw_explainability_graph(graph_file)
    return send_file(graph_file)

@app.route('/charts')
def show_charts():
    reports = council.get_reports()
    virtue_data = reports.get("VirtueAgent", {}).get("result", {}).get("virtue_profile", {})
    influence_data = reports.get("MetaJudgeAgent", {}).get("result", {}).get("scores", [])
    return render_template('charts.html', virtue_data=virtue_data, influence_data=influence_data)

# === EXECUTION ===
def main():
    global council
    try:
        parser = argparse.ArgumentParser(description="AegisCouncil AI System")
        parser.add_argument('--config', default='config.json', help='Path to configuration file')
        parser.add_argument('--weights', type=str, help='JSON string for MetaJudgeAgent weights')
        parser.add_argument('--log-level', default='INFO', help='Logging level (DEBUG, INFO, WARNING, ERROR)')
        parser.add_argument('--agent-module', help='Path to custom agent module')
        parser.add_argument('--agent-class', help='Custom agent class name')
        args = parser.parse_args()

        config = load_config(args.config)
        if args.weights:
            try:
                config['meta_judge_weights'] = json.loads(args.weights)
            except json.JSONDecodeError:
                logging.error("Invalid weights JSON, using config file weights")

        setup_logging(config['log_level'])

        council = AegisCouncil(config)
        council.register_agent(MetaJudgeAgent("MetaJudgeAgent", council.memory, config["meta_judge_weights"]))
        council.register_agent(TemporalAgent("TemporalAgent", council.memory, config["temporal_decay_thresholds"]))
        virtue_agent = VirtueAgent("VirtueAgent", council.memory, config["virtue_weights"])
        virtue_agent.set_federated_trainer(council.federated_trainer)
        council.register_agent(virtue_agent)

        if args.agent_module and args.agent_class:
            council.register_dynamic_agent(args.agent_module, args.agent_class)

        sample_input = {
            "text": "We must stand for truth and help others with empathy and knowledge.",
            "overrides": {
                "EthosiaAgent": {"influence": 0.7, "reliability": 0.8, "severity": 0.6},
                "AegisCore": {"influence": 0.6, "reliability": 0.9, "severity": 0.7}
            }
        }

        success = council.dispatch(sample_input)
        if not success:
            print("Static dispatch failed. Check logs for details.")
        else:
            reports = council.get_reports()
            df = pd.DataFrame.from_dict(reports, orient='index')
            print("\nStatic Input Agent Reports:")
            print(df.to_string())
            council.draw_explainability_graph("static_explainability_graph.html")

        success = council.dispatch_realtime("empathy")
        if not success:
            print("Real-time dispatch failed. Check logs for details.")
        else:
            reports = council.get_reports()
            df = pd.DataFrame.from_dict(reports, orient='index')
            print("\nReal-Time Input Agent Reports:")
            print(df.to_string())
            council.draw_explainability_graph("realtime_explainability_graph.html")

        blockchain_valid = council.memory.blockchain.verify()
        print(f"\nBlockchain Integrity: {'Valid' if blockchain_valid else 'Invalid'}")

        print("\nStarting Flask server at http://localhost:5000")
        app.run(debug=False, host='0.0.0.0', port=5000)

    except Exception as e:
        logging.error(f"Main execution failed: {e}")

if __name__ == "__main__":
    main()