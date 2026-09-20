"""
Benchmark script for evaluating RecursiveChunker on TikTok Shop Policy Knowledge Base.
Runs official group benchmark queries from benchmark.json and generates ket_qua_benchmark.txt & benchmark_results_duong.json.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import yaml

from src.agent import KnowledgeBaseAgent
from src.chunking import RecursiveChunker
from src.embeddings import (
    EMBEDDING_PROVIDER_ENV,
    OPENAI_EMBEDDING_MODEL,
    OpenAIEmbedder,
    _mock_embed,
)
from src.models import Document
from src.store import EmbeddingStore

# Path configuration
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data" / "seller-warranty-policy"
CACHE_FILE = BASE_DIR / ".embedding_cache.json"
BENCHMARK_JSON = BASE_DIR / "benchmark.json"
OUTPUT_TXT = BASE_DIR / "ket_qua_benchmark.txt"
OUTPUT_JSON = BASE_DIR / "benchmark_results_duong.json"


class CachedEmbedder:
    """Wrapper that caches embeddings by text hash to save API calls and ensure fast repeats."""

    def __init__(self, base_embedder, cache_path: Path):
        self.base_embedder = base_embedder
        self.cache_path = cache_path
        self.cache: dict[str, list[float]] = {}
        self._load_cache()

    def _load_cache(self):
        if self.cache_path.exists():
            try:
                self.cache = json.loads(self.cache_path.read_text(encoding="utf-8"))
            except Exception:
                self.cache = {}

    def _save_cache(self):
        try:
            self.cache_path.write_text(json.dumps(self.cache), encoding="utf-8")
        except Exception:
            pass

    def warm_cache_batch(self, texts: list[str], batch_size: int = 100):
        """Batch-fetch embeddings from OpenAI for all uncached texts."""
        if not hasattr(self.base_embedder, "client"):
            return

        missing = []
        for t in texts:
            key = hashlib.sha256(t.encode("utf-8")).hexdigest()
            if key not in self.cache:
                missing.append((key, t))

        if not missing:
            return

        print(f"Pre-warming cache for {len(missing)} items via batch API...")
        for i in range(0, len(missing), batch_size):
            batch = missing[i : i + batch_size]
            batch_texts = [item[1] for item in batch]
            try:
                resp = self.base_embedder.client.embeddings.create(
                    model=self.base_embedder.model_name,
                    input=batch_texts,
                )
                for item, data_entry in zip(batch, resp.data):
                    self.cache[item[0]] = [float(v) for v in data_entry.embedding]
                print(f"  Processed {min(i + batch_size, len(missing))}/{len(missing)} items...")
            except Exception as e:
                print(f"  Error in batch embedding: {e}")
                break

        self._save_cache()
        print(f"Cache pre-warmed! Total cached: {len(self.cache)}")

    def __call__(self, text: str) -> list[float]:
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if key in self.cache:
            return self.cache[key]
        emb = self.base_embedder(text)
        self.cache[key] = emb
        self._save_cache()
        return emb

    @property
    def _backend_name(self):
        return getattr(self.base_embedder, "_backend_name", self.base_embedder.__class__.__name__)


def load_and_chunk_documents(data_dir: Path, chunker) -> list[Document]:
    """
    1. Read each .md file.
    2. Split frontmatter and markdown body.
    3. Chunk the body using RecursiveChunker.
    4. Return list of Document objects with metadata propagated.
    """
    documents: list[Document] = []
    md_files = sorted(data_dir.glob("*.md"))

    print(f"Loading files from: {data_dir}")
    print(f"Found {len(md_files)} markdown files:")

    for file_path in md_files:
        text = file_path.read_text(encoding="utf-8")
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                meta = yaml.safe_load(parts[1]) or {}
            except Exception:
                meta = {}
            body = parts[2].strip()
        else:
            meta = {}
            body = text.strip()

        chunks = chunker.chunk(body)
        print(f"  - {file_path.name}: {len(chunks)} chunks (raw length: {len(body):,} chars)")

        for i, chunk in enumerate(chunks):
            chunk_meta = {
                **meta,
                "doc_id": file_path.stem,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "source_file": file_path.name,
            }
            doc = Document(
                id=f"{file_path.stem}#{i}",
                content=chunk,
                metadata=chunk_meta,
            )
            documents.append(doc)

    return documents


def run_benchmark():
    load_dotenv(override=False)

    print("=" * 70)
    print("      OFFICIAL BENCHMARK EVALUATION — T020 (TIKTOK SHOP POLICY)")
    print("=" * 70)

    # 1. Load official benchmark queries from benchmark.json
    if not BENCHMARK_JSON.exists():
        raise FileNotFoundError(f"Missing {BENCHMARK_JSON}")
    benchmark_queries = json.loads(BENCHMARK_JSON.read_text(encoding="utf-8"))
    print(f"Loaded {len(benchmark_queries)} official benchmark queries from {BENCHMARK_JSON.name}")

    # 2. Initialize embedder
    provider = os.getenv(EMBEDDING_PROVIDER_ENV, "openai").strip().lower()
    openai_key = os.getenv("OPENAI_API_KEY")

    if provider == "openai" and openai_key:
        print(f"Initializing OpenAIEmbedder ({OPENAI_EMBEDDING_MODEL})...")
        base_embedder = OpenAIEmbedder(model_name=OPENAI_EMBEDDING_MODEL)
    else:
        print("Falling back to MockEmbedder...")
        base_embedder = _mock_embed

    embedder = CachedEmbedder(base_embedder, CACHE_FILE)
    print(f"Active embedding backend: {embedder._backend_name}")

    # 3. Chunking with RecursiveChunker (User's assigned strategy)
    chunker = RecursiveChunker(chunk_size=500)
    print(f"Strategy: RecursiveChunker(chunk_size=500)")

    documents = load_and_chunk_documents(DATA_DIR, chunker)
    print(f"\nTotal generated chunks: {len(documents)}")

    # Pre-warm cache in batches for high speed
    all_texts = [d.content for d in documents] + [q["query"] for q in benchmark_queries]
    embedder.warm_cache_batch(all_texts, batch_size=100)

    # 4. Store in EmbeddingStore
    store = EmbeddingStore(collection_name="tiktok_policy_bench", embedding_fn=embedder)
    print("Indexing documents into EmbeddingStore...")
    store.add_documents(documents)
    print(f"Successfully stored {store.get_collection_size()} chunks in vector store.\n")

    # 5. Execute Benchmark Queries
    lines: list[str] = []
    lines.append("================================================================================")
    lines.append("              KẾT QUẢ BENCHMARK TRUY XUẤT CHÍNH THỨC (NHÓM T020)")
    lines.append("   Sinh viên: Lâm Hải Dương (MSSV: 2A202602676)")
    lines.append("   Chủ đề: Chính sách bảo hành & quy định niêm yết bán hàng TikTok Shop")
    lines.append("   Chiến lược: RecursiveChunker (chunk_size=500)")
    lines.append(f"   Embedding Model: {embedder._backend_name} (dim: 1536)")
    lines.append(f"   Tổng số tài liệu: 5 | Tổng số chunk: {len(documents)}")
    lines.append("================================================================================\n")

    score_total = 0
    exported_results = []
    ab_q4_results = {}

    for item in benchmark_queries:
        qid = item["id"]
        query = item["query"]
        filt = item.get("metadata_filter")
        gold_doc = item["expected_doc_id"]
        gold_ans = item["gold_answer"]
        terms = item.get("retrieval_terms", [])
        evidence = item.get("evidence_quotes", [])

        print(f"--- Running Query {qid} ---")
        print(f"Query: {query}")
        if filt:
            print(f"Filter applied: {filt}")

        # Search with or without filter
        if filt:
            results = store.search_with_filter(query, metadata_filter=filt, top_k=3)
        else:
            results = store.search(query, top_k=3)

        # Evaluate scoring
        gold_in_top1 = False
        gold_in_top3 = False
        content_matches_top1 = False
        content_matches_top3 = False

        if results:
            first = results[0]
            if first["metadata"].get("doc_id") == gold_doc:
                gold_in_top1 = True
                first_text = first["content"].lower()
                if any(t.lower() in first_text for t in terms) or any(e[:30].lower() in first_text for e in evidence):
                    content_matches_top1 = True

            for r in results:
                if r["metadata"].get("doc_id") == gold_doc:
                    gold_in_top3 = True
                    r_text = r["content"].lower()
                    if any(t.lower() in r_text for t in terms) or any(e[:30].lower() in r_text for e in evidence):
                        content_matches_top3 = True

        if gold_in_top1 and content_matches_top1:
            query_score = 2
        elif gold_in_top3 and content_matches_top3:
            query_score = 1
        elif gold_in_top1:
            query_score = 1
        elif gold_in_top3:
            query_score = 1
        else:
            query_score = 0

        score_total += query_score

        # Save for JSON export
        exported_results.append({
            "query_id": qid,
            "query": query,
            "metadata_filter": filt,
            "expected_doc_id": gold_doc,
            "gold_answer": gold_ans,
            "top1_doc_id": results[0]["metadata"].get("doc_id") if results else None,
            "top1_chunk_id": results[0]["id"] if results else None,
            "top1_score": round(results[0]["score"], 4) if results else 0.0,
            "gold_in_top1": gold_in_top1,
            "gold_in_top3": gold_in_top3,
            "content_verified": content_matches_top1 or content_matches_top3,
            "score_awarded": query_score,
            "top3_chunks": [
                {
                    "rank": idx,
                    "id": r["id"],
                    "doc_id": r["metadata"].get("doc_id"),
                    "score": round(r["score"], 4),
                    "preview": r["content"][:160].replace("\n", " ") + "...",
                }
                for idx, r in enumerate(results, start=1)
            ],
        })

        # Save Q4 results for A/B comparison
        if qid == "Q4":
            ab_q4_results["with_filter"] = results

        # Format output lines
        lines.append(f"================================================================================")
        lines.append(f"CÂU HỎI {qid}: {query}")
        lines.append(f"Filter: {filt if filt else 'None'}")
        lines.append(f"Tài liệu chuẩn (Expected Doc): {gold_doc}")
        lines.append(f"Đáp án chuẩn (Gold Answer):\n  {gold_ans}")
        lines.append(f"Điểm đánh giá câu này: {query_score}/2 điểm")
        lines.append(f"\nTOP-3 CHUNKS TRUY XUẤT:")

        for rank, r in enumerate(results, start=1):
            doc_id = r["metadata"].get("doc_id", "unknown")
            chunk_idx = r["metadata"].get("chunk_index", 0)
            score = r["score"]
            content = r["content"].strip().replace("\n", " ")
            preview = content[:220] + "..." if len(content) > 220 else content
            is_gold = " [GOLD MATCH]" if doc_id == gold_doc else ""

            lines.append(f"  [{rank}] Score: {score:.4f} | ID: {r['id']} | Doc: {doc_id} | Chunk: #{chunk_idx}{is_gold}")
            lines.append(f"      Preview: {preview}")
            print(f"  [{rank}] Score: {score:.4f} | Doc: {doc_id} | Chunk: #{chunk_idx}{is_gold}")

        lines.append("")

    # Run A/B test on Q4 without filter
    print("--- Running A/B Test for Q4 without filter ---")
    q4_item = next(q for q in benchmark_queries if q["id"] == "Q4")
    q4_without_filter = store.search(q4_item["query"], top_k=3)
    ab_q4_results["without_filter"] = q4_without_filter

    lines.append("================================================================================")
    lines.append("A/B TEST ĐÁNH GIÁ METADATA FILTER TRÊN CÂU HỎI Q4")
    lines.append("Query: " + q4_item["query"])
    lines.append("--------------------------------------------------------------------------------")
    lines.append("Lần 1: CÓ metadata_filter={'audience': 'seller'}")
    for rank, r in enumerate(ab_q4_results["with_filter"], start=1):
        lines.append(f"  [{rank}] Score: {r['score']:.4f} | Doc: {r['metadata'].get('doc_id')} (Audience: {r['metadata'].get('audience')})")
        lines.append(f"      Content: {r['content'][:150].replace(chr(10), ' ')}...")

    lines.append("\nLần 2: KHÔNG CÓ filter (chạy toàn bộ corpus)")
    for rank, r in enumerate(ab_q4_results["without_filter"], start=1):
        lines.append(f"  [{rank}] Score: {r['score']:.4f} | Doc: {r['metadata'].get('doc_id')} (Audience: {r['metadata'].get('audience')})")
        lines.append(f"      Content: {r['content'][:150].replace(chr(10), ' ')}...")

    lines.append("\nNhận xét A/B:")
    lines.append("- Khi CÓ filter {'audience': 'seller'}, hệ thống giới hạn không gian tìm kiếm trong tập tài liệu quy định cho Người Bán, đảm bảo không bị lẫn tài liệu chung.")
    lines.append("- Khi KHÔNG CÓ filter, tài liệu quy chế chung đồ sộ (audience: both) có thể chen chân vào kết quả do chứa nhiều từ khóa bảo hành.")
    lines.append("================================================================================\n")

    lines.append(f"TỔNG KẾT ĐIỂM TRUY XUẤT: {score_total}/10 điểm")

    output_text = "\n".join(lines)
    OUTPUT_TXT.write_text(output_text, encoding="utf-8")
    print(f"\nBenchmark completed! Result saved to: {OUTPUT_TXT}")
    print(f"Total Retrieval Quality Score: {score_total}/10")

    # Export JSON
    json_data = {
        "student_name": "Lâm Hải Dương",
        "student_id": "2A202602676",
        "team_id": "T020",
        "strategy": "RecursiveChunker",
        "parameters": {"chunk_size": 500, "separators": ["\n\n", "\n", ". ", " ", ""]},
        "embedding_model": embedder._backend_name,
        "embedding_dim": 1536,
        "total_documents": 5,
        "total_chunks": len(documents),
        "total_score": f"{score_total}/10",
        "results": exported_results,
        "ab_test_q4": {
            "query": q4_item["query"],
            "with_filter": [
                {"rank": i, "score": r["score"], "doc_id": r["metadata"].get("doc_id")}
                for i, r in enumerate(ab_q4_results["with_filter"], start=1)
            ],
            "without_filter": [
                {"rank": i, "score": r["score"], "doc_id": r["metadata"].get("doc_id")}
                for i, r in enumerate(ab_q4_results["without_filter"], start=1)
            ],
        },
    }
    OUTPUT_JSON.write_text(json.dumps(json_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Summary JSON saved to: {OUTPUT_JSON}")


if __name__ == "__main__":
    run_benchmark()
