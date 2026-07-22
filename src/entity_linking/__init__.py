"""
Entity Linking Module
Retrieval (FAISS) + Reranking (Cross-Encoder) for ICD-10 and RxNorm mapping.
"""
import json
import os
import numpy as np
from typing import List, Dict, Optional, Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Optional imports
try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

try:
    from sentence_transformers import CrossEncoder
    HAS_CROSS_ENCODER = True
except ImportError:
    HAS_CROSS_ENCODER = False


class EntityLinker:
    """Entity linking using Retrieval + Cross-Encoder reranking."""

    def __init__(
        self,
        embedding_model: str = "BAAI/bge-m3",
        cross_encoder_model: str = "BAAI/bge-reranker-v2-m3",
        index_dir: str = None,
    ):
        self.embedding_model_name = embedding_model
        self.cross_encoder_model_name = cross_encoder_model
        self.index_dir = index_dir or os.path.join(PROJECT_ROOT, "indices")
        self.embedder = None
        self.cross_encoder = None

        # Indexes
        self.icd_index = None
        self.icd_metadata = None
        self.rxnorm_index = None
        self.rxnorm_metadata = None

    def load(self):
        """Load embedding model, cross-encoder, and FAISS indexes."""
        print("=== Loading Entity Linking Models ===")

        if HAS_SENTENCE_TRANSFORMERS:
            try:
                self.embedder = SentenceTransformer(self.embedding_model_name)
                print(f"  Embedding model loaded: {self.embedding_model_name}")
            except Exception as e:
                print(f"  Failed to load embedding model: {e}")

        if HAS_CROSS_ENCODER:
            try:
                self.cross_encoder = CrossEncoder(self.cross_encoder_model_name)
                print(f"  Cross-encoder loaded: {self.cross_encoder_model_name}")
            except Exception as e:
                print(f"  Failed to load cross-encoder: {e}")

        self._load_indexes()

    def _load_indexes(self):
        """Load FAISS indexes and metadata."""
        if not HAS_FAISS:
            print("  FAISS not available, using fallback linking")
            return

        # ICD-10 index
        icd_index_path = os.path.join(self.index_dir, "icd10.faiss")
        icd_meta_path = os.path.join(self.index_dir, "icd10_metadata.json")
        if os.path.exists(icd_index_path) and os.path.exists(icd_meta_path):
            self.icd_index = faiss.read_index(icd_index_path)
            with open(icd_meta_path, "r", encoding="utf-8") as f:
                self.icd_metadata = json.load(f)
            print(f"  ICD-10 index loaded: {self.icd_index.ntotal} entries")

        # RxNorm index
        rxnorm_index_path = os.path.join(self.index_dir, "rxnorm.faiss")
        rxnorm_meta_path = os.path.join(self.index_dir, "rxnorm_metadata.json")
        if os.path.exists(rxnorm_index_path) and os.path.exists(rxnorm_meta_path):
            self.rxnorm_index = faiss.read_index(rxnorm_index_path)
            with open(rxnorm_meta_path, "r", encoding="utf-8") as f:
                self.rxnorm_metadata = json.load(f)
            print(f"  RxNorm index loaded: {self.rxnorm_index.ntotal} entries")

    def link_entity(
        self,
        entity_text: str,
        entity_type: str,
        context: str = "",
        top_k: int = 5,
    ) -> List[str]:
        """
        Link an entity to ICD-10 or RxNorm code.
        Returns list of candidate codes.
        """
        if entity_type == "THUỐC":
            return self._link_drug(entity_text, context, top_k)
        elif entity_type == "CHẨN_ĐOÁN":
            return self._link_disease(entity_text, context, top_k)
        return []

    def _link_drug(self, entity_text: str, context: str, top_k: int) -> List[str]:
        """Link drug entity to RxNorm codes."""
        if self.rxnorm_index is None or self.embedder is None:
            return self._fallback_drug_link(entity_text)

        # Embed query
        query_embedding = self.embedder.encode([entity_text], normalize_embeddings=True)
        query_embedding = np.array(query_embedding, dtype=np.float32)

        # Search FAISS
        k = min(top_k * 3, self.rxnorm_index.ntotal)
        scores, indices = self.rxnorm_index.search(query_embedding, k)

        candidates = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.rxnorm_metadata):
                continue
            meta = self.rxnorm_metadata[idx]
            candidates.append({
                "code": meta.get("rxcui", ""),
                "name": meta.get("name_vi", meta.get("name_en", "")),
                "score": float(score),
                "generic": meta.get("generic", ""),
            })

        if not candidates:
            return self._fallback_drug_link(entity_text)

        # Rerank with cross-encoder
        if self.cross_encoder:
            candidates = self._rerank_with_cross_encoder(entity_text, candidates, top_k)

        return [c["code"] for c in candidates[:top_k] if c["code"]]

    def _link_disease(self, entity_text: str, context: str, top_k: int) -> List[str]:
        """Link disease entity to ICD-10 codes."""
        if self.icd_index is None or self.embedder is None:
            return self._fallback_disease_link(entity_text)

        # Embed query
        query_embedding = self.embedder.encode([entity_text], normalize_embeddings=True)
        query_embedding = np.array(query_embedding, dtype=np.float32)

        # Search FAISS
        k = min(top_k * 3, self.icd_index.ntotal)
        scores, indices = self.icd_index.search(query_embedding, k)

        candidates = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.icd_metadata):
                continue
            meta = self.icd_metadata[idx]
            candidates.append({
                "code": meta.get("code", ""),
                "name": meta.get("name_vi", meta.get("name_en", "")),
                "score": float(score),
            })

        if not candidates:
            return self._fallback_disease_link(entity_text)

        # Rerank with cross-encoder
        if self.cross_encoder:
            candidates = self._rerank_with_cross_encoder(entity_text, candidates, top_k)

        return [c["code"] for c in candidates[:top_k] if c["code"]]

    def _rerank_with_cross_encoder(
        self,
        entity_text: str,
        candidates: List[Dict],
        top_k: int,
    ) -> List[Dict]:
        """Rerank candidates using cross-encoder."""
        if not candidates:
            return candidates

        pairs = [(entity_text, c.get("name", "")) for c in candidates]
        try:
            scores = self.cross_encoder.predict(pairs)
            for i, score in enumerate(scores):
                candidates[i]["rerank_score"] = float(score)
            candidates.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        except Exception as e:
            print(f"  Cross-encoder rerank failed: {e}")
            candidates.sort(key=lambda x: x.get("score", 0), reverse=True)

        return candidates[:top_k]

    def _fallback_drug_link(self, entity_text: str) -> List[str]:
        """Fallback: exact match from database."""
        db_path = os.path.join(PROJECT_ROOT, "databases", "rxnorm", "rxnorm_database.json")
        if not os.path.exists(db_path):
            return []

        with open(db_path, "r", encoding="utf-8") as f:
            db = json.load(f)

        entity_lower = entity_text.lower()
        matches = []
        for rxcui, info in db.get("drugs", {}).items():
            search_text = info.get("search_text", "")
            name_vi = info.get("name_vi", "").lower()
            name_en = info.get("name_en", "").lower()
            generic = info.get("generic", "").lower()

            # Exact match
            if entity_lower == name_vi or entity_lower == name_en:
                matches.insert(0, rxcui)
                continue

            # Partial match
            if entity_lower in search_text or entity_lower in name_vi or entity_lower in name_en:
                matches.append(rxcui)
            elif generic and entity_lower in generic:
                matches.append(rxcui)

        # Deduplicate preserving order
        seen = set()
        unique = []
        for m in matches:
            if m not in seen:
                seen.add(m)
                unique.append(m)

        return unique[:5]

    def _fallback_disease_link(self, entity_text: str) -> List[str]:
        """Fallback: exact match from database."""
        db_path = os.path.join(PROJECT_ROOT, "databases", "icd10_vn", "icd10_database.json")
        if not os.path.exists(db_path):
            return []

        with open(db_path, "r", encoding="utf-8") as f:
            db = json.load(f)

        entity_lower = entity_text.lower()
        matches = []
        for code, info in db.get("codes", {}).items():
            search_text = info.get("search_text", "")
            name_vi = info.get("name_vi", "").lower()
            name_en = info.get("name_en", "").lower()

            if entity_lower == name_vi or entity_lower == name_en:
                matches.insert(0, code)
                continue

            if entity_lower in search_text or entity_lower in name_vi:
                matches.append(code)
            elif entity_lower in name_en:
                matches.append(code)

        seen = set()
        unique = []
        for m in matches:
            if m not in seen:
                seen.add(m)
                unique.append(m)

        return unique[:5]

    def link_entities(
        self,
        entities: List[Dict],
        full_text: str = "",
        top_k: int = 5,
    ) -> List[Dict]:
        """Link all entities that need candidates."""
        for ent in entities:
            etype = ent.get("type", "")
            if etype in ["THUỐC", "CHẨN_ĐOÁN"]:
                ent["candidates"] = self.link_entity(
                    ent["text"], etype, full_text, top_k
                )
            else:
                ent["candidates"] = []
        return entities
