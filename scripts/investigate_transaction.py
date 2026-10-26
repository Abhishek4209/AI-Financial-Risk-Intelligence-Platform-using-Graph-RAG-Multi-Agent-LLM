import argparse
import json
from pathlib import Path
from src.services.risk_investigation import investigate_transaction
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a PaySim fraud investigation support report."
    )
    parser.add_argument("transaction_json", type=Path, help="Path to one PaySim transaction JSON object.")
    args = parser.parse_args()
    with args.transaction_json.open(encoding="utf-8") as transaction_file:
        transaction = json.load(transaction_file)
    if not isinstance(transaction, dict):
        parser.error("The input JSON must be one transaction object.")
    result = investigate_transaction(transaction)
    print(json.dumps(result, indent=2, ensure_ascii=True))
if __name__ == "__main__":
    main()
