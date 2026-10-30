import json
from src.services.risk_investigation import index_regulatory_documents
if __name__ == "__main__":
    print(json.dumps(index_regulatory_documents(), indent=2))
