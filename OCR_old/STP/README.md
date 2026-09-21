# STP — Standalone Semantic Department Suggestion

Reference PDFs are mapped to departments by folder name:

STP/references/FCTD/*.pdf
STP/references/Mechanical/*.pdf
STP/references/Electrical/*.pdf

Put the complete `all-MiniLM-L6-v2` SentenceTransformer model in `STP/model/`.

Run:

`python main.py new_document.pdf`

The prototype creates department embeddings, embeds the new PDF, compares cosine similarity, and prints ranked department suggestions.

The model is loaded with `local_files_only=True`, so after the model and Python packages are installed locally, no Internet or LAN is required to run the demo.
