from __future__ import annotations

from typing import Any, Callable

from .chunking import _dot
from .embeddings import _mock_embed
from .models import Document


class EmbeddingStore:
    """
    A vector store for text chunks.

    Tries to use ChromaDB if available; falls back to an in-memory store.
    The embedding_fn parameter allows injection of mock embeddings for tests.
    """

    def __init__(
        self,
        collection_name: str = "documents",
        embedding_fn: Callable[[str], list[float]] | None = None,
    ) -> None:
        self._embedding_fn = embedding_fn or _mock_embed
        self._collection_name = collection_name
        self._use_chroma = False
        self._store: list[dict[str, Any]] = []
        self._collection = None
        self._next_index = 0

        try:
            import os
            import chromadb

            persist_dir = os.getenv("CHROMA_PERSIST_DIR")
            if persist_dir:
                client = chromadb.PersistentClient(path=persist_dir)
            else:
                client = chromadb.Client()

            self._collection = client.get_or_create_collection(
                name=self._collection_name,
                embedding_function=None,
            )
            self._use_chroma = True
        except Exception:
            self._use_chroma = False
            self._collection = None

    def _make_record(self, doc: Document) -> dict[str, Any]:
        return {
            "id": doc.id,
            "content": doc.content,
            "metadata": dict(doc.metadata) if doc.metadata else {},
            "embedding": self._embedding_fn(doc.content),
        }

    def _search_records(self, query: str, records: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        if not records or top_k <= 0:
            return []
        query_emb = self._embedding_fn(query)
        scored = []
        for r in records:
            score = _dot(query_emb, r["embedding"])
            scored.append({
                "id": r["id"],
                "content": r["content"],
                "metadata": r["metadata"],
                "score": score,
            })
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def add_documents(self, docs: list[Document]) -> None:
        """
        Embed each document's content and store it.

        For ChromaDB: use collection.add(ids=[...], documents=[...], embeddings=[...])
        For in-memory: append dicts to self._store
        """
        new_records = [self._make_record(doc) for doc in docs]
        self._store.extend(new_records)

        if self._use_chroma and self._collection is not None:
            try:
                ids = [r["id"] for r in new_records]
                documents = [r["content"] for r in new_records]
                embeddings = [r["embedding"] for r in new_records]
                metadatas = [r["metadata"] if r["metadata"] else None for r in new_records]
                self._collection.add(
                    ids=ids,
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=metadatas,
                )
            except Exception:
                pass

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Find the top_k most similar documents to query.

        For in-memory: compute dot product of query embedding vs all stored embeddings.
        """
        return self._search_records(query, self._store, top_k)

    def get_collection_size(self) -> int:
        """Return the total number of stored chunks."""
        return len(self._store)

    def search_with_filter(self, query: str, top_k: int = 3, metadata_filter: dict = None) -> list[dict]:
        """
        Search with optional metadata pre-filtering.

        First filter stored chunks by metadata_filter, then run similarity search.
        """
        if not metadata_filter:
            return self.search(query, top_k)

        filtered = [
            r for r in self._store
            if all(r["metadata"].get(k) == v for k, v in metadata_filter.items())
        ]
        return self._search_records(query, filtered, top_k)

    def delete_document(self, doc_id: str) -> bool:
        """
        Remove all chunks belonging to a document.

        Returns True if any chunks were removed, False otherwise.
        """
        initial_len = len(self._store)
        self._store = [
            r for r in self._store
            if r["id"] != doc_id and r.get("metadata", {}).get("doc_id") != doc_id
        ]
        removed = len(self._store) < initial_len
        if self._use_chroma and self._collection is not None:
            try:
                self._collection.delete(ids=[doc_id])
            except Exception:
                pass
        return removed
