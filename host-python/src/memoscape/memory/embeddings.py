from __future__ import annotations
import hashlib, math
from abc import ABC, abstractmethod
class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: str) -> list[float]: ...
class MockEmbeddingProvider(EmbeddingProvider):
    DIM = 32
    def embed(self, text: str) -> list[float]:
        vec = [0.0]*self.DIM
        for tok in text.lower().split():
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            vec[h % self.DIM] += 1.0
        norm = math.sqrt(sum(v*v for v in vec)) or 1.0
        return [v/norm for v in vec]
def cosine(a, b): return sum(x*y for x,y in zip(a,b))
