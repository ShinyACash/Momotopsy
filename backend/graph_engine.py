from __future__ import annotations

import hashlib
import struct
from typing import Any

import networkx as nx
import numpy as np
from numpy.typing import NDArray
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

_MODEL_NAME: str = "all-MiniLM-L6-v2"
_SIMILARITY_THRESHOLD: float = 0.65


class LegalGraphBuilder:
    def __init__(self) -> None:
        self.model: SentenceTransformer = SentenceTransformer(_MODEL_NAME)

    def build_graph(self, clauses: list[str]) -> dict[str, Any]:
        if not clauses:
            return nx.node_link_data(nx.Graph())

        embeddings: NDArray[np.float32] = self.model.encode(
            clauses, convert_to_numpy=True, show_progress_bar=False
        )

        graph = nx.Graph()
        for idx, clause in enumerate(clauses):
            node_id = f"clause_{idx}"
            risk = self._mock_risk_score(clause)
            graph.add_node(
                node_id,
                text=clause,
                risk_score=round(risk, 4),
            )

        sim_matrix: NDArray[np.float64] = cosine_similarity(embeddings)
        n = len(clauses)
        for i in range(n):
            for j in range(i + 1, n):
                score = float(sim_matrix[i, j])
                if score > _SIMILARITY_THRESHOLD:
                    graph.add_edge(
                        f"clause_{i}",
                        f"clause_{j}",
                        weight=round(score, 4),
                    )

        return nx.node_link_data(graph)

    @staticmethod
    def _mock_risk_score(clause: str) -> float:
        digest = hashlib.sha256(clause.encode()).digest()
        value = struct.unpack("!I", digest[:4])[0]
        return value / 0xFFFFFFFF
