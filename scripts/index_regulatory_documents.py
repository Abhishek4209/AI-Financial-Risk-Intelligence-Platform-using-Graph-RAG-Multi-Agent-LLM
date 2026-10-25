import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from src.services.risk_investigation import index_regulatory_documents


if __name__ == "__main__":
    print(json.dumps(index_regulatory_documents(), indent=2))
