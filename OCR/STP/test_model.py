from pathlib import Path
import sys

from sentence_transformers import SentenceTransformer


BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "model" / "all-MiniLM-L6-v2"


print("=" * 60)
print("LOCAL ALL-MINILM-L6-V2 MODEL TEST")
print("=" * 60)

print(f"\nModel path:")
print(MODEL_DIR)

if not MODEL_DIR.exists():
    print("\nERROR: Model folder does not exist.")
    sys.exit(1)

print("\nLoading local model...")
print("Internet is NOT required for this test.")

try:
    model = SentenceTransformer(
        str(MODEL_DIR),
        local_files_only=True,
    )

    print("\nSUCCESS: Model loaded successfully!")

    test_text = (
        "This document contains technical information "
        "about fuel cell technology and hydrogen systems."
    )

    print("\nCreating test embedding...")

    embedding = model.encode(
        test_text,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    print("SUCCESS: Embedding created!")

    print(f"\nEmbedding type : {type(embedding)}")
    print(f"Embedding shape: {embedding.shape}")
    print(f"Embedding size : {len(embedding)}")

    print("\nFirst 10 values:")
    print(embedding[:10])

    print("\n" + "=" * 60)
    print("OFFLINE MINILM TEST PASSED")
    print("=" * 60)

except Exception as exc:
    print("\n" + "=" * 60)
    print("MODEL TEST FAILED")
    print("=" * 60)

    print("\nError:")
    print(exc)

    print("\nFull error type:")
    print(type(exc).__name__)

    sys.exit(1)