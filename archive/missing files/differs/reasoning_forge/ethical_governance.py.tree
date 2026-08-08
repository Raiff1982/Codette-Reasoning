"""
EthicalAIGovernance - Ethical Decision Framework
=================================================

Ported from J:\TheAI\src\framework\ethical_governance.py
Original design by Jonathan Harrison (Raiffs Bits LLC)

Ensures transparency, fairness, and respect in all AI responses.
Works alongside ColleenConscience (corruption detection) and
CoreGuardianSpindle (logical validation) to form a 3-layer ethical stack.

Role in the stack:
- EthicalAIGovernance: Query validation + response policy enforcement + audit
- ColleenConscience: Corruption/intent-loss detection in generated text
- CoreGuardianSpindle: Logical coherence and structural validation
"""

import re
import time
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class EthicalAIGovernance:
    """
    Ethical AI Governance Module.

    Enforces:
    - Transparency in decision-making
    - Fairness and bias mitigation
    - Privacy respect
    - Harmful content filtering
    - Audit logging for accountability
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.ethical_principles = self.config.get("ethical_considerations",
            "Always act with transparency, fairness, and respect for privacy.")

        # Harmful content patterns — only flag genuinely harmful promotion
        # (not discussions about these topics, which are legitimate)
        self.harmful_patterns = [
            r'\b(instructions?\s+to\s+(?:make|build|create)\s+(?:a\s+)?(?:bomb|weapon|explosive))',
            r'\b(how\s+to\s+(?:hack|steal|exploit)\s+(?:someone|people|user))',
        ]

        # Audit log
        self.audit_log: List[Dict] = []
        self._max_audit_entries = 100

    def validate_query(self, query: str) -> Dict[str, Any]:
        """
        Validate a user query for ethical concerns before processing.

        Args:
            query: User query

        Returns:
            {"valid": bool, "warnings": list, "suggestions": list}
        """
        result = {
            "valid": True,
            "warnings": [],
            "suggestions": []
        }

        for pattern in self.harmful_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                result["valid"] = False
                result["warnings"].append("Query may request harmful content")
                result["suggestions"].append("Please rephrase your question")

        return result

    def enforce_policies(self, response: str) -> Dict[str, Any]:
        """
        Enforce ethical policies on a generated response.

        Unlike Colleen (corruption detection) or Guardian (logic validation),
        this checks for ethical content issues in the actual output text.

        Args:
            response: AI-generated response

        Returns:
            {"passed": bool, "warnings": list, "filtered_response": str}
        """
        result = {
            "passed": True,
            "warnings": [],
            "filtered_response": response,
        }

        # Check for bias indicators
        bias_check = self._check_bias(response)
        if bias_check["has_bias"]:
            result["warnings"].extend(bias_check["warnings"])
            # Bias is a warning, not a hard block

        # Log the enforcement
        self._log_enforcement(result)

        return result

    def _check_bias(self, text: str) -> Dict[str, Any]:
        """Check text for potential bias patterns."""
        result = {
            "has_bias": False,
            "warnings": []
        }

        # Only flag strong stereotype patterns, not incidental word co-occurrence
        gendered_terms = [
            (r'\ball\s+(?:men|women)\s+are\b', "Broad gender generalization detected"),
            (r'\b(?:men|women)\s+(?:can\'t|cannot|shouldn\'t)\b', "Gender-limiting statement detected"),
        ]

        for pattern, warning in gendered_terms:
            if re.search(pattern, text, re.IGNORECASE):
                result["has_bias"] = True
                result["warnings"].append(warning)

        return result

    def get_ethical_guidelines(self) -> List[str]:
        """Get list of ethical guidelines."""
        return [
            "Transparency: All decisions must be explainable",
            "Fairness: No discrimination based on protected characteristics",
            "Privacy: Respect user data and confidentiality",
            "Safety: Prevent harmful outputs",
            "Accountability: Log all decisions for audit",
            "Beneficence: Act in the best interest of users"
        ]

    def _log_enforcement(self, result: Dict[str, Any]):
        """Log enforcement action for audit trail."""
        self.audit_log.append({
            "timestamp": time.time(),
            "passed": result["passed"],
            "warnings": result["warnings"]
        })

        # Trim to prevent unbounded growth
        if len(self.audit_log) > self._max_audit_entries:
            self.audit_log = self.audit_log[-self._max_audit_entries:]

    def get_audit_log(self, recent: int = 10) -> List[Dict]:
        """Get recent audit log entries."""
        return self.audit_log[-recent:]
