from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from scripts.rag.embedding.config import (
    DEFAULT_EMBEDDED_CHUNKS_PATH,
    EMBEDDING_DIM,
    MILVUS_COLLECTION,
    MILVUS_URI,
)
from scripts.rag.embedding.io import read_jsonl


try:
    from pymilvus import DataType, MilvusClient
except ImportError as exc:  # pragma: no cover
    raise ImportError("pymilvus is required to load embedded chunks into Milvus.") from exc


VARCHAR_MAX = {
    "chunk_id": 512,
    "content": 16_384,
    "document_id": 512,
    "document_type": 64,
    "event_type": 64,
    "section": 128,
    "section_title": 256,
    "title": 512,
    "source_path": 1024,
    "drug_name": 512,
    "normalized_drug_name": 512,
    "rxnorm_rxcui": 128,
    "classification": 128,
    "lot": 1024,
    "recall_number": 128,
    "embedding_model": 128,
    "content_hash": 128,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Load embedded evidence chunks into Milvus.")
    parser.add_argument("--input", type=Path, default=DEFAULT_EMBEDDED_CHUNKS_PATH)
    parser.add_argument("--uri", default=MILVUS_URI)
    parser.add_argument("--collection", default=MILVUS_COLLECTION)
    parser.add_argument("--embedding-dim", type=int, default=EMBEDDING_DIM)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--drop-existing", action="store_true")
    return parser


def ensure_collection(
    client: MilvusClient,
    *,
    collection_name: str,
    embedding_dim: int,
    drop_existing: bool,
) -> None:
    if client.has_collection(collection_name):
        if not drop_existing:
            return
        client.drop_collection(collection_name)

    schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=False)
    schema.add_field("chunk_id", DataType.VARCHAR, is_primary=True, max_length=VARCHAR_MAX["chunk_id"])
    schema.add_field("embedding", DataType.FLOAT_VECTOR, dim=embedding_dim)
    schema.add_field("content", DataType.VARCHAR, max_length=VARCHAR_MAX["content"])
    schema.add_field("document_id", DataType.VARCHAR, max_length=VARCHAR_MAX["document_id"])
    schema.add_field("document_type", DataType.VARCHAR, max_length=VARCHAR_MAX["document_type"])
    schema.add_field("event_type", DataType.VARCHAR, max_length=VARCHAR_MAX["event_type"])
    schema.add_field("event_types_json", DataType.JSON)
    schema.add_field("section", DataType.VARCHAR, max_length=VARCHAR_MAX["section"])
    schema.add_field("section_title", DataType.VARCHAR, max_length=VARCHAR_MAX["section_title"])
    schema.add_field("title", DataType.VARCHAR, max_length=VARCHAR_MAX["title"])
    schema.add_field("source_path", DataType.VARCHAR, max_length=VARCHAR_MAX["source_path"])
    schema.add_field("drug_name", DataType.VARCHAR, max_length=VARCHAR_MAX["drug_name"])
    schema.add_field("normalized_drug_name", DataType.VARCHAR, max_length=VARCHAR_MAX["normalized_drug_name"])
    schema.add_field("rxnorm_rxcui", DataType.VARCHAR, max_length=VARCHAR_MAX["rxnorm_rxcui"])
    schema.add_field("classification", DataType.VARCHAR, max_length=VARCHAR_MAX["classification"])
    schema.add_field("ndc_json", DataType.JSON)
    schema.add_field("lot", DataType.VARCHAR, max_length=VARCHAR_MAX["lot"])
    schema.add_field("recall_number", DataType.VARCHAR, max_length=VARCHAR_MAX["recall_number"])
    schema.add_field("metadata_json", DataType.JSON)
    schema.add_field("embedding_model", DataType.VARCHAR, max_length=VARCHAR_MAX["embedding_model"])
    schema.add_field("content_hash", DataType.VARCHAR, max_length=VARCHAR_MAX["content_hash"])

    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="embedding",
        index_type="IVF_FLAT",
        metric_type="COSINE",
        params={"nlist": 128},
    )

    client.create_collection(collection_name=collection_name, schema=schema, index_params=index_params)


def truncate(value: Any, max_length: int) -> str:
    if value is None:
        return ""
    text = str(value)
    return text[:max_length]


def as_json_array(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def to_milvus_row(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "chunk_id": truncate(record["chunk_id"], VARCHAR_MAX["chunk_id"]),
        "embedding": record["embedding"],
        "content": truncate(record["content"], VARCHAR_MAX["content"]),
        "document_id": truncate(record["document_id"], VARCHAR_MAX["document_id"]),
        "document_type": truncate(record["document_type"], VARCHAR_MAX["document_type"]),
        "event_type": truncate(record["event_type"], VARCHAR_MAX["event_type"]),
        "event_types_json": as_json_array(record.get("event_types")),
        "section": truncate(record["section"], VARCHAR_MAX["section"]),
        "section_title": truncate(record["section_title"], VARCHAR_MAX["section_title"]),
        "title": truncate(record["title"], VARCHAR_MAX["title"]),
        "source_path": truncate(record["source_path"], VARCHAR_MAX["source_path"]),
        "drug_name": truncate(record.get("drug_name"), VARCHAR_MAX["drug_name"]),
        "normalized_drug_name": truncate(record.get("normalized_drug_name"), VARCHAR_MAX["normalized_drug_name"]),
        "rxnorm_rxcui": truncate(record.get("rxnorm_rxcui"), VARCHAR_MAX["rxnorm_rxcui"]),
        "classification": truncate(record.get("classification"), VARCHAR_MAX["classification"]),
        "ndc_json": as_json_array(record.get("ndc")),
        "lot": truncate(record.get("lot"), VARCHAR_MAX["lot"]),
        "recall_number": truncate(record.get("recall_number"), VARCHAR_MAX["recall_number"]),
        "metadata_json": record.get("metadata", {}),
        "embedding_model": truncate(record["embedding_model"], VARCHAR_MAX["embedding_model"]),
        "content_hash": truncate(record["content_hash"], VARCHAR_MAX["content_hash"]),
    }


def batched(items: list[dict[str, Any]], batch_size: int) -> list[list[dict[str, Any]]]:
    return [items[index : index + batch_size] for index in range(0, len(items), batch_size)]


def load_milvus(
    input_path: Path,
    *,
    uri: str,
    collection_name: str,
    embedding_dim: int,
    batch_size: int,
    drop_existing: bool,
) -> int:
    records = read_jsonl(input_path)
    client = MilvusClient(uri=uri)
    ensure_collection(
        client,
        collection_name=collection_name,
        embedding_dim=embedding_dim,
        drop_existing=drop_existing,
    )

    total = 0
    for batch in batched(records, batch_size):
        rows = [to_milvus_row(record) for record in batch]
        client.upsert(collection_name=collection_name, data=rows)
        total += len(rows)
        print(f"[MILVUS] upserted={total}/{len(records)}", flush=True)

    client.flush(collection_name)
    client.load_collection(collection_name)
    return total


def main() -> None:
    args = build_parser().parse_args()
    count = load_milvus(
        args.input,
        uri=args.uri,
        collection_name=args.collection,
        embedding_dim=args.embedding_dim,
        batch_size=args.batch_size,
        drop_existing=args.drop_existing,
    )

    print("[SUMMARY]")
    print(f"input={args.input}")
    print(f"uri={args.uri}")
    print(f"collection={args.collection}")
    print(f"loaded_chunks={count}")


if __name__ == "__main__":
    main()
