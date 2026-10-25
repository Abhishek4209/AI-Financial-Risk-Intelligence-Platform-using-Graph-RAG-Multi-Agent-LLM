# Transaction Risk Investigation

The PaySim workflow runs in this order:

1. Build the saved model's training features from one transaction.
2. Load `models/Fraud_models/paysim_fraud_model.pkl` and calculate its fraud score.
3. Explain the prediction with SHAP.
4. Retrieve regulatory evidence from the local FAISS index (Pinecone is optional).
5. Ask a local Hugging Face model for an analyst-support report grounded in the supplied evidence (Ollama is optional).

A score is a model risk signal, not proof of fraud. The model artifact's stored threshold is used for the `HIGH` label; the report asks for human review and does not make an automated adverse decision.

## Setup

Install the project dependencies and use the same Python environment for the notebook and commands. The default local workflow requires the packages in `requirements.txt`, including `xgboost`, `shap`, `faiss-cpu`, and `langchain-huggingface`.

Vector storage:

- Pinecone is the default vector store. Set `PINECONE_API_KEY` and `PINECONE_INDEX_NAME` in `.env`; the indexer creates the index if needed, using the local BGE model's 384 dimensions and cosine similarity. `PINECONE_CLOUD` and `PINECONE_REGION` default to `aws` and `us-east-1`. Without credentials, the app fails clearly instead of silently writing vectors locally.
- To explicitly use local FAISS for development only, set `RAG_VECTOR_BACKEND=faiss`; its index is stored at `vector_store/financial_rag_faiss`.
- `RAG_DOCUMENT_ORGANIZATIONS=FATF,RBI,SEBI,American_Express` sets the default index sources; set it to `all` to include every organization folder.
- `RAG_EMBEDDING_MODEL=models/embeddings` loads the existing local `BAAI/bge-small-en-v1.5` model and creates 384-dimensional embeddings.
- `RISK_REPORT_PROVIDER=huggingface` uses `google/flan-t5-small` for report generation.
- `HF_REPORT_MODEL` can override the Hugging Face report model.

The first run downloads the embedding and report models if they are not cached. To use Ollama instead, start Ollama, pull a chat model, then set `RISK_REPORT_PROVIDER=ollama`; `OLLAMA_BASE_URL` defaults to `http://localhost:11434` and `OLLAMA_MODEL` defaults to `llama3.1`.

From the repository root, index the PDF and HTML documents under `data/raw/Documents`:

```powershell
python -m scripts.index_regulatory_documents
```

The command indexes FATF, RBI, SEBI, and American Express files by default. Set `RAG_DOCUMENT_ORGANIZATIONS=all` to include other local organization folders. By default, chunks are upserted with stable IDs into Pinecone. FAISS is used only when explicitly selected for development.

## Investigate A Transaction

Provide one JSON object using the PaySim model's training schema:

```json
{
  "transaction_id": "T10045",
  "step": 49,
  "type": "TRANSFER",
  "amount": 850000,
  "oldbalanceOrg": 900000,
  "newbalanceOrig": 50000,
  "oldbalanceDest": 10000,
  "newbalanceDest": 860000
}
```

Run the investigation from the repository root:

```powershell
python -m scripts.investigate_transaction transaction.json
```

The JSON result contains the score and threshold, SHAP drivers, retrieval query, cited evidence metadata, report text, and human-review flag. Inputs from other datasets (for example, age, beneficiary novelty, or daily transaction frequency) are not accepted as model features by this PaySim artifact. A different schema requires a separately trained model and matching feature preparation.
