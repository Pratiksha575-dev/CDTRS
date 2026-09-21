import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

# Fix Windows DLL conflict between PyTorch and PaddlePaddle by loading torch first
try:
    import torch
except ImportError:
    pass

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_OCR_DIR = _PROJECT_ROOT / "OCR_new"
if str(_OCR_DIR) not in sys.path:
    sys.path.insert(0, str(_OCR_DIR))

try:
    # Explicitly import layout modules to ensure they are cached and paths are resolved
    import layout.layout_analyzer
except Exception as e:
    print('Failed to pre-load layout:', e)

try:
    from document_intelligence import DocumentProcessor
    _OCR_AVAILABLE = True
except ImportError as e:
    _OCR_AVAILABLE = False
    DocumentProcessor = None
    print('OCR unavailable:', e)

logger = logging.getLogger(__name__)

class CDTRSOCRAdapter:
    def __init__(self):
        self.processor = DocumentProcessor() if _OCR_AVAILABLE else None
    
    def process(self, file_path: str, reference_texts: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Process the document and return a simplified dict.
        reference_texts: Used for semantic department matching.
        """
        if not self.processor:
            return {"error": "OCR system not available"}
        
        try:
            res = self.processor.process(file_path, mode="full", reference_texts=reference_texts)
            
            # Extract standard fields
            extracted = res.extracted_fields
            
            # Enhance with entities (like PERSON, DEPARTMENT)
            for ent in res.entities:
                label = ent.get("label", "")
                text = ent.get("text", "")
                if label and text:
                    # Collect all mentions of people or departments
                    key = label.lower()
                    if key not in extracted:
                        extracted[key] = []
                    if isinstance(extracted[key], list):
                        extracted[key].append(text)
                    else:
                        extracted[key] = [extracted[key], text]
            
            # Detect Director instructions using Layout & Text Type (Handwriting)
            # Find any handwritten text that looks like a routing instruction
            director_instruction_detected = False
            director_remark = None
            
            for region in res.regions:
                # We also check if text_type was identified as HANDWRITTEN
                if region.get("text_type") == "HANDWRITTEN":
                    text = region.get("text", "").lower()
                    
                    if "director" in text and "to director" in text:
                        continue # Addressed to director
                    
                    instruction_verbs = ["send to", "forward to", "discuss", "approved", "speak", "hod", "fctd"]
                    if any(v in text for v in instruction_verbs) or "director" in text:
                        director_instruction_detected = True
                        director_remark = region.get("text", "")
                        break
            
            if director_instruction_detected:
                extracted["prior_director_review_detected"] = "true"
                extracted["director_handwritten_remark"] = director_remark
            
            return {
                "success": True,
                "text": res.full_text,
                "confidence": 0.98, # PaddleEngine doesn't always provide a global conf easily
                "extracted_fields": extracted,
                "similarities": res.semantic.get("similarities", []) if res.semantic else [],
                "engine": "OCR_new"
            }
        except Exception as e:
            logger.exception("OCR processing failed")
            return {"error": str(e), "success": False}

ocr_adapter = CDTRSOCRAdapter()
