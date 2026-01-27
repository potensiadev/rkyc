"""
Embedding Service
OpenAI text-embedding-3-large based vector generation

v1.1 변경사항:
- Thread-safe singleton 패턴 적용 (P0-001)
- 임베딩 차원 검증 추가 (P0-002)
- 배치 실패 상세 로깅 추가
"""

import logging
import threading
import time
from typing import Optional

import openai

from app.core.config import settings

logger = logging.getLogger(__name__)

# Thread-safe singleton lock (P0-001 fix)
_embedding_service_lock = threading.Lock()


class EmbeddingError(Exception):
    """Raised when embedding generation fails"""
    pass


class EmbeddingService:
    """
    OpenAI text-embedding-3-large based vector generation service.

    Uses:
    - Signal summary text vectorization
    - Insight memory vectorization
    - Similar case search support

    Model: text-embedding-3-large
    Dimension: 2000 (pgvector 최대 지원 차원, API에서 축소)
    """

    MODEL = "text-embedding-3-large"
    DIMENSION = 2000  # pgvector max limit, reduced from 3072
    MAX_BATCH_SIZE = 100  # OpenAI batch limit
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0

    def __init__(self):
        """Initialize embedding service with OpenAI API key"""
        self.client = None
        if settings.OPENAI_API_KEY:
            self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            logger.warning("OpenAI API key not configured - embedding service disabled")

    @property
    def is_available(self) -> bool:
        """Check if embedding service is available"""
        return self.client is not None

    def embed_text(self, text: str) -> Optional[list[float]]:
        """
        Generate embedding vector for a single text.

        Args:
            text: Text to embed (max ~8000 tokens)

        Returns:
            list[float]: Embedding vector of dimension 1536, or None if failed

        Raises:
            EmbeddingError: When embedding generation fails after retries
        """
        if not self.is_available:
            logger.warning("Embedding service not available")
            return None

        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return None

        # Truncate text if too long (rough estimate: ~4 chars per token)
        max_chars = 32000  # ~8000 tokens
        if len(text) > max_chars:
            text = text[:max_chars]
            logger.warning(f"Text truncated to {max_chars} chars for embedding")

        for attempt in range(self.MAX_RETRIES):
            try:
                start_time = time.time()

                response = self.client.embeddings.create(
                    model=self.MODEL,
                    input=text,
                    dimensions=self.DIMENSION,  # Reduce from 3072 to 2000 for pgvector
                )

                embedding = response.data[0].embedding
                elapsed_ms = int((time.time() - start_time) * 1000)

                logger.debug(f"Generated embedding in {elapsed_ms}ms")
                return embedding

            except openai.RateLimitError as e:
                logger.warning(f"Rate limit hit (attempt {attempt + 1}): {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
                else:
                    raise EmbeddingError(f"Rate limit exceeded after {self.MAX_RETRIES} attempts")

            except openai.APIError as e:
                logger.error(f"OpenAI API error (attempt {attempt + 1}): {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                else:
                    raise EmbeddingError(f"OpenAI API error: {e}")

            except Exception as e:
                logger.error(f"Unexpected error generating embedding: {e}")
                raise EmbeddingError(f"Embedding generation failed: {e}")

        return None

    def embed_batch(self, texts: list[str]) -> list[Optional[list[float]]]:
        """
        Generate embeddings for multiple texts in batch.

        Args:
            texts: List of texts to embed

        Returns:
            list: List of embedding vectors (None for failed items)
        """
        if not self.is_available:
            logger.warning("Embedding service not available")
            return [None] * len(texts)

        if not texts:
            return []

        results = []

        # Process in batches
        for i in range(0, len(texts), self.MAX_BATCH_SIZE):
            batch = texts[i:i + self.MAX_BATCH_SIZE]
            batch_results = self._embed_batch_internal(batch)
            results.extend(batch_results)

        return results

    # P0-2 Fix: Alias for sync method (consensus_engine compatibility)
    embed_batch_sync = embed_batch

    def _embed_batch_internal(self, texts: list[str]) -> list[Optional[list[float]]]:
        """
        Internal method to embed a batch of texts.

        Args:
            texts: List of texts (max MAX_BATCH_SIZE)

        Returns:
            list: List of embedding vectors
        """
        # Filter out empty texts, keep track of indices
        valid_indices = []
        valid_texts = []

        for i, text in enumerate(texts):
            if text and text.strip():
                # Truncate if needed
                max_chars = 32000
                if len(text) > max_chars:
                    text = text[:max_chars]
                valid_texts.append(text)
                valid_indices.append(i)

        if not valid_texts:
            return [None] * len(texts)

        for attempt in range(self.MAX_RETRIES):
            try:
                start_time = time.time()

                response = self.client.embeddings.create(
                    model=self.MODEL,
                    input=valid_texts,
                    dimensions=self.DIMENSION,  # Reduce from 3072 to 2000 for pgvector
                )

                elapsed_ms = int((time.time() - start_time) * 1000)
                logger.info(f"Generated {len(valid_texts)} embeddings in {elapsed_ms}ms")

                # Map results back to original indices with dimension validation (P0-002 fix)
                results = [None] * len(texts)
                failed_indices = []

                for idx, embedding_data in enumerate(response.data):
                    original_idx = valid_indices[idx]
                    embedding = embedding_data.embedding

                    # Validate embedding dimension (P0-002)
                    if embedding and len(embedding) != self.DIMENSION:
                        logger.error(
                            f"Embedding dimension mismatch at index {original_idx}: "
                            f"expected {self.DIMENSION}, got {len(embedding)}"
                        )
                        failed_indices.append(original_idx)
                        continue

                    results[original_idx] = embedding

                # Log failed embeddings for debugging (P0-002)
                none_count = sum(1 for r in results if r is None)
                if none_count > 0:
                    logger.warning(
                        f"Batch embedding: {none_count}/{len(texts)} items returned None "
                        f"(empty inputs: {len(texts) - len(valid_texts)}, "
                        f"dimension errors: {len(failed_indices)})"
                    )

                return results

            except openai.RateLimitError as e:
                logger.warning(f"Batch rate limit hit (attempt {attempt + 1}): {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY * (attempt + 1) * 2)  # Longer delay for batches
                else:
                    raise EmbeddingError(f"Batch rate limit exceeded")

            except openai.APIError as e:
                logger.error(f"Batch OpenAI API error (attempt {attempt + 1}): {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                else:
                    raise EmbeddingError(f"Batch API error: {e}")

            except Exception as e:
                logger.error(f"Unexpected error in batch embedding: {e}")
                raise EmbeddingError(f"Batch embedding failed: {e}")

        return [None] * len(texts)

    def compute_similarity(
        self,
        embedding1: list[float],
        embedding2: list[float],
    ) -> float:
        """
        Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            float: Cosine similarity score (0 to 1)
        """
        if not embedding1 or not embedding2:
            return 0.0

        if len(embedding1) != len(embedding2):
            raise ValueError("Embeddings must have same dimension")

        # Compute dot product
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))

        # Compute magnitudes
        mag1 = sum(a * a for a in embedding1) ** 0.5
        mag2 = sum(b * b for b in embedding2) ** 0.5

        if mag1 == 0 or mag2 == 0:
            return 0.0

        return dot_product / (mag1 * mag2)

    def embed_signal_summary(self, signal: dict) -> Optional[list[float]]:
        """
        Generate embedding for a signal's summary text.

        Combines title and summary for better semantic representation.

        Args:
            signal: Signal dict with 'title' and 'summary' keys

        Returns:
            Embedding vector or None
        """
        title = signal.get("title", "")
        summary = signal.get("summary", "")
        signal_type = signal.get("signal_type", "")
        event_type = signal.get("event_type", "")

        # Combine relevant fields for embedding
        combined_text = f"""
Signal Type: {signal_type}
Event Type: {event_type}
Title: {title}
Summary: {summary}
""".strip()

        return self.embed_text(combined_text)


# Singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """
    Get singleton embedding service instance (thread-safe).

    P0-001 fix: Double-checked locking pattern for thread safety
    in Celery multi-worker environment.
    """
    global _embedding_service

    # First check without lock (fast path)
    if _embedding_service is not None:
        return _embedding_service

    # Acquire lock for initialization
    with _embedding_service_lock:
        # Double-check after acquiring lock
        if _embedding_service is None:
            _embedding_service = EmbeddingService()
            logger.info("EmbeddingService singleton initialized")

    return _embedding_service


def reset_embedding_service() -> None:
    """
    Reset singleton instance (for testing purposes).
    """
    global _embedding_service
    with _embedding_service_lock:
        _embedding_service = None
        logger.info("EmbeddingService singleton reset")
