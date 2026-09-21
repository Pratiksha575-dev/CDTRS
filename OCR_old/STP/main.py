import sys
from pathlib import Path
from create_embeddings import main as create_department_embeddings
from suggest_department import suggest_departments, print_suggestions

def main():
    if len(sys.argv)<2:
        print('Usage: python main.py <new_document.pdf>'); sys.exit(1)
    pdf=Path(sys.argv[1])
    if not pdf.exists(): print(f'ERROR: New document not found: {pdf}'); sys.exit(1)
    print('\n'+'='*60); print('        CDTRS STANDALONE SEMANTIC ROUTING'); print('='*60)
    print('\n[STEP 1/2] Creating department embeddings...')
    create_department_embeddings()
    print('\n[STEP 2/2] Suggesting departments for new document...')
    results=suggest_departments(str(pdf),top_k=5)
    print_suggestions(str(pdf),results)
    if results: print(f"\nTop suggestion: {results[0]['department']} (similarity = {results[0]['score']:.4f})")
    print('\nStandalone semantic routing test completed.')

if __name__=='__main__':
    try: main()
    except Exception as e: print(f'\nERROR: {e}'); sys.exit(1)
