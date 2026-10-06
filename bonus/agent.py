"""Minimal hybrid-memory agent for the Lab 19 bonus challenge."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient, models
from rank_bm25 import BM25Okapi

from app.embeddings import Embedder

COLLECTION = "bonus_episodic_memory"


@dataclass
class Memory:
    point_id: int
    user_id: str
    text: str


class HybridMemoryAgent:
    """Combine per-user episodic retrieval with Feast profile features."""

    def __init__(
        self,
        client: QdrantClient | None = None,
        feature_store: Any | None = None,
        top_k: int = 3,
    ) -> None:
        self.client = client or QdrantClient(":memory:")
        self.embedder = Embedder()
        self.top_k = top_k
        self.memories: list[Memory] = []
        self._next_id = 0
        self.feature_store = feature_store if feature_store is not None else self._load_feast()

        existing = {c.name for c in self.client.get_collections().collections}
        if COLLECTION not in existing:
            self.client.create_collection(
                collection_name=COLLECTION,
                vectors_config=models.VectorParams(
                    size=self.embedder.dim, distance=models.Distance.COSINE
                ),
            )

    @staticmethod
    def _load_feast() -> Any | None:
        """Use the NB4 store when available; remain usable before NB4."""
        repo = Path(__file__).resolve().parents[1] / "app" / "feast_repo"
        if not (repo / "registry.db").exists():
            return None
        try:
            from feast import FeatureStore

            return FeatureStore(repo_path=str(repo))
        except Exception:
            return None

    @staticmethod
    def _chunks(text: str, max_chars: int = 450, overlap: int = 80) -> list[str]:
        """Sentence-aware chunks with a small overlap for boundary context."""
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]
        chunks: list[str] = []
        current = ""
        for sentence in sentences:
            candidate = f"{current} {sentence}".strip()
            if current and len(candidate) > max_chars:
                chunks.append(current)
                current = f"{current[-overlap:]} {sentence}".strip()
            else:
                current = candidate
        if current:
            chunks.append(current)
        return chunks or [text.strip()]

    def remember(self, text: str, user_id: str = "u_001") -> None:
        """Chunk, embed and store a new episodic memory for one user."""
        if not text.strip():
            raise ValueError("memory text must not be empty")
        chunks = self._chunks(text)
        vectors = list(self.embedder.embed(chunks))
        points = []
        for chunk, vector in zip(chunks, vectors):
            point_id = self._next_id
            self._next_id += 1
            self.memories.append(Memory(point_id, user_id, chunk))
            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=vector.tolist(),
                    payload={"user_id": user_id, "text": chunk, "created_at": time.time()},
                )
            )
        self.client.upsert(collection_name=COLLECTION, points=points)

    @staticmethod
    def _tokens(text: str) -> list[str]:
        # Keep technical tokens such as kubernetes and oauth intact. A production
        # version would normalize Telex and use underthesea/pyvi for Vietnamese.
        return re.findall(r"[\w/-]+", text.lower(), flags=re.UNICODE)

    def _hybrid_search(self, query: str, user_id: str) -> list[str]:
        owned = [m for m in self.memories if m.user_id == user_id]
        if not owned:
            return []
        depth = min(max(self.top_k * 5, 10), len(owned))

        bm25 = BM25Okapi([self._tokens(m.text) for m in owned])
        scores = bm25.get_scores(self._tokens(query))
        lexical = [owned[i].point_id for i in sorted(range(len(owned)), key=lambda i: -scores[i])[:depth]]

        user_filter = models.Filter(must=[models.FieldCondition(
            key="user_id", match=models.MatchValue(value=user_id)
        )])
        vector = next(self.embedder.embed([query])).tolist()
        dense = self.client.query_points(
            collection_name=COLLECTION, query=vector, query_filter=user_filter, limit=depth
        ).points

        rrf: dict[int, float] = {}
        for ids in (lexical, [int(p.id) for p in dense]):
            for rank, point_id in enumerate(ids, start=1):
                rrf[point_id] = rrf.get(point_id, 0.0) + 1.0 / (60 + rank)
        by_id = {m.point_id: m.text for m in owned}
        ranked = sorted(rrf, key=rrf.get, reverse=True)[: self.top_k]
        return [by_id[i] for i in ranked]

    def _profile(self, user_id: str) -> dict[str, Any]:
        if self.feature_store is None:
            return {}
        try:
            raw = self.feature_store.get_online_features(
                features=[
                    "user_profile_features:reading_speed_wpm",
                    "user_profile_features:preferred_language",
                    "user_profile_features:topic_affinity",
                    "query_velocity_features:queries_last_hour",
                    "query_velocity_features:distinct_topics_24h",
                ],
                entity_rows=[{"user_id": user_id}],
            ).to_dict()
            return {k: (v[0] if isinstance(v, list) and v else v) for k, v in raw.items()}
        except Exception as exc:
            return {"profile_error": str(exc)}

    def recall(self, query: str, user_id: str = "u_001") -> str:
        """Return an LLM-ready context assembled from profile and memories."""
        profile = self._profile(user_id)
        memories = self._hybrid_search(query, user_id)
        profile_line = (
            f"language={profile.get('preferred_language', 'unknown')}, "
            f"topic_affinity={profile.get('topic_affinity', 'unknown')}, "
            f"reading_speed={profile.get('reading_speed_wpm', 'unknown')} wpm"
        )
        activity_line = (
            f"queries_last_hour={profile.get('queries_last_hour', 'unknown')}, "
            f"distinct_topics_24h={profile.get('distinct_topics_24h', 'unknown')}"
        )
        memory_lines = "\n".join(f"  {i}. {m}" for i, m in enumerate(memories, 1))
        return (
            f"User: {user_id}\nQuery: {query}\nStable profile: {profile_line}\n"
            f"Recent activity: {activity_line}\nTop episodic memories:\n"
            f"{memory_lines or '  (no memory found)'}"
        )
