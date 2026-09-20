from pathlib import Path
import json, sys
import numpy as np
import pdfplumber
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / 'model'
REFERENCES_DIR = BASE_DIR / 'references'
OUTPUT_FILE = BASE_DIR / 'embeddings' / 'department_embeddings.json'

def extract_pdf_text(pdf_path):
    parts=[]
    with pdfplumber.open(pdf_path) as doc:
        for page in doc:
            text=page.extract_text()
            if text: parts.append(text)
    return '\n'.join(parts).strip()

def load_model():
    if not MODEL_DIR.exists():
        raise FileNotFoundError(f'Model folder not found: {MODEL_DIR}')
    print(f'Loading local model from: {MODEL_DIR}')
    model=SentenceTransformer(str(MODEL_DIR), local_files_only=True)
    print('Local model loaded successfully.')
    return model

def main():
    model=load_model()
    department_embeddings={}; total=0
    dirs=sorted(p for p in REFERENCES_DIR.iterdir() if p.is_dir())
    if not dirs: raise RuntimeError(f'No department folders found inside {REFERENCES_DIR}')
    print('\nCreating department embeddings...')
    for d in dirs:
        pdfs=sorted(d.glob('*.pdf'))
        if not pdfs:
            print(f'[SKIP] {d.name}: no PDFs'); continue
        texts=[]; usable=[]
        for p in pdfs:
            text=extract_pdf_text(p)
            if not text:
                print(f'[WARNING] No extractable text: {p.name}'); continue
            texts.append(text); usable.append(p.name); total+=1
            print(f'[OK] {d.name:<20} {p.name}')
        if not texts: continue
        vecs=model.encode(texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)
        vec=np.mean(vecs, axis=0); norm=np.linalg.norm(vec)
        if norm==0: continue
        vec=vec/norm
        department_embeddings[d.name]={'embedding':vec.tolist(),'reference_documents':usable,'usable_document_count':len(usable)}
    if not department_embeddings: raise RuntimeError('No department embeddings were created.')
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    output={'model':'all-MiniLM-L6-v2','embedding_dimension':len(next(iter(department_embeddings.values()))['embedding']),'departments':department_embeddings}
    OUTPUT_FILE.write_text(json.dumps(output,indent=2),encoding='utf-8')
    print('='*60); print(f'Departments created : {len(department_embeddings)}'); print(f'Reference PDFs used  : {total}'); print(f'Saved to             : {OUTPUT_FILE}'); print('Embedding creation completed successfully.')

if __name__=='__main__':
    try: main()
    except Exception as e: print(f'\nERROR: {e}'); sys.exit(1)
