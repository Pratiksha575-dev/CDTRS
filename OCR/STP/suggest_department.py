from pathlib import Path
import json, sys
import numpy as np
import pdfplumber
from sentence_transformers import SentenceTransformer

BASE_DIR=Path(__file__).resolve().parent
MODEL_DIR=BASE_DIR/'model'
EMBEDDINGS_FILE=BASE_DIR/'embeddings'/'department_embeddings.json'

def extract_pdf_text(pdf_path):
    parts=[]
    with pdfplumber.open(pdf_path) as doc:
        for page in doc:
            text=page.extract_text()
            if text: parts.append(text)
    return '\n'.join(parts).strip()

def suggest_departments(pdf_path, top_k=5):
    pdf=Path(pdf_path)
    if not pdf.exists(): raise FileNotFoundError(f'PDF not found: {pdf}')
    if not EMBEDDINGS_FILE.exists(): raise FileNotFoundError('Run create_embeddings.py first.')
    text=extract_pdf_text(pdf)
    if not text: raise ValueError(f'No extractable text found in {pdf.name}.')
    data=json.loads(EMBEDDINGS_FILE.read_text(encoding='utf-8'))
    model=SentenceTransformer(str(MODEL_DIR), local_files_only=True)
    doc_vec=model.encode(text,convert_to_numpy=True,normalize_embeddings=True,show_progress_bar=False)
    results=[]
    for dept,info in data['departments'].items():
        dept_vec=np.asarray(info['embedding'],dtype=np.float32)
        score=float(np.dot(doc_vec,dept_vec)/(np.linalg.norm(doc_vec)*np.linalg.norm(dept_vec)))
        results.append({'department':dept,'score':score})
    return sorted(results,key=lambda x:x['score'],reverse=True)[:top_k]

def print_suggestions(pdf_path,results):
    print('\n'+'='*60); print('       CDTRS SEMANTIC DEPARTMENT SUGGESTION'); print('='*60)
    print(f'Document: {Path(pdf_path).name}\n'); print('Department Suggestions'); print('-'*60)
    for i,r in enumerate(results,1): print(f"{i}. {r['department']:<25} {r['score']:.4f}")
    print('='*60)

if __name__=='__main__':
    if len(sys.argv)<2: print('Usage: python suggest_department.py <new_document.pdf>'); sys.exit(1)
    try:
        pdf=sys.argv[1]; print_suggestions(pdf,suggest_departments(pdf))
    except Exception as e: print(f'\nERROR: {e}'); sys.exit(1)
