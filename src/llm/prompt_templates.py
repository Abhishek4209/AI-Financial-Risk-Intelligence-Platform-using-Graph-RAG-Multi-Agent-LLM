
"""Prompt templates; the LLM must never fabricate facts or citations (architecture.md)."""

SYSTEM_GUARDRAIL = (
    "You are a financial risk analyst assistant. Treat model scores as risk signals, never proof. "
    "Use only the supplied evidence; do not invent facts, figures, or citations. "
    "If evidence is insufficient, say so explicitly. Recommend human review instead of an automated decision."
)

RAG_QA_TEMPLATE = (
    "{system}\n\n"
    "Question: {question}\n\n"
    "Retrieved context (use only this; cite the source for each claim):\n{context}\n\n"
    "Answer using only the context above. If the context does not contain the answer, "
    "state that the information was not found in the available sources."
)

COMPLIANCE_QA_TEMPLATE = (
    "{system}\n\n"
    "Regulatory question: {question}\n\n"
    "Retrieved regulatory text:\n{context}\n\n"
    "Answer with the applicable regulation(s) and cite the source document for each point. "
    "If no retrieved text answers the question, say the information was not found."
)

FRAUD_INVESTIGATION_TEMPLATE = (
    "{system}\n\n"
    "Transaction type: {transaction_type}; amount: {amount}\n"
    "Model fraud risk score: {risk_score}; risk level: {risk_level}\n"
    "Top model factors:\n{drivers}\n\n"
    "Regulatory evidence:\n{evidence}\n\n"
    "Write 2-3 concise sentences interpreting these facts for an analyst. "
    "Do not state that fraud has been confirmed."
)

CREDIT_RISK_TEMPLATE = (
    "{system}\n\n"
    "Applicant dataset: {dataset}\n"
    "Model default probability: {probability}; risk band: {risk_band}\n"
    "Top model factors:\n{drivers}\n\n"
    "Write 2-3 concise sentences interpreting this credit-risk estimate for an analyst. "
    "Do not state that the loan should be automatically approved or rejected."
)


def render_rag_prompt(
    question: str,
    context: str,
    *,
    template: str = RAG_QA_TEMPLATE,
) -> str:
    return template.format(
        system=SYSTEM_GUARDRAIL,
        question=question,
        context=context or "No evidence was retrieved.",
    )


def render_fraud_prompt(
    transaction_type: str,
    amount: float,
    risk_score: float,
    risk_level: str,
    drivers: str,
    evidence: str,
) -> str:
    return FRAUD_INVESTIGATION_TEMPLATE.format(
        system=SYSTEM_GUARDRAIL,
        transaction_type=transaction_type,
        amount=amount,
        risk_score=risk_score,
        risk_level=risk_level,
        drivers=drivers or "No SHAP factors available.",
        evidence=evidence or "No regulatory evidence retrieved.",
    )


def render_credit_prompt(
    dataset: str,
    probability: float,
    risk_band: str,
    drivers: str,
) -> str:
    return CREDIT_RISK_TEMPLATE.format(
        system=SYSTEM_GUARDRAIL,
        dataset=dataset,
        probability=probability,
        risk_band=risk_band,
        drivers=drivers or "No SHAP factors available.",
    )
