"""
Recovered from the Codette archives — see RECOVERY_MANIFEST.md
"""


# Codette CLI Interface

import argparse
from universal_reasoning import UniversalReasoner

def main():
    parser = argparse.ArgumentParser(description="Codette CLI")
    parser.add_argument("--query", type=str, help="Input question or task")
    args = parser.parse_args()

    agent = UniversalReasoner()
    result = agent.analyze(args.query)
    print("Codette's Unified Response:")
    print(result)

if __name__ == "__main__":
    main()
