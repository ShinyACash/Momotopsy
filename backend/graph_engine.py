from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import joblib
import networkx as nx
import numpy as np
from numpy.typing import NDArray
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from llm_fixer import ClauseFixer

_MODEL_NAME: str = "all-mpnet-base-v2"
_CLF_PATH: str = str(Path(__file__).with_name("momotopsy_risk_model.pkl"))
_SIMILARITY_THRESHOLD: float = 0.65
_RISK_THRESHOLD: float = 0.15


class LegalGraphBuilder:
    def __init__(self) -> None:
        self.encoder: SentenceTransformer = SentenceTransformer(_MODEL_NAME)
        self.clf = joblib.load(_CLF_PATH)
        self.fixer: ClauseFixer = ClauseFixer()

    async def build_graph(self, clauses: list[str]) -> dict[str, Any]:
        if not clauses:
            return nx.node_link_data(nx.Graph())

        embeddings: NDArray[np.float32] = self.encoder.encode(
            clauses, convert_to_numpy=True, show_progress_bar=False
        )

        # Risk scores from trained classifier 
        probas = self.clf.predict_proba(embeddings)
        risk_scores: NDArray[np.float64] = probas[:, 1]

        # Build nodes
        graph = nx.Graph()
        
        avg_risk = float(np.mean(risk_scores)) if len(risk_scores) > 0 else 0.0
        graph.graph["document_risk_score"] = round(avg_risk, 4)
        
        llm_tasks: list = []
        predatory_indices: list[int] = []

        for idx, (clause, risk) in enumerate(zip(clauses, risk_scores)):
            node_id = f"clause_{idx}"
            risk_val = float(risk)
            label = "Predatory" if risk_val >= _RISK_THRESHOLD else "Safe"

            graph.add_node(
                node_id,
                text=clause,
                risk_score=round(risk_val, 4),
                label=label,
                reason_flagged=None,
                key_issues=[],
                improved_clause=None,
            )

            if label == "Predatory":
                llm_tasks.append(self.fixer.analyze_clause(clause))
                predatory_indices.append(idx)

        # LLM analysis — all predatory clauses in parallel 
        if llm_tasks:
            results = await asyncio.gather(*llm_tasks)
            for idx, result in zip(predatory_indices, results):
                node_id = f"clause_{idx}"
                graph.nodes[node_id]["reason_flagged"] = result["reason_flagged"]
                graph.nodes[node_id]["key_issues"] = result["key_issues"]
                graph.nodes[node_id]["improved_clause"] = result["improved_clause"]

        # Similarity edges
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
