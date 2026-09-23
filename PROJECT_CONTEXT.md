# AI-Financial-Risk-Intelligence

## 1. Project Overview

Build an enterprise-style **AI Financial Risk Intelligence Platform** for banking and financial-services use cases.

The platform should combine:

1. Credit Risk Assessment
2. Transaction Fraud Detection
3. Anti-Money Laundering (AML)
4. Customer Analytics
5. Financial Document RAG
6. Regulatory/Compliance Intelligence
7. Financial Sentiment Analysis
8. Financial Question Answering
9. Explainable AI using SHAP
10. Graph-based risk analysis
11. Multi-agent AI
12. REST API
13. Dashboard
14. Model evaluation and monitoring

The project must be designed like a real-world financial AI system rather than a collection of unrelated notebooks.

---

# 2. Main Business Goal

The system should help a financial institution answer questions such as:

* Is this customer likely to default?
* Is this transaction potentially fraudulent?
* Is this customer involved in suspicious transaction activity?
* Does this transaction/customer require manual investigation?
* Why did the ML model assign this risk?
* What regulatory policy is relevant?
* What does the customer's financial behavior indicate?
* What does a company's annual financial report say?
* What is the sentiment around a financial statement/news text?
* Can an analyst ask questions about financial documents using natural language?

The system should combine:

ML predictions + Explainability + Rules + Graph Analysis + RAG + LLMs

---

# 3. Important Design Principle

Do NOT merge unrelated datasets into one giant DataFrame.

Each dataset belongs to a specific business problem.

Use domain-specific pipelines and models.

Example:

IEEE-CIS → Transaction Fraud

PaySim → Mobile-money Fraud

European Credit Card → Credit-card Fraud Benchmark

IBM AMLSim → AML

Elliptic → Graph-based AML

Taiwan Credit Default → Credit Risk

Lending Club → Credit Risk

Bank Marketing → Customer Analytics

SEC Reports → Financial RAG

RBI/SEBI documents → Compliance RAG

Financial PhraseBank → Financial Sentiment

FiQA → Financial Q&A

---

# 4. Project Architecture

Use the following high-level architecture:

User / Analyst
|
v
Frontend Dashboard
|
v
FastAPI Backend
|
v
Risk Intelligence Service
|
+-------------------+
|                   |
v                   v
ML Models             RAG / LLM Layer
|                   |
|                   +--> SEC Documents
|                   +--> RBI Documents
|                   +--> SEBI Documents
|                   +--> Financial Knowledge
|
+--> Credit Risk
+--> Fraud Detection
+--> AML
+--> Customer Analytics
|
v
Explainability
|
+--> SHAP
+--> Feature Importance
|
v
Graph Analysis
|
v
Risk Decision Engine
|
+--> APPROVE
+--> MONITOR
+--> MANUAL_REVIEW
+--> BLOCK
|
v
Investigation / Risk Report

---

# 5. Development Strategy

Build the project in phases.

Do NOT attempt to implement everything simultaneously.

Each phase must work before moving to the next phase.

---

# PHASE 1 — Project Foundation

Create the complete repository structure.

Use:

AI-Financial-Risk-Intelligence/
│
├── README.md
├── LICENSE
├── .gitignore
├── requirements.txt
├── environment.yml
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── .env.example
│
├── configs/
├── data/
├── notebooks/
├── src/
├── frontend/
├── tests/
├── docs/
├── scripts/
├── models/
├── logs/
└── deployment/

Do not put datasets directly into GitHub.

Add data/, models/, logs/, and environment files to .gitignore where appropriate.

---

# PHASE 2 — Configuration

Create centralized configuration files.

configs/

├── config.yaml
├── database.yaml
├── llm_config.yaml
├── logging.yaml
└── prompts.yaml

Configuration should include:

* dataset paths
* model paths
* database settings
* embedding model
* vector database
* LLM settings
* logging
* API configuration

Never hard-code API keys.

Use environment variables.

---

# PHASE 3 — Data Organization

Create:

data/

├── raw/
├── processed/
├── external/
├── embeddings/
└── metadata/

Organize raw datasets:

data/raw/

├── credit_risk/
│
├── fraud/
│   ├── ieee_cis/
│   ├── paysim/
│   └── european/
│
├── aml/
│   ├── amlsim/
│   └── elliptic/
│
├── customer_analytics/
│   └── bank_marketing/
│
└── financial_documents/

Never mix datasets from different business domains without a clear schema-mapping strategy.

---

# PHASE 4 — Data Ingestion

Implement reusable ingestion modules:

src/ingestion/

├── csv_loader.py
├── excel_loader.py
├── pdf_loader.py
├── api_loader.py
└── parser.py

Requirements:

* validate file existence
* validate columns
* detect encoding
* handle missing values
* log ingestion
* return pandas DataFrames or standardized document objects
* never silently fail

For large datasets, support chunked reading.

---

# PHASE 5 — Exploratory Data Analysis

Create notebooks:

notebooks/

├── EDA_Credit_Risk.ipynb
├── EDA_Fraud.ipynb
├── EDA_AML.ipynb
├── EDA_Customer_Analytics.ipynb
└── EDA_Financial_Text.ipynb

For every dataset analyze:

* shape
* data types
* missing values
* duplicates
* target distribution
* numerical distributions
* categorical distributions
* outliers
* correlations
* class imbalance
* time patterns
* important business relationships

For fraud and AML, pay special attention to temporal patterns and class imbalance.

---

# PHASE 6 — Credit Risk

Use:

1. Taiwan Credit Card Default
2. Lending Club

Do NOT directly concatenate the datasets.

Build separate domain-specific models.

Target:

Taiwan:
default payment next month

Lending Club:
derive a carefully defined default/bad-loan target from loan_status.

Avoid data leakage.

Do not use information that would only become available after the outcome.

Pipeline:

Raw Data
→ Cleaning
→ Feature Engineering
→ Train/Validation Split
→ Model Training
→ Evaluation
→ Probability of Default
→ Risk Category
→ SHAP Explanation

Use models such as:

* Logistic Regression baseline
* Random Forest
* XGBoost
* LightGBM if available

Metrics:

* ROC-AUC
* PR-AUC
* Precision
* Recall
* F1
* Confusion Matrix
* Calibration

---

# PHASE 7 — Transaction Fraud Detection

Use three datasets separately:

1. IEEE-CIS
2. PaySim
3. European Credit Card Fraud

Create:

src/ml_models/fraud_detection/

├── ieee_cis/
├── paysim/
├── european/
├── fraud_aggregator.py
├── anomaly_detector.py
└── fraud_explainer.py

Each dataset gets its own preprocessing and feature engineering.

IEEE-CIS:

Target = isFraud

PaySim:

Target = isFraud

European:

Target = Class

Important:

Do not concatenate raw datasets.

Train domain-specific models.

Use:

* XGBoost
* LightGBM if available
* Logistic Regression baseline
* Isolation Forest for optional anomaly detection

Handle severe class imbalance.

Use:

* PR-AUC
* ROC-AUC
* Precision
* Recall
* F1
* confusion matrix

For fraud detection, do not rely on accuracy.

Use time-aware validation where appropriate.

---

# PHASE 8 — Fraud Feature Engineering

Examples:

IEEE-CIS:

* transaction day
* transaction hour
* log transaction amount
* missing feature count
* device-related features
* email-related features

PaySim:

* origin balance change
* destination balance change
* origin balance error
* destination balance error
* amount/origin balance ratio
* amount/destination balance ratio
* zero-balance indicators

European:

* transaction hour
* transaction day
* log amount

Keep feature engineering reproducible.

---

# PHASE 9 — AML

AML is a separate problem from transaction fraud.

Use:

1. IBM AMLSim
2. Elliptic as an optional graph-based dataset

Create:

src/ml_models/aml/

├── preprocessing.py
├── feature_engineering.py
├── anomaly_detection.py
├── graph_analysis.py
├── train.py
├── evaluate.py
└── predict.py

AML should analyze customer/account behavior rather than only individual transactions.

Generate features such as:

* transaction frequency
* transaction velocity
* total incoming amount
* total outgoing amount
* number of counterparties
* unique counterparties
* average transaction amount
* transaction amount variance
* incoming/outgoing ratio
* circular transaction indicators
* unusual transaction timing
* account network degree
* network centrality

Use:

* XGBoost/LightGBM where labels exist
* Isolation Forest
* clustering
* graph algorithms

For graph analysis use:

NetworkX initially.

Optionally support Neo4j for the enterprise version.

---

# PHASE 10 — AML Graph Analysis

Represent transactions as a graph.

Example:

Customer A
|
| ₹5,00,000
v
Customer B
|
| ₹4,80,000
v
Customer C
|
| ₹4,70,000
v
Customer D

Analyze:

* degree
* weighted degree
* PageRank
* connected components
* suspicious cycles
* fan-in
* fan-out
* transaction chains

The graph layer should generate suspicious-network evidence.

Do not automatically call every graph pattern money laundering.

Call it suspicious behavior requiring investigation.

---

# PHASE 11 — Customer Analytics

Use:

Bank Marketing Dataset.

This dataset is NOT an AML dataset and NOT a fraud dataset.

Use it for:

* customer propensity
* customer segmentation
* campaign response prediction

Target:

y

yes → subscribed

no → did not subscribe

Build:

1. Classification model
2. Optional customer segmentation

Models:

* Logistic Regression
* Random Forest
* XGBoost

Output:

subscription_probability

customer_segment

This module demonstrates customer analytics/business intelligence capability.

---

# PHASE 12 — Explainable AI

Use SHAP.

SHAP means:

SHapley Additive exPlanations.

For every important ML prediction provide:

* predicted probability
* risk level
* top positive contributors
* top negative contributors
* feature values

Example:

Fraud Probability: 94%

Top contributors:

Transaction Amount → +0.31

Transaction Type → +0.22

Balance Anomaly → +0.18

Transaction Frequency → +0.12

SHAP explains the model prediction.

It does NOT prove that fraud actually occurred.

Create:

src/ml_models/explainability/

├── shap_explainer.py
├── feature_importance.py
└── report.py

---

# PHASE 13 — Risk Decision Engine

Create a centralized decision engine.

Input:

* model probability
* AML score
* fraud score
* rule results
* transaction information
* graph risk

Output:

* risk score
* risk category
* decision
* reasons

Possible decisions:

APPROVE

MONITOR

MANUAL_REVIEW

BLOCK

Thresholds must be configurable.

Do not hard-code arbitrary thresholds as if they were regulatory requirements.

---

# PHASE 14 — Rules Engine

Create financial risk rules.

Examples:

* unusually high transaction amount
* rapid repeated transactions
* unusual geographic/device behavior
* many counterparties in short time
* suspicious fan-in/fan-out
* unusual balance changes
* known high-risk transaction patterns

Rules should produce:

rule_id

rule_name

triggered

severity

description

Do not automatically label a customer as a criminal based on a single rule.

---

# PHASE 15 — Financial Document RAG

Use financial documents such as:

* SEC annual reports
* company financial reports
* financial filings

Pipeline:

Documents
→ PDF/Text Extraction
→ Cleaning
→ Chunking
→ Metadata
→ Embeddings
→ Vector Database
→ Retrieval
→ Reranking
→ LLM
→ Answer

Store metadata:

* company
* document type
* reporting year
* page
* section
* source

The RAG system must return source citations.

---

# PHASE 16 — Compliance RAG

Use:

* RBI circulars
* RBI Master Directions
* SEBI circulars
* other legitimate regulatory documents

Pipeline:

Regulatory Documents
→ Chunking
→ Embeddings
→ Vector DB
→ Retrieval
→ Reranking
→ LLM

Questions could include:

"What regulation is relevant to this risk?"

"What customer due-diligence requirement applies?"

"What documentation should an analyst review?"

The LLM should not invent regulations.

If evidence is unavailable, clearly state that the information was not found.

---

# PHASE 17 — Hybrid Retrieval

Implement:

1. Vector search
2. BM25
3. Hybrid retrieval
4. Reranking

Architecture:

User Query
|
+------ Vector Search
|
+------ BM25
|
v
Hybrid Results
|
v
Reranker
|
v
Top Documents
|
v
LLM

---

# PHASE 18 — Graph RAG

Use Neo4j optionally.

Graph:

Customer
|
Transaction
|
Account
|
Company
|
Regulation

Combine:

Graph Retrieval
+
Vector Retrieval

Then send the retrieved evidence to the LLM.

This should be used for complex relationship questions.

---

# PHASE 19 — Financial Sentiment

Use:

Financial PhraseBank.

Task:

Classify financial text into:

* positive
* negative
* neutral

Possible models:

* Logistic Regression + TF-IDF
* Naive Bayes
* Transformer model

The sentiment model is separate from fraud/AML.

---

# PHASE 20 — Financial Q&A

Use:

FiQA.

Build a financial question-answering component.

Pipeline:

Question
→ Retrieval
→ Relevant financial information
→ LLM
→ Answer

Evaluate answer quality.

---

# PHASE 21 — Multi-Agent Architecture

Create:

src/agents/

├── supervisor.py
├── risk_agent.py
├── fraud_agent.py
├── aml_agent.py
├── compliance_agent.py
├── finance_agent.py
└── report_agent.py

Supervisor Agent:

Receives user request.

Determines which agent/tool should handle it.

Example:

"Is this transaction suspicious?"

Supervisor
→ Fraud Agent
→ AML Agent
→ Graph Analysis
→ SHAP
→ Compliance Agent
→ Report Agent

The supervisor should not blindly call every agent.

Use the minimum required tools.

---

# PHASE 22 — Investigation Report

Generate structured reports.

Example:

Customer:

CUST123

Fraud Probability:

82%

AML Risk:

HIGH

Decision:

MANUAL_REVIEW

Triggered Rules:

* High transaction velocity
* Unusual transaction amount
* Multiple counterparties

SHAP Evidence:

* Amount
* Transaction frequency
* Balance behavior

Graph Evidence:

* High fan-out
* Suspicious transaction chain

Regulatory Evidence:

Relevant retrieved RBI/SEBI document sections.

Final report should clearly distinguish:

1. Model prediction
2. Rule-based evidence
3. Graph evidence
4. Retrieved regulatory evidence
5. Human investigation requirement

---

# PHASE 23 — API

Use FastAPI.

Create endpoints such as:

POST /predict/fraud

POST /predict/credit-risk

POST /predict/aml

POST /customer/propensity

POST /investigation

POST /rag/query

POST /compliance/query

GET /health

Example fraud response:

{
"transaction_id": "TX123",
"fraud_probability": 0.92,
"risk_level": "HIGH",
"decision": "MANUAL_REVIEW",
"top_factors": [
"transaction_amount",
"transaction_velocity"
]
}

---

# PHASE 24 — Database

Use PostgreSQL for structured application data.

Store:

* customers
* transactions
* predictions
* risk scores
* investigation cases
* rules
* model versions
* audit logs

Use Redis optionally for:

* caching
* temporary results
* session data

Use vector DB for embeddings.

Use Neo4j optionally for graph relationships.

---

# PHASE 25 — Frontend

Build a simple professional financial-risk dashboard.

Pages:

1. Dashboard
2. Transaction Investigation
3. Fraud Detection
4. AML Investigation
5. Customer Risk
6. Customer Analytics
7. Financial Documents
8. Compliance
9. Reports

Dashboard should display:

* number of transactions
* fraud alerts
* AML alerts
* high-risk customers
* manual reviews
* model performance
* recent investigations

Do not overload the UI.

---

# PHASE 26 — Evaluation

Create:

src/evaluation/

├── classification_metrics.py
├── retrieval_metrics.py
├── ragas_eval.py
├── benchmark.py
└── model_comparison.py

ML metrics:

* Precision
* Recall
* F1
* ROC-AUC
* PR-AUC
* calibration

RAG metrics:

* retrieval precision
* retrieval recall
* faithfulness
* answer relevance
* context relevance

Do not use accuracy alone for highly imbalanced fraud datasets.

---

# PHASE 27 — Model Registry

Use MLflow optionally.

Track:

* model version
* parameters
* training dataset
* metrics
* feature version
* model artifact

Example:

fraud_ieee_v1

fraud_ieee_v2

aml_model_v1

credit_model_v1

---

# PHASE 28 — Monitoring

Monitor:

* prediction distribution
* fraud rate
* AML alert rate
* feature drift
* data quality
* model performance
* latency
* API errors

Add logging.

Do not log sensitive customer information unnecessarily.

---

# PHASE 29 — Testing

Create:

tests/

├── unit/
├── integration/
├── api/
└── performance/

Test:

* feature engineering
* preprocessing
* model loading
* prediction
* API endpoints
* RAG retrieval
* decision engine
* validation
* error handling

Every major module should have tests.

---

# PHASE 30 — Docker

Create:

Dockerfile

docker-compose.yml

Services may include:

* API
* PostgreSQL
* Redis
* vector database
* Neo4j
* frontend

Keep the first local version simple.

Add services incrementally.

---

# PHASE 31 — CI/CD

Create:

.github/workflows/

├── tests.yml
├── lint.yml
└── build.yml

Pipeline:

Git Push
→ Lint
→ Unit Tests
→ Integration Tests
→ Build Docker Image

---

# 32. Coding Standards

Use:

* Python 3.10+
* type hints
* docstrings
* PEP8
* modular functions
* reusable classes
* logging
* configuration files
* exception handling

Avoid:

* giant scripts
* hard-coded paths
* hard-coded API keys
* duplicate code
* unnecessary global variables
* data leakage
* unexplained magic numbers

Use pathlib for paths.

---

# 33. Data Leakage Rules

This project is intended for realistic financial ML.

Always prevent leakage.

Never use:

* future transaction information
* post-default information
* outcome-derived variables
* future customer behavior
* information unavailable at prediction time

Split temporal datasets appropriately.

Fit preprocessing only on training data.

---

# 34. Security

Never commit:

API keys

passwords

database credentials

private certificates

customer PII

Use:

.env

.env.example

Secrets must come from environment variables.

Add appropriate logging without exposing sensitive financial information.

---

# 35. Implementation Order

Copilot MUST implement the project in this exact order:

STEP 1
Project structure

STEP 2
Configuration

STEP 3
Data ingestion

STEP 4
EDA

STEP 5
Credit risk

STEP 6
Fraud detection

STEP 7
AML

STEP 8
Customer analytics

STEP 9
SHAP explainability

STEP 10
Risk/rules engine

STEP 11
Financial RAG

STEP 12
Compliance RAG

STEP 13
Hybrid retrieval

STEP 14
Graph analysis / Graph RAG

STEP 15
Financial sentiment

STEP 16
Financial Q&A

STEP 17
Multi-agent system

STEP 18
Investigation report generation

STEP 19
FastAPI

STEP 20
Database

STEP 21
Frontend

STEP 22
Testing

STEP 23
MLflow/model tracking

STEP 24
Monitoring

STEP 25
Docker

STEP 26
CI/CD

STEP 27
Documentation

---

# 36. Critical Copilot Rule

Do not generate the entire project in one response.

Implement one phase at a time.

For every phase:

1. Explain what will be created.
2. Create the required files.
3. Write production-quality code.
4. Explain important code.
5. Run/validate the code if possible.
6. Fix errors.
7. Add tests.
8. Update README/documentation.
9. Only then move to the next phase.

If an existing file is modified, preserve working functionality.

Do not overwrite working code unnecessarily.

---

# 37. Definition of Done

The project is complete only when:

* all major modules work independently
* models can make predictions
* SHAP explanations work
* AML graph analysis works
* RAG retrieves relevant evidence
* compliance RAG provides source information
* API works
* database works
* frontend communicates with API
* tests pass
* Docker builds successfully
* configuration is environment-based
* README explains setup and architecture
* example requests/responses are documented

The final system should demonstrate:

Machine Learning
+
Deep Learning where appropriate
+
Fraud Detection
+
AML
+
Credit Risk
+
Customer Analytics
+
Explainable AI
+
RAG
+
Graph Analytics
+
LLM
+
Agents
+
FastAPI
+
Database
+
Docker
+
Testing
+
Monitoring

This is an educational/portfolio financial intelligence platform. Model outputs are risk signals for investigation and decision support, not definitive proof of fraud, money laundering, or financial wrongdoing.
