from __future__ import annotations

import sys
import types
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src.embeddings import embedding_pipeline
from src.embeddings import cache as embedding_cache
from src.ingestion import api_loader, csv_loader, email_loader, excel_loader, parser, pdf_loader
from src.preprocessing import chunking, cleaner, feature_engineering, metadata, ocr
from src import preprocessing
from src.utils import helpers, validators


def _install_module(monkeypatch, name: str, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)
    return module


def test_helpers_resolve_paths_load_yaml_and_serialize_values(tmp_path):
    assert helpers.resolve_path("child.txt", root=tmp_path) == (
        tmp_path / "child.txt"
    ).resolve()
    assert helpers.env_or_config("MISSING_SETTING", {"setting": "yaml"}, "setting") == "yaml"

    config_path = tmp_path / "config.yaml"
    config_path.write_text("answer: 42\n", encoding="utf-8")
    assert helpers.load_yaml(config_path) == {"answer": 42}
    config_path.write_text("- item\n", encoding="utf-8")
    with pytest.raises(ValueError, match="root must be a mapping"):
        helpers.load_yaml(config_path)

    value = {"array": np.array([1, 2]), 4: (np.int64(3),)}
    assert helpers.json_safe(value) == {"array": [1, 2], "4": [3]}
    assert '"array": [1, 2]' in helpers.json_dumps(value)


def test_yaml_empty_configuration_and_environment_override(tmp_path, monkeypatch):
    empty_path = tmp_path / "empty.yaml"
    empty_path.write_text("", encoding="utf-8")
    assert helpers.load_yaml(empty_path) == {}
    monkeypatch.setenv("APP_SETTING", "environment")
    assert helpers.env_or_config(
        "APP_SETTING", {"setting": "yaml"}, "setting", "default"
    ) == "environment"


def test_validators_accept_valid_payments_and_reject_invalid_values():
    validators.require_columns(["a", "b"], ["b"])
    with pytest.raises(ValueError, match="missing required columns"):
        validators.require_columns(["a"], ["b"], source="records")

    assert validators.validate_probability("0.25") == 0.25
    for value in ("nan", "inf", -0.1, 1.1):
        with pytest.raises(ValueError, match="between 0 and 1"):
            validators.validate_probability(value)

    transaction = {
        "step": "24",
        "type": "transfer",
        "amount": "5.5",
        "oldbalanceOrg": 10,
        "newbalanceOrig": 4.5,
        "oldbalanceDest": 2,
        "newbalanceDest": 7.5,
    }
    checked = validators.validate_paysim_transaction(transaction)
    assert checked["type"] == "TRANSFER"
    assert checked["step"] == 24.0
    assert checked["amount"] == 5.5

    with pytest.raises(ValueError, match="missing required columns"):
        validators.validate_paysim_transaction({"step": 1})
    bad = {**transaction, "type": "unknown"}
    with pytest.raises(ValueError, match="Unsupported PaySim"):
        validators.validate_paysim_transaction(bad)
    for value in (-1, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="finite and non-negative"):
            validators.validate_paysim_transaction({**transaction, "amount": value})
    with pytest.raises(ValueError, match="step must be an integer"):
        validators.validate_paysim_transaction({**transaction, "step": 1.5})


def test_cleaning_chunking_and_metadata_helpers():
    frame = pd.DataFrame([[" a ", "1"], [" a ", "1"], ["b", "bad"]], columns=[" name ", "value"])
    cleaned = cleaner.clean_frame(frame, drop_duplicates=True)
    assert list(cleaned.columns) == ["name", "value"]
    assert len(cleaned) == 2
    with pytest.raises(ValueError, match="Duplicate column names"):
        cleaner.clean_frame(pd.DataFrame([[1, 2]], columns=["x", " x "]))
    numeric = cleaner.coerce_numeric(cleaned, ["value"])
    assert numeric["value"].iloc[0] == 1
    assert pd.isna(numeric["value"].iloc[1])
    with pytest.raises(ValueError, match="not found"):
        cleaner.coerce_numeric(cleaned, ["missing"])
    report = cleaner.missing_value_report(numeric)
    assert report["rows"] == 2
    assert report["missing"]["value"]["count"] == 1
    assert report["duplicate_rows"] == 0

    assert chunking.split_text("  alpha \n beta   gamma ", 8, 2) == [
        "alpha",
        "ha beta",
        "ta gamma",
    ]
    assert chunking.split_text("", 5, 0) == []
    for size, overlap in ((0, 0), (3, -1), (3, 3)):
        with pytest.raises(ValueError, match="Require chunk_size"):
            chunking.split_text("text", size, overlap)

    organization = metadata.document_metadata(
        "RBI_guidance.PDF", page=2, organization="Custom"
    )
    assert organization["organization"] == "Custom"
    assert organization["file_type"] == "pdf"
    assert organization["page"] == 2
    assert metadata.identify_organization("Basel_rules.pdf") == "Basel Committee"
    assert metadata.identify_organization("unknown.txt") == "Unknown"


def test_split_documents_preserves_metadata(monkeypatch):
    class FakeDocument:
        def __init__(self, page_content, metadata):
            self.page_content = page_content
            self.metadata = metadata

    _install_module(
        monkeypatch, "langchain_core", documents=SimpleNamespace(Document=FakeDocument)
    )
    _install_module(
        monkeypatch, "langchain_core.documents", Document=FakeDocument
    )
    source = SimpleNamespace(
        page_content="one two three four",
        metadata={"source": "policy"},
    )
    chunks = chunking.split_documents([source], chunk_size=8, chunk_overlap=0)
    assert [item.page_content for item in chunks] == ["one two", "three", "four"]
    assert [item.metadata["chunk_index"] for item in chunks] == [0, 1, 2]
    assert all(item.metadata["source"] == "policy" for item in chunks)


def test_credit_feature_engineering_paths():
    transaction = {
        "step": 24,
        "type": "cash_out",
        "amount": 10,
        "oldbalanceOrg": 0,
        "newbalanceOrig": 0,
        "oldbalanceDest": 1,
        "newbalanceDest": 11,
    }
    features = feature_engineering.build_paysim_features(
        transaction, ["hour", "day", "amount_to_origin_balance", "type_CASH_OUT"]
    )
    assert features.iloc[0].tolist() == [0.0, 1.0, 0.0, 1.0]
    with pytest.raises(ValueError, match="Unsupported model features"):
        feature_engineering.build_paysim_features(transaction, ["not_a_feature"])

    lending = feature_engineering.build_lending_features(
        {"loan_amnt": "100", "annual_inc": "bad"}, ["loan_amount", "annual_income"]
    )
    assert lending.iloc[0, 0] == 100
    assert pd.isna(lending.iloc[0, 1])

    taiwan = pd.DataFrame(
        [{column: "1" for column in feature_engineering.TAIWAN_FEATURES}]
    )
    assert feature_engineering.derive_taiwan_features(taiwan).shape == (
        1,
        len(feature_engineering.TAIWAN_FEATURES),
    )
    with pytest.raises(ValueError, match="missing columns"):
        feature_engineering.derive_taiwan_features(pd.DataFrame())

    mapped_taiwan = feature_engineering.harmonize_credit_record(
        {"LIMIT_BAL": 100, "BILL_AMT1": 40, "AGE": 30, "PAY_0": -1, "PAY_AMT1": 5},
        "taiwan",
    )
    assert mapped_taiwan["utilization"] == 0.4
    assert mapped_taiwan["delinquencies"] == 0
    mapped_lending = feature_engineering.harmonize_credit_record(
        {"revol_util": "50", "loan_amnt": 10}, "lending_club"
    )
    assert mapped_lending["utilization"] == 0.5
    with pytest.raises(ValueError, match="dataset must"):
        feature_engineering.harmonize_credit_record({}, "other")


def test_csv_loading_iteration_and_document_conversion(tmp_path):
    path = tmp_path / "records.csv"
    path.write_text(" name ,amount\nAlice,4\nBob,5\n", encoding="utf-8")
    frame = csv_loader.load_csv(path, required_columns=["name"])
    assert list(frame.columns) == ["name", "amount"]
    assert len(list(csv_loader.iter_csv(path, chunksize=1, required_columns=["name"]))) == 2
    docs = csv_loader.load_csv_documents(path, text_columns=["name"])
    assert docs[0]["page_content"] == "name: Alice"
    assert docs[0]["metadata"]["row"] == 2
    path.write_text("name,amount\nAlice,4\nBob,\n", encoding="utf-8")
    blank_docs = csv_loader.load_csv_documents(path)
    assert blank_docs[1]["page_content"] == "name: Bob"
    with pytest.raises(FileNotFoundError):
        csv_loader.load_csv(tmp_path / "missing.csv")
    with pytest.raises(ValueError, match="chunksize must be positive"):
        list(csv_loader.iter_csv(path, chunksize=0))
    with pytest.raises(ValueError, match="missing required columns"):
        csv_loader.load_csv(path, required_columns=["unknown"])
    with pytest.raises(ValueError, match="missing required columns"):
        csv_loader.load_csv_documents(path, text_columns=["unknown"])


def test_excel_and_email_loading(tmp_path, monkeypatch):
    workbook = tmp_path / "sheet.xlsx"
    workbook.touch()
    monkeypatch.setattr(
        excel_loader.pd,
        "read_excel",
        lambda *args, **kwargs: pd.DataFrame({" name ": ["A"]}),
    )
    assert excel_loader.load_excel(workbook, required_columns=["name"]).columns.tolist() == [
        "name"
    ]
    with pytest.raises(FileNotFoundError):
        excel_loader.load_excel(tmp_path / "missing.xlsx")
    with pytest.raises(ValueError, match="missing required columns"):
        excel_loader.load_excel(workbook, required_columns=["absent"])

    email_path = tmp_path / "message.eml"
    email_path.write_bytes(
        b"From: analyst@example.com\r\nSubject: Review\r\n"
        b"Date: Tue, 1 Jan 2030 00:00:00 +0000\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n\r\nPlease review."
    )
    email = email_loader.load_email(email_path)
    assert email["page_content"] == "Please review."
    assert email["metadata"]["subject"] == "Review"
    with pytest.raises(FileNotFoundError):
        email_loader.load_email(tmp_path / "missing.eml")


def test_parser_and_pdf_loader_dispatch(monkeypatch, tmp_path):
    class FakeDocument:
        def __init__(self, page_content, metadata):
            self.page_content = page_content
            self.metadata = metadata

    _install_module(monkeypatch, "langchain_core", documents=SimpleNamespace(Document=FakeDocument))
    _install_module(monkeypatch, "langchain_core.documents", Document=FakeDocument)
    text_path = tmp_path / "note.txt"
    text_path.write_text("review", encoding="utf-8")
    parsed = parser.parse_file(text_path)
    assert parsed[0].page_content == "review"
    assert parsed[0].metadata["source_file"] == "note.txt"
    with pytest.raises(FileNotFoundError):
        parser.parse_file(tmp_path / "absent.txt")
    binary_path = tmp_path / "file.bin"
    binary_path.touch()
    with pytest.raises(ValueError, match="Unsupported document extension"):
        parser.parse_file(binary_path)

    workbook_path = tmp_path / "table.xlsx"
    workbook_path.touch()
    monkeypatch.setattr(
        parser,
        "load_excel",
        lambda path: pd.DataFrame({"value": [1]}),
    )
    workbook = parser.parse_file(workbook_path)
    assert "value" in workbook[0].page_content
    email_path = tmp_path / "mail.eml"
    email_path.touch()
    monkeypatch.setattr(
        parser,
        "load_email",
        lambda path: {
            "page_content": "email text",
            "metadata": {"subject": "notice"},
        },
    )
    assert parser.parse_file(email_path)[0].metadata["subject"] == "notice"
    html_path = tmp_path / "page.html"
    html_path.write_text("<p>html text</p>", encoding="utf-8")
    class FakeSoup:
        def __init__(self, content, parser_name):
            self.content = content

        def get_text(self, separator):
            return "html text"

    _install_module(monkeypatch, "bs4", BeautifulSoup=FakeSoup)
    assert parser.parse_file(html_path)[0].page_content == "html text"
    pdf_dispatch_path = tmp_path / "dispatch.pdf"
    pdf_dispatch_path.touch()
    monkeypatch.setattr(parser, "load_pdf", lambda path: ["pdf"])
    assert parser.parse_file(pdf_dispatch_path) == ["pdf"]

    class FakePdfLoader:
        def __init__(self, path):
            self.path = path

        def load(self):
            return [FakeDocument("page", {"page": 0})]

    _install_module(
        monkeypatch,
        "langchain_community",
        document_loaders=SimpleNamespace(PyPDFLoader=FakePdfLoader),
    )
    _install_module(
        monkeypatch,
        "langchain_community.document_loaders",
        PyPDFLoader=FakePdfLoader,
    )
    pdf_path = tmp_path / "RBI.pdf"
    pdf_path.touch()
    pages = pdf_loader.load_pdf(pdf_path, metadata={"case": "C1"})
    assert pages[0].metadata["page"] == 1
    assert pages[0].metadata["organization"] == "RBI"
    assert pages[0].metadata["case"] == "C1"
    with pytest.raises(FileNotFoundError):
        pdf_loader.load_pdf(tmp_path / "missing.pdf")


def test_https_loader_validates_and_returns_text(monkeypatch):
    response = SimpleNamespace(
        headers={"content-type": "application/json"},
        text='{"ok": true}',
        raise_for_status=lambda: None,
    )
    calls = []
    monkeypatch.setattr(api_loader.requests, "get", lambda *args, **kwargs: calls.append((args, kwargs)) or response)
    result = api_loader.load_url("https://example.test/data", allowed_hosts={"EXAMPLE.TEST"})
    assert result["page_content"] == '{"ok": true}'
    assert calls[0][1]["timeout"] == 20.0
    with pytest.raises(ValueError, match="Only absolute HTTPS"):
        api_loader.load_url("http://example.test/data")
    with pytest.raises(ValueError, match="allowlist"):
        api_loader.load_url("https://other.test/data", allowed_hosts={"example.test"})
    monkeypatch.setattr(api_loader.requests, "get", lambda *args, **kwargs: SimpleNamespace(
        headers={"content-type": "application/octet-stream"},
        text="",
        raise_for_status=lambda: None,
    ))
    with pytest.raises(ValueError, match="text or JSON"):
        api_loader.load_url("https://example.test/data")


def test_ocr_uses_requested_language(monkeypatch, tmp_path):
    class FakeImage:
        def __enter__(self):
            return "image"

        def __exit__(self, *args):
            return False

    pil = types.ModuleType("PIL")
    pil.Image = SimpleNamespace(open=lambda path: FakeImage())
    _install_module(monkeypatch, "PIL", Image=pil.Image)
    _install_module(
        monkeypatch,
        "pytesseract",
        image_to_string=lambda image, lang: f"{image}:{lang}",
    )
    assert ocr.extract_image_text(tmp_path / "scan.png", language="fra") == "image:fra"


def test_embedding_cache_hits_and_batches_missing_texts(tmp_path):
    calls = []
    embed = lambda text: calls.append(text) or [float(len(text))]
    assert embedding_cache.get_or_embed("alpha", "model", embed, cache_dir=tmp_path) == [5.0]
    assert embedding_cache.get_or_embed("alpha", "model", embed, cache_dir=tmp_path) == [5.0]
    assert calls == ["alpha"]

    batch_calls = []
    batch_embed = lambda texts: batch_calls.append(texts) or [[float(len(text))] for text in texts]
    values = embedding_cache.embed_many_with_cache(
        ["alpha", "beta"], "model", batch_embed, cache_dir=tmp_path
    )
    assert values == [[5.0], [4.0]]
    assert batch_calls == [["beta"]]
    assert embedding_cache.embed_many_with_cache([], "model", batch_embed, cache_dir=tmp_path) == []
    with pytest.raises(ValueError, match="one vector per requested text"):
        embedding_cache.embed_many_with_cache(
            ["new"], "other-model", lambda texts: [], cache_dir=tmp_path
        )


def test_embedding_pipeline_merges_metadata_and_pairs_vectors(monkeypatch, tmp_path):
    document = SimpleNamespace(page_content="policy text", metadata={"organization": "Override"})
    monkeypatch.setattr(embedding_pipeline, "parse_file", lambda path: [document])
    monkeypatch.setattr(
        embedding_pipeline,
        "document_metadata",
        lambda path: {"source_file": Path(path).name, "organization": "RBI"},
    )
    split_args = []
    monkeypatch.setattr(
        embedding_pipeline,
        "split_documents",
        lambda docs, size, overlap: split_args.append((docs, size, overlap)) or docs,
    )
    chunks = embedding_pipeline.build_document_chunks(
        [tmp_path / "policy.pdf"], chunk_size=50, chunk_overlap=5
    )
    assert chunks == [document]
    assert document.metadata == {
        "source_file": "policy.pdf",
        "organization": "Override",
    }
    assert split_args[0][1:] == (50, 5)

    embed_calls = []
    monkeypatch.setattr(
        embedding_pipeline,
        "embed_texts",
        lambda texts, provider=None: embed_calls.append((texts, provider)) or [[0.1]],
    )
    records = embedding_pipeline.embed_document_chunks(chunks, provider="local")
    assert records == [{
        "page_content": "policy text",
        "metadata": document.metadata,
        "embedding": [0.1],
    }]
    assert embed_calls == [(["policy text"], "local")]
    assert embedding_pipeline.build_document_chunks([]) == []
    assert embedding_pipeline.embed_document_chunks([]) == []
    assert embedding_pipeline.run_embedding_pipeline(
        ["policy.pdf"], provider="openai"
    ) == records


def test_preprocessing_package_exports_embedding_pipeline(monkeypatch):
    document = SimpleNamespace(page_content="package-level text", metadata={})
    monkeypatch.setattr(preprocessing, "parse_file", lambda path: [document])
    monkeypatch.setattr(preprocessing, "document_metadata", lambda path: {"source_file": str(path)})
    monkeypatch.setattr(
        preprocessing,
        "split_documents",
        lambda docs, size, overlap: docs,
    )
    chunks = preprocessing.build_document_chunks(["policy.pdf"])
    assert chunks == [document]
    assert document.metadata["source_file"] == "policy.pdf"
    monkeypatch.setattr(preprocessing, "embed_texts", lambda texts, provider=None: [[0.5]])
    assert preprocessing.embed_document_chunks(chunks)[0]["embedding"] == [0.5]
    assert preprocessing.run_embedding_pipeline(["policy.pdf"])[0]["page_content"] == (
        "package-level text"
    )
    monkeypatch.setattr(preprocessing, "parse_file", lambda path: [])
    assert preprocessing.build_document_chunks(["empty.pdf"]) == []
