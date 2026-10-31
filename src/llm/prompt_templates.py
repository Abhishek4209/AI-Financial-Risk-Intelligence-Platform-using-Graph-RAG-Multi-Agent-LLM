
"""Prompt templates for grounded financial risk and compliance answers."""

from __future__ import annotations


SYSTEM_GUARDRAIL = (
    "You are a careful financial risk analyst. "
    "Use only the supplied evidence for factual claims. "
    "Never invent facts, figures, policies, regulations, or citations. "
    "Do not describe general industry practices as company policies. "
    "Treat model predictions as risk signals, not proof. "
    "State clearly when the evidence does not answer the question."
)


RAG_QA_TEMPLATE = (
    "{system}\n\n"
    "Question: {question}\n\n"
    "Evidence:\n"
    "{context}\n\n"
    "Answer the question in 2 to 4 complete, clear sentences.\n"
    "Use only facts stated in the evidence above.\n"
    "Focus on the specific risk-management practices relevant to the question.\n"
    "Mention the source document and page when available.\n"
    "Do not add assumptions, generic practices, or unsupported controls.\n"
    "If the evidence does not answer the question, say:\n"
    "'The information was not found in the available sources.'\n"
    "Answer:"
)


COMPLIANCE_QA_TEMPLATE = (
    "{system}\n\n"
    "Question: {question}\n\n"
    "Regulatory and company evidence:\n"
    "{context}\n\n"
    "Answer in 2 to 4 complete, professional sentences.\n"
    "Distinguish regulatory requirements from company disclosures.\n"
    "Describe a company practice only when the evidence explicitly supports it.\n"
    "Mention the source and page when available.\n"
    "Never claim regulatory compliance without supporting evidence.\n"
    "If the evidence does not answer the question, say:\n"
    "'The information was not found in the available sources.'\n"
    "Answer:"
)


FRAUD_INVESTIGATION_TEMPLATE = (
    "{system}\n\n"
    "Transaction type: {transaction_type}; amount: {amount}\n"
    "Model fraud risk score: {risk_score}; risk level: {risk_level}\n"
    "Top model factors:\n{drivers}\n\n"
    "Regulatory evidence:\n{evidence}\n\n"
    "Write 2-3 concise sentences interpreting the supplied facts. "
    "Explain the model signal and relevant factors without treating them "
    "as proof of fraud. Refer to regulatory evidence only when it supports "
    "the statement. Do not invent controls or policies. "
    "Recommend human investigation where appropriate. "
    "Never state that fraud has been confirmed."
)


CREDIT_RISK_TEMPLATE = (
    "{system}\n\n"
    "Applicant dataset: {dataset}\n"
    "Model default probability: {probability}; risk band: {risk_band}\n"
    "Top model factors:\n{drivers}\n\n"
    "Write 2-3 concise sentences interpreting this credit-risk estimate. "
    "Explain the model estimate and supplied risk factors without presenting "
    "the prediction as certainty. Do not invent applicant information "
    "or financial history. Do not recommend automatic loan approval "
    "or rejection. Recommend human review before a credit decision."
)


def render_rag_prompt(
    question: str,
    context: str,
    *,
    template: str = RAG_QA_TEMPLATE,
) -> str:
    """Render a grounded question-answering prompt."""
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
    """Render a fraud-investigation prompt."""
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
    """Render a credit-risk interpretation prompt."""
    return CREDIT_RISK_TEMPLATE.format(
        system=SYSTEM_GUARDRAIL,
        dataset=dataset,
        probability=probability,
        risk_band=risk_band,
        drivers=drivers or "No SHAP factors available.",
    )
