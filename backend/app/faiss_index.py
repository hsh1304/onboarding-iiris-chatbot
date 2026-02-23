import faiss
import numpy as np
from typing import List, Tuple


class FaissIndex:
    def __init__(self, dim: int):
        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)
        self.metadatas = []

    def add(self, vectors: List[List[float]], metadatas: List[dict]):
        arr = np.array(vectors).astype("float32")

        # normalize for cosine similarity
        faiss.normalize_L2(arr)

        self.index.add(arr)
        self.metadatas.extend(metadatas)

    def search(
        self, vector: List[float], top_k: int = 4
    ) -> List[Tuple[dict, float]]:
        v = np.array([vector]).astype("float32")

        # normalize for cosine similarity
        faiss.normalize_L2(v)

        distances, indices = self.index.search(v, top_k)

        results = []
        for score, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            results.append((self.metadatas[idx], float(score)))

        return results

    def size(self):
        return self.index.ntotal
