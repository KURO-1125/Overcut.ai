import pytest
from backend.vector_store.engine import VectorEngine
import numpy as np
from PIL import Image
import os

@pytest.fixture(scope="module")
def vector_engine():
    # Initialize on CPU to avoid allocating VRAM during tests
    return VectorEngine(model_name="ViT-B-32", pretrained="laion2b_s34b_b79k", device="cpu")

def test_embed_artifact(vector_engine, tmp_path):
    """
    Task 3.2: Verify the joint image+text embedding is correctly generated
    and normalized.
    """
    # Create a dummy image for testing
    dummy_image_path = tmp_path / "dummy_roi.png"
    img = Image.new('RGB', (300, 100), color = 'black')
    img.save(dummy_image_path)
    
    # Metadata string
    metadata = "Monza 2023, Verstappen Turn 1 Lockup, Speed and Brake channels"
    
    # Generate embedding
    embedding = vector_engine.embed_artifact(str(dummy_image_path), metadata)
    
    # Check output type and shape (ViT-B-32 outputs 512-dim vectors)
    assert isinstance(embedding, np.ndarray)
    assert embedding.shape == (1, 512)
    
    # Check normalization (L2 norm should be approximately 1.0)
    norm = np.linalg.norm(embedding)
    assert np.isclose(norm, 1.0, atol=1e-5)
