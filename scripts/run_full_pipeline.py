#!/usr/bin/env python3
"""
Codette Full Training Pipeline
=================================

End-to-end pipeline orchestration for the Codette training lab.
Runs dataset generation, validation, reasoning forge enhancement,
adapter training, evaluation benchmarks, and observatory logging.

Each stage can be run independently or as part of the full pipeline.

Usage:
    # Run everything
    python scripts/run_full_pipeline.py --all

    # Run specific stages
    python scripts/run_full_pipeline.py --generate --validate
    python scripts/run_full_pipeline.py --forge --train
    python scripts/run_full_pipeline.py --evaluate

    # Select specific adapters
    python scripts/run_full_pipeline.py --all --adapters newton davinci quantum
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure the project root is on sys.path so sibling packages
# (training, evaluation, dataset_engine, etc.) are importable
# regardless of how the script is invoked.
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import yaml


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_pipeline_logging() -> logging.Logger:
    """Configure the pipeline logger with file and console handlers.

    Returns:
        Configured logger instance.
    """
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"pipeline_{timestamp}.log"

    logger = logging.getLogger("codette.pipeline")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    fh = logging.FileHandler(str(log_file), encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(fh)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    ))
    logger.addHandler(ch)

    return logger


# ---------------------------------------------------------------------------
# Configuration Loading
# ---------------------------------------------------------------------------

def load_pipeline_config(config_path: str = "configs/pipeline_config.yaml") -> dict:
    """Load the pipeline configuration from YAML.

    Args:
        config_path: Path to the pipeline config file.

    Returns:
        Parsed configuration dictionary.
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Pipeline config not found: {config_path}")

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_adapter_registry(config_path: str = "configs/adapter_registry.yaml") -> dict:
    """Load the adapter registry from YAML.

    Args:
        config_path: Path to the adapter registry file.

    Returns:
        Dictionary mapping adapter names to configurations.
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Adapter registry not found: {config_path}")

    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config.get("adapters", {})


# ---------------------------------------------------------------------------
# Observatory Metrics
# ---------------------------------------------------------------------------

class ObservatoryLogger:
    """Centralized metrics logger for the Codette observatory.

    Accumulates metrics from all pipeline stages and writes them
    to a JSON file for dashboard consumption.
    """

    def __init__(self, output_path: str = "observatory_metrics.json"):
        self.output_path = Path(output_path)
        self.metrics: list[dict] = []
        self.pipeline_start = datetime.now()

        # Load existing metrics if present
        if self.output_path.exists():
            try:
                with open(self.output_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                    if isinstance(existing, list):
                        self.metrics = existing
            except (json.JSONDecodeError, IOError):
                self.metrics = []

    def log(self, stage: str, adapter: str | None, data: dict) -> None:
        """Log a metrics entry.

        Args:
            stage: Pipeline stage name.
            adapter: Adapter name (or None for global metrics).
            data: Dictionary of metric values.
        """
        entry = {
            "stage": stage,
            "adapter": adapter,
            "timestamp": datetime.now().isoformat(),
            "pipeline_run": self.pipeline_start.isoformat(),
            **data,
        }
        self.metrics.append(entry)

    def save(self) -> None:
        """Write all metrics to disk."""
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(self.metrics, f, indent=2)


# ---------------------------------------------------------------------------
# Stage 1: Dataset Generation
# ---------------------------------------------------------------------------

def stage_generate(
    registry: dict,
    pipeline_config: dict,
    adapter_names: list[str],
    observatory: ObservatoryLogger,
    logger: logging.Logger,
) -> dict[str, dict]:
    """Generate training datasets for selected adapters.

    Uses the dataset_engine module to produce JSONL files
    with chat-format training examples.

    Args:
        registry: Adapter registry configuration.
        pipeline_config: Pipeline configuration.
        adapter_names: List of adapter names to generate for.
        observatory: Metrics logger.
        logger: Logger instance.

    Returns:
        Dictionary mapping adapter names to generation results.
    """
    logger.info("=" * 60)
    logger.info("STAGE 1: Dataset Generation")
    logger.info("=" * 60)

    gen_config = pipeline_config.get("generation", {})
    output_dir = pipeline_config.get("pipeline", {}).get(
        "dataset_output_dir", "./datasets"
    )
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    results = {}

    try:
        from dataset_engine import DatasetGenerator
    except ImportError:
        logger.warning(
            "dataset_engine module not available. "
            "Checking for existing dataset files instead."
        )
        for name in adapter_names:
            adapter_cfg = registry.get(name, {})
            dataset_path = adapter_cfg.get("dataset", "")
            exists = Path(dataset_path).exists()
            count = 0
            if exists:
                with open(dataset_path, "r", encoding="utf-8") as f:
                    count = sum(1 for line in f if line.strip())
            results[name] = {
                "status": "exists" if exists else "missing",
                "examples": count,
                "path": dataset_path,
            }
            observatory.log("generate", name, results[name])
            if exists:
                logger.info(f"  {name}: found {count} existing examples")
            else:
                logger.warning(f"  {name}: dataset missing at {dataset_path}")
        return results

    seed = pipeline_config.get("pipeline", {}).get("seed", 42)
    generator = DatasetGenerator(output_dir=output_dir, seed=seed)

    for name in adapter_names:
        adapter_cfg = registry.get(name, {})
        dataset_path = adapter_cfg.get("dataset", "")
        target_examples = adapter_cfg.get("target_examples", 2000)

        logger.info(f"Generating dataset for: {name}")
        logger.info(f"  Target: {target_examples} examples")
        logger.info(f"  Output: {dataset_path}")

        start_time = time.time()
        try:
            generated_path = generator.generate_adapter(
                adapter=name,
                count=target_examples,
            )
            # Count the generated examples
            count = 0
            with open(generated_path, "r", encoding="utf-8") as f:
                count = sum(1 for line in f if line.strip())
            elapsed = time.time() - start_time

            results[name] = {
                "status": "generated",
                "examples": count,
                "path": generated_path,
                "time_seconds": elapsed,
            }
            logger.info(
                f"  Generated {count} examples in {elapsed:.1f}s"
            )

        except Exception as e:
            elapsed = time.time() - start_time
            results[name] = {
                "status": "error",
                "error": str(e),
                "time_seconds": elapsed,
            }
            logger.error(f"  Generation failed for {name}: {e}")

        observatory.log("generate", name, results[name])

    return results


# ---------------------------------------------------------------------------
# Stage 2: Dataset Validation
# ---------------------------------------------------------------------------

def stage_validate(
    registry: dict,
    pipeline_config: dict,
    adapter_names: list[str],
    observatory: ObservatoryLogger,
    logger: logging.Logger,
) -> dict[str, dict]:
    """Validate generated datasets for quality and correctness.

    Checks for proper JSON structure, required message roles,
    minimum token counts, and duplicate detection.

    Args:
        registry: Adapter registry configuration.
        pipeline_config: Pipeline configuration.
        adapter_names: List of adapter names to validate.
        observatory: Metrics logger.
        logger: Logger instance.

    Returns:
        Dictionary mapping adapter names to validation results.
    """
    logger.info("=" * 60)
    logger.info("STAGE 2: Dataset Validation")
    logger.info("=" * 60)

    val_config = pipeline_config.get("validation", {})
    min_tokens = val_config.get("min_tokens", 40)
    max_dup_sim = val_config.get("max_duplicate_similarity", 0.85)
    required_roles = set(val_config.get("required_roles", ["system", "user", "assistant"]))

    results = {}

    for name in adapter_names:
        adapter_cfg = registry.get(name, {})
        dataset_path = adapter_cfg.get("dataset", "")

        logger.info(f"Validating: {name} ({dataset_path})")

        if not Path(dataset_path).exists():
            results[name] = {
                "status": "missing",
                "error": f"Dataset file not found: {dataset_path}",
            }
            observatory.log("validate", name, results[name])
            logger.warning(f"  SKIP: dataset file not found")
            continue

        total = 0
        valid = 0
        errors = {
            "json_parse": 0,
            "missing_messages": 0,
            "missing_roles": 0,
            "too_short": 0,
        }

        try:
            with open(dataset_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    total += 1

                    # Parse JSON
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        errors["json_parse"] += 1
                        continue

                    # Check messages key
                    messages = record.get("messages")
                    if not isinstance(messages, list) or len(messages) < 2:
                        errors["missing_messages"] += 1
                        continue

                    # Check required roles
                    found_roles = {m.get("role") for m in messages if isinstance(m, dict)}
                    if not required_roles.issubset(found_roles):
                        errors["missing_roles"] += 1
                        continue

                    # Check minimum content length
                    total_words = sum(
                        len(m.get("content", "").split())
                        for m in messages
                        if isinstance(m, dict)
                    )
                    if total_words < min_tokens:
                        errors["too_short"] += 1
                        continue

                    valid += 1

            error_count = sum(errors.values())
            pass_rate = (valid / total * 100) if total > 0 else 0

            results[name] = {
                "status": "valid" if pass_rate > 90 else "warning",
                "total_records": total,
                "valid_records": valid,
                "error_records": error_count,
                "pass_rate": round(pass_rate, 2),
                "errors": errors,
            }

            level = logging.INFO if pass_rate > 90 else logging.WARNING
            logger.log(
                level,
                f"  {name}: {valid}/{total} valid "
                f"({pass_rate:.1f}% pass rate)",
            )
            if error_count > 0:
                for error_type, count in errors.items():
                    if count > 0:
                        logger.log(level, f"    {error_type}: {count}")

        except Exception as e:
            results[name] = {
                "status": "error",
                "error": str(e),
            }
            logger.error(f"  Validation failed for {name}: {e}")

        observatory.log("validate", name, results[name])

    return results


# ---------------------------------------------------------------------------
# Stage 3: Reasoning Forge
# ---------------------------------------------------------------------------

def stage_forge(
    registry: dict,
    pipeline_config: dict,
    adapter_names: list[str],
    observatory: ObservatoryLogger,
    logger: logging.Logger,
) -> dict[str, dict]:
    """Run the reasoning forge to enhance datasets with multi-agent reasoning.

    Each dataset is processed through the forge's multi-agent pipeline,
    which adds analytical depth from multiple perspectives.

    Args:
        registry: Adapter registry configuration.
        pipeline_config: Pipeline configuration.
        adapter_names: List of adapter names to process.
        observatory: Metrics logger.
        logger: Logger instance.

    Returns:
        Dictionary mapping adapter names to forge results.
    """
    logger.info("=" * 60)
    logger.info("STAGE 3: Reasoning Forge")
    logger.info("=" * 60)

    results = {}

    try:
        from reasoning_forge import ForgeEngine
    except ImportError:
        logger.warning(
            "reasoning_forge module not available. Skipping forge stage."
        )
        for name in adapter_names:
            results[name] = {"status": "skipped", "reason": "module_not_available"}
            observatory.log("forge", name, results[name])
        return results

    try:
        forge = ForgeEngine()
    except Exception as e:
        logger.error(f"Failed to initialize forge engine: {e}")
        for name in adapter_names:
            results[name] = {"status": "error", "error": str(e)}
            observatory.log("forge", name, results[name])
        return results

    for name in adapter_names:
        adapter_cfg = registry.get(name, {})
        dataset_path = adapter_cfg.get("dataset", "")

        if not Path(dataset_path).exists():
            results[name] = {"status": "skipped", "reason": "dataset_missing"}
            observatory.log("forge", name, results[name])
            logger.warning(f"  SKIP {name}: dataset not found")
            continue

        logger.info(f"Forging: {name}")
        start_time = time.time()

        try:
            # Read existing examples
            examples = []
            with open(dataset_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        examples.append(json.loads(line))

            enhanced_count = 0
            enhanced_examples = []

            for i, example in enumerate(examples):
                messages = example.get("messages", [])
                # Extract user query for forge input
                user_msg = next(
                    (m["content"] for m in messages if m.get("role") == "user"),
                    None,
                )
                if not user_msg:
                    enhanced_examples.append(example)
                    continue

                try:
                    forge_result = forge.forge_single(user_msg)
                    synthesis = None
                    if forge_result:
                        # forge_single returns a chat-format dict;
                        # extract the assistant response as the synthesis
                        for m in forge_result.get("messages", []):
                            if m.get("role") == "assistant":
                                synthesis = m.get("content")
                                break
                    if synthesis:
                        # Enhance the assistant response with forge synthesis
                        for msg in messages:
                            if msg.get("role") == "assistant":
                                original = msg["content"]
                                msg["content"] = (
                                    f"{original}\n\n"
                                    f"[Multi-perspective synthesis]: {synthesis}"
                                )
                                enhanced_count += 1
                                break
                except Exception:
                    pass  # Keep original if forge fails on individual example

                enhanced_examples.append(example)

            # Write enhanced dataset back
            with open(dataset_path, "w", encoding="utf-8") as f:
                for ex in enhanced_examples:
                    f.write(json.dumps(ex, ensure_ascii=False) + "\n")

            elapsed = time.time() - start_time
            results[name] = {
                "status": "success",
                "total_examples": len(examples),
                "enhanced_examples": enhanced_count,
                "time_seconds": elapsed,
            }
            logger.info(
                f"  {name}: enhanced {enhanced_count}/{len(examples)} "
                f"examples in {elapsed:.1f}s"
            )

        except Exception as e:
            elapsed = time.time() - start_time
            results[name] = {
                "status": "error",
                "error": str(e),
                "time_seconds": elapsed,
            }
            logger.error(f"  Forge failed for {name}: {e}")

        observatory.log("forge", name, results[name])

    return results


# ---------------------------------------------------------------------------
# Stage 4: Training
# ---------------------------------------------------------------------------

def stage_train(
    registry: dict,
    pipeline_config: dict,
    adapter_names: list[str],
    observatory: ObservatoryLogger,
    logger: logging.Logger,
) -> dict[str, dict]:
    """Train LoRA adapters for selected perspectives.

    Delegates to training.train_all_adapters for the actual
    training loop.

    Args:
        registry: Adapter registry configuration.
        pipeline_config: Pipeline configuration.
        adapter_names: List of adapter names to train.
        observatory: Metrics logger.
        logger: Logger instance.

    Returns:
        Dictionary mapping adapter names to training results.
    """
    logger.info("=" * 60)
    logger.info("STAGE 4: Adapter Training")
    logger.info("=" * 60)

    results = {}

    try:
        from training.train_all_adapters import (
            load_training_config,
            train_single_adapter,
        )
    except ImportError:
        logger.error("training module not available")
        for name in adapter_names:
            results[name] = {"status": "error", "error": "module_not_available"}
            observatory.log("train", name, results[name])
        return results

    training_defaults = load_training_config()
    output_dir = pipeline_config.get("pipeline", {}).get(
        "adapter_output_dir", "./adapters"
    )

    for name in adapter_names:
        adapter_cfg = registry.get(name, {})
        dataset_path = adapter_cfg.get("dataset", "")

        if not Path(dataset_path).exists():
            results[name] = {"status": "skipped", "reason": "dataset_missing"}
            observatory.log("train", name, results[name])
            logger.warning(f"  SKIP {name}: dataset not found at {dataset_path}")
            continue

        logger.info(f"Training adapter: {name}")
        metrics = train_single_adapter(
            adapter_name=name,
            adapter_config=adapter_cfg,
            training_defaults=training_defaults,
            output_base_dir=output_dir,
            logger=logger,
        )
        results[name] = metrics
        observatory.log("train", name, metrics)

    return results


# ---------------------------------------------------------------------------
# Stage 5: Evaluation
# ---------------------------------------------------------------------------

def stage_evaluate(
    registry: dict,
    pipeline_config: dict,
    adapter_names: list[str],
    observatory: ObservatoryLogger,
    logger: logging.Logger,
) -> dict[str, dict]:
    """Run evaluation benchmarks on trained adapters.

    Uses the evaluation module to run reasoning tests and
    compute quality metrics.

    Args:
        registry: Adapter registry configuration.
        pipeline_config: Pipeline configuration.
        adapter_names: List of adapter names to evaluate.
        observatory: Metrics logger.
        logger: Logger instance.

    Returns:
        Dictionary mapping adapter names to evaluation results.
    """
    logger.info("=" * 60)
    logger.info("STAGE 5: Evaluation")
    logger.info("=" * 60)

    eval_config = pipeline_config.get("evaluation", {})
    results = {}

    try:
        from evaluation import ReasoningMetrics
    except ImportError:
        logger.warning(
            "evaluation module not fully available. "
            "Running basic dataset statistics instead."
        )
        for name in adapter_names:
            adapter_cfg = registry.get(name, {})
            dataset_path = adapter_cfg.get("dataset", "")

            if not Path(dataset_path).exists():
                results[name] = {"status": "skipped", "reason": "dataset_missing"}
                observatory.log("evaluate", name, results[name])
                continue

            # Basic stats as fallback evaluation
            total = 0
            total_words = 0
            total_turns = 0

            try:
                with open(dataset_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        record = json.loads(line)
                        messages = record.get("messages", [])
                        total += 1
                        total_turns += len(messages)
                        for msg in messages:
                            if isinstance(msg, dict):
                                total_words += len(
                                    msg.get("content", "").split()
                                )

                avg_words = total_words / total if total > 0 else 0
                avg_turns = total_turns / total if total > 0 else 0

                results[name] = {
                    "status": "basic_stats",
                    "total_examples": total,
                    "avg_words_per_example": round(avg_words, 1),
                    "avg_turns_per_example": round(avg_turns, 1),
                    "total_words": total_words,
                }
                logger.info(
                    f"  {name}: {total} examples, "
                    f"avg {avg_words:.0f} words, "
                    f"avg {avg_turns:.1f} turns"
                )

            except Exception as e:
                results[name] = {"status": "error", "error": str(e)}
                logger.error(f"  Evaluation failed for {name}: {e}")

            observatory.log("evaluate", name, results[name])

        return results

    # Full evaluation: score training-data assistant responses as a
    # quality proxy (actual inference evaluation requires a loaded model).
    metrics = ReasoningMetrics()

    for name in adapter_names:
        adapter_cfg = registry.get(name, {})
        dataset_path = adapter_cfg.get("dataset", "")

        if not Path(dataset_path).exists():
            results[name] = {"status": "skipped", "reason": "dataset_missing"}
            observatory.log("evaluate", name, results[name])
            logger.warning(f"  SKIP {name}: dataset not found")
            continue

        logger.info(f"Evaluating adapter: {name}")
        start_time = time.time()

        try:
            # Extract assistant responses from the training data
            responses: list[str] = []
            with open(dataset_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    record = json.loads(line)
                    for msg in record.get("messages", []):
                        if msg.get("role") == "assistant":
                            responses.append(msg["content"])

            # Score with ReasoningMetrics
            batch_scores = metrics.score_batch(responses)

            # Compute per-dimension averages
            if batch_scores:
                dim_keys = [k for k in batch_scores[0] if isinstance(batch_scores[0][k], (int, float))]
                avg_scores = {
                    k: round(sum(s[k] for s in batch_scores) / len(batch_scores), 4)
                    for k in dim_keys
                }
            else:
                avg_scores = {}

            elapsed = time.time() - start_time
            results[name] = {
                "status": "evaluated",
                "total_responses": len(responses),
                "scores": avg_scores,
                "time_seconds": elapsed,
            }
            logger.info(
                f"  {name}: scored {len(responses)} responses, "
                f"overall={avg_scores.get('overall', 0):.3f} "
                f"in {elapsed:.1f}s"
            )

        except Exception as e:
            elapsed = time.time() - start_time
            results[name] = {
                "status": "error",
                "error": str(e),
                "time_seconds": elapsed,
            }
            logger.error(f"  Evaluation failed for {name}: {e}")

        observatory.log("evaluate", name, results[name])

    return results


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

def print_dashboard(
    all_results: dict[str, dict[str, dict]],
    total_time: float,
    logger: logging.Logger,
) -> None:
    """Print a comprehensive pipeline dashboard.

    Args:
        all_results: Nested dictionary of {stage: {adapter: results}}.
        total_time: Total pipeline execution time in seconds.
        logger: Logger instance.
    """
    logger.info("")
    logger.info("=" * 72)
    logger.info("  CODETTE TRAINING PIPELINE DASHBOARD")
    logger.info("=" * 72)
    logger.info(f"  Total time: {total_time:.1f}s ({total_time / 60:.1f} min)")
    logger.info(f"  Timestamp:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")

    # Collect all adapter names across stages
    all_adapters = set()
    for stage_results in all_results.values():
        all_adapters.update(stage_results.keys())
    all_adapters = sorted(all_adapters)

    stages = ["generate", "validate", "forge", "train", "evaluate"]

    # Header
    header = f"{'Adapter':<20}"
    for stage in stages:
        if stage in all_results:
            header += f" {stage[:8]:^10}"
    logger.info(header)
    logger.info("-" * 72)

    # Rows
    for adapter in all_adapters:
        row = f"{adapter:<20}"
        for stage in stages:
            if stage not in all_results:
                continue
            result = all_results.get(stage, {}).get(adapter, {})
            status = result.get("status", "---")

            # Color-code statuses with symbols
            if status in ("success", "generated", "valid", "evaluated", "exists"):
                symbol = "OK"
            elif status in ("warning", "basic_stats"):
                symbol = "WARN"
            elif status in ("skipped",):
                symbol = "SKIP"
            elif status in ("error", "missing"):
                symbol = "FAIL"
            else:
                symbol = status[:8]

            row += f" {symbol:^10}"

        logger.info(row)

    logger.info("-" * 72)

    # Stage summaries
    logger.info("")
    for stage_name, stage_results in all_results.items():
        if not stage_results:
            continue
        ok = sum(
            1 for r in stage_results.values()
            if r.get("status") in ("success", "generated", "valid", "evaluated", "exists", "basic_stats")
        )
        fail = sum(
            1 for r in stage_results.values()
            if r.get("status") in ("error", "missing")
        )
        skip = sum(
            1 for r in stage_results.values()
            if r.get("status") == "skipped"
        )
        logger.info(
            f"  {stage_name:<12}: {ok} ok, {fail} failed, {skip} skipped"
        )

    # Training-specific stats
    train_results = all_results.get("train", {})
    if train_results:
        logger.info("")
        logger.info("  Training Details:")
        for name, metrics in train_results.items():
            if metrics.get("status") == "success":
                loss = metrics.get("final_loss", 0)
                steps = metrics.get("total_steps", 0)
                t = metrics.get("training_time_seconds", 0)
                logger.info(
                    f"    {name:<16}: loss={loss:.4f}, "
                    f"steps={steps}, time={t:.1f}s"
                )

    # Validation stats
    val_results = all_results.get("validate", {})
    if val_results:
        logger.info("")
        logger.info("  Validation Details:")
        for name, metrics in val_results.items():
            if "pass_rate" in metrics:
                total = metrics.get("total_records", 0)
                valid = metrics.get("valid_records", 0)
                rate = metrics.get("pass_rate", 0)
                logger.info(
                    f"    {name:<16}: {valid}/{total} valid ({rate:.1f}%)"
                )

    logger.info("")
    logger.info("=" * 72)


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Codette Full Training Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Stage selection
    parser.add_argument("--all", action="store_true", help="Run all stages")
    parser.add_argument(
        "--generate", action="store_true", help="Stage 1: Generate datasets"
    )
    parser.add_argument(
        "--validate", action="store_true", help="Stage 2: Validate datasets"
    )
    parser.add_argument(
        "--forge", action="store_true", help="Stage 3: Run reasoning forge"
    )
    parser.add_argument(
        "--train", action="store_true", help="Stage 4: Train adapters"
    )
    parser.add_argument(
        "--evaluate", action="store_true", help="Stage 5: Run evaluations"
    )

    # Options
    parser.add_argument(
        "--adapters",
        nargs="+",
        default=None,
        help="Specific adapters to process (default: all in registry)",
    )
    parser.add_argument(
        "--pipeline-config",
        type=str,
        default="configs/pipeline_config.yaml",
        help="Path to pipeline configuration",
    )
    parser.add_argument(
        "--adapter-registry",
        type=str,
        default="configs/adapter_registry.yaml",
        help="Path to adapter registry",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed (overrides config)",
    )

    return parser.parse_args()


def main():
    """Main entry point for the Codette training pipeline."""
    args = parse_args()

    # Determine which stages to run
    run_all = args.all
    stages = {
        "generate": args.generate or run_all,
        "validate": args.validate or run_all,
        "forge": args.forge or run_all,
        "train": args.train or run_all,
        "evaluate": args.evaluate or run_all,
    }

    if not any(stages.values()):
        print(
            "No stages selected. Use --all or specify stages "
            "(--generate, --validate, --forge, --train, --evaluate)"
        )
        sys.exit(1)

    # Setup
    logger = setup_pipeline_logging()
    logger.info("=== Codette Training Pipeline ===")
    logger.info(f"Stages: {[s for s, enabled in stages.items() if enabled]}")

    # Load configuration
    try:
        pipeline_config = load_pipeline_config(args.pipeline_config)
        registry = load_adapter_registry(args.adapter_registry)
    except FileNotFoundError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Set random seed
    seed = args.seed or pipeline_config.get("pipeline", {}).get("seed", 42)
    import random
    import numpy as np
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass
    logger.info(f"Random seed: {seed}")

    # Determine adapters
    if args.adapters:
        adapter_names = args.adapters
        unknown = [n for n in adapter_names if n not in registry]
        if unknown:
            logger.error(
                f"Unknown adapters: {unknown}. "
                f"Available: {list(registry.keys())}"
            )
            sys.exit(1)
    else:
        adapter_names = list(registry.keys())

    logger.info(f"Adapters ({len(adapter_names)}): {adapter_names}")

    # Initialize observatory
    observatory = ObservatoryLogger()

    # Run pipeline stages
    all_results: dict[str, dict[str, dict]] = {}
    pipeline_start = time.time()

    if stages["generate"]:
        all_results["generate"] = stage_generate(
            registry, pipeline_config, adapter_names, observatory, logger
        )

    if stages["validate"]:
        all_results["validate"] = stage_validate(
            registry, pipeline_config, adapter_names, observatory, logger
        )

    if stages["forge"]:
        all_results["forge"] = stage_forge(
            registry, pipeline_config, adapter_names, observatory, logger
        )

    if stages["train"]:
        all_results["train"] = stage_train(
            registry, pipeline_config, adapter_names, observatory, logger
        )

    if stages["evaluate"]:
        all_results["evaluate"] = stage_evaluate(
            registry, pipeline_config, adapter_names, observatory, logger
        )

    total_time = time.time() - pipeline_start

    # Save observatory metrics
    observatory.log("pipeline", None, {
        "total_time_seconds": total_time,
        "stages_run": [s for s, enabled in stages.items() if enabled],
        "adapters_processed": adapter_names,
    })
    observatory.save()
    logger.info(f"Observatory metrics saved to: {observatory.output_path}")

    # Print dashboard
    print_dashboard(all_results, total_time, logger)

    # Save pipeline results
    results_path = Path("logs") / "pipeline_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "total_time_seconds": total_time,
                "seed": seed,
                "stages": {s: e for s, e in stages.items()},
                "adapters": adapter_names,
                "results": all_results,
            },
            f,
            indent=2,
        )
    logger.info(f"Pipeline results saved to: {results_path}")

    # Check for failures
    has_failures = False
    for stage_results in all_results.values():
        for result in stage_results.values():
            if result.get("status") == "error":
                has_failures = True
                break

    if has_failures:
        logger.warning("Pipeline completed with errors. Check logs for details.")
        sys.exit(1)
    else:
        logger.info("Pipeline completed successfully.")


if __name__ == "__main__":
    main()
