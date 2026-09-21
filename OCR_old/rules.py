
"""
=============================================================================
CDTRS OCR — Regex Rules & Department Keyword Configuration
=============================================================================
This file is the SINGLE SOURCE OF TRUTH for:
  1. Field extraction regex patterns  (FIELD_PATTERNS)
  2. Department suggestion keywords   (DEPARTMENT_KEYWORDS)
  3. Score weights                    (DEPARTMENT_SCORE_WEIGHTS)
  4. Document type canonical map      (DOCUMENT_TYPE_CANONICAL)
  5. OCR engine tuning config         (PRINT_CONFIG, HANDWRITING_CONFIG)

HOW TO EDIT:
  • Add new patterns to any list inside FIELD_PATTERNS — they are tried in
    order; the FIRST match wins (put most-specific patterns first).
  • Add new departments to DEPARTMENT_KEYWORDS with their keyword lists.
  • Edit DEPARTMENT_SCORE_WEIGHTS to boost high-signal keywords.
  • Patterns use Python `re` syntax (case-insensitive flags applied at runtime).
  • NO imports from paddleocr or ocr.py are needed here — keep it plain Python.

=============================================================================
"""

# ---------------------------------------------------------------------------
# 1. FIELD EXTRACTION PATTERNS
#    Each key maps to a list of regex patterns (tried top-to-bottom).
#    Use a named group (?P<val>...) to capture the extracted value.
# ---------------------------------------------------------------------------

FIELD_PATTERNS: dict[str, list[str]] = {

    # ---- Reference / File Number ------------------------------------------
    "reference_number": [
        r"(?:F\.?\s*No\.?|File\s*No\.?|Ref\.?\s*No\.?|Letter\s*No\.?)\s*[:\-]?\s*(?P<val>[\w/\-\.]{3,}(?:\s*[\w/\-\.]+)*)(?:\n|$)",
        r"(?:Ref\.?)\s*[:\-]\s*(?P<val>[\w/\-\.]{3,})(?:\s|$)",
        r"\b(?P<val>[A-Z]{1,5}[-/]\d{2,6}[-/]\d{2,4})\b",        # e.g. HR/2025/001
        r"\b(?P<val>\d{4,}/\d{2,}/[A-Z]{2,})\b",                  # e.g. 2025/08/FIN
    ],

    # ---- Date -------------------------------------------------------------
    "date": [
        r"\b(?P<val>(?:0?[1-9]|[12]\d|3[01])[\-/\.](?:0?[1-9]|1[0-2])[\-/\.](?:19|20)\d{2})\b",
        r"\b(?P<val>(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+\d{1,2}[,\s]+\d{4})\b",
        r"\b(?P<val>\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4})\b",
        r"[Dd]ated?\s*[:\-]?\s*(?P<val>[\d]{1,2}[\-/\.][\d]{1,2}[\-/\.][\d]{2,4})",
    ],

    # ---- Subject ----------------------------------------------------------
    "subject": [
        r"(?m)^(?:Sub(?:ject)?|RE|Reg(?:arding)?|Re)\s*[:\-]\s*(?P<val>.+?)$",
        r"(?m)^(?:Matter|Ref)\s*[:\-]\s*(?P<val>.+?)$",
        r"Sub\s*:\s*(?P<val>.+?)(?:\n|$)",
    ],

    # ---- From Address / Sender --------------------------------------------
    "from_address": [
        r"(?m)^(?:From|Sender|Issued\s+by)\s*[:\-]\s*(?P<val>.+?)$",
        r"(?m)^(?P<val>(?:The\s+)?(?:Director|Secretary|Ministry|Department|"
        r"Office|Commissioner|Collector|Additional|Joint|Deputy|Principal)\s+.+?)$",
    ],

    # ---- To Address / Recipient -------------------------------------------
    "to_address": [
        r"(?m)^(?:To|Addressed\s+to|Recipient)\s*[:\-]?\s*(?P<val>[A-Za-z].{4,})$",
        r"(?:Dear|Sir|Ma'?am)\s*[,\.]?\s*(?P<val>(?:The\s+)?[A-Z][^\n]{5,60})(?:\n|$)",
    ],

    # ---- Priority / Urgency -----------------------------------------------
    # PZ_26/08: Order multi-word priority expressions first so High Priority and Most Urgent match correctly
    "priority": [
        r"\b(?P<val>(?:Most\s+Urgent|High[\s\-]Priority|Top[\s\-]Secret|Urgent|Immediate|Critical|Confidential|Secret|Flash|High|Medium|Low|Priority))\b",
        r"\b(?P<val>Demi[\s\-]Official)\b",
    ],

    # ---- Deadline / Due Date ----------------------------------------------
    "deadline": [
        r"(?:by|before|on\s+or\s+before|due\s+(?:date|by)|submit\s+(?:by|before))\s+"
        r"(?P<val>(?:0?[1-9]|[12]\d|3[01])[\-/\.](?:0?[1-9]|1[0-2])[\-/\.](?:19|20)\d{2})(?:[^\d]|$)",
        r"(?:by|before|on\s+or\s+before|due\s+(?:date|by))\s+"
        r"(?P<val>(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+\d{1,2}[,\s]+\d{4})",
        r"(?:deadline|last\s+date|due\s+date)\s*[:\-]?\s*(?P<val>[\d/\.\-]+)(?:[^\d]|$)",
    ],

    # ---- Designation ------------------------------------------------------
    "designation": [
        r"\b(?P<val>(?:Director\s+General|Joint\s+Secretary|Additional\s+Secretary|"
        r"Under\s+Secretary|Deputy\s+Secretary|Principal\s+Secretary|"
        r"Chief\s+Secretary|District\s+Collector|Commissioner|Director|Secretary|"
        r"Head\s+of\s+Department|HOD|Manager|Officer|Superintendent|Inspector|"
        r"Constable|Clerk|Assistant|Advisor|Consultant|CEO|CFO|CTO|MD|GM|DGM|AGM))\b",
    ],

    # ---- Monetary / Financial Amounts -------------------------------------
    "amount": [
        r"(?:Rs\.?|₹|INR|Rupees?)\s*(?P<val>[\d,]+(?:\.\d{1,2})?(?:\s*(?:Lakh|Lakhs|Crore|Crores|Thousand))?)",
        r"(?P<val>[\d,]+(?:\.\d{1,2})?)\s*(?:Rs\.?|₹|INR|Rupees?|Lakhs?|Crores?)",
    ],

    # ---- Document Type ----------------------------------------------------
    "document_type": [
        r"\b(?P<val>(?:D\.O\.?\s*)?(?:Office\s+)?(?:Memorandum|Memo|Circular|Notice|"
        r"Order|Notification|Gazette|Letter|Report|Minutes|Agenda|Directive|"
        r"Instructions?|Communiqu[eé]|Endorsement|Forwarding\s+Letter|"
        r"Inter[\s\-]?[Dd]epartmental\s+Note|Policy|Guideline|Tender|Warrant))\b",
    ],

    # ---- Signature / Closing Block ----------------------------------------
    "signature_block": [
        r"(?:Yours?\s+(?:faithfully|sincerely|truly|obediently)|Sd\/?\.?\-?|Signed|Signature)"
        r"\s*[:\-]?\s*(?P<val>[A-Za-z].{3,})(?:\n|$)",
    ],
}

# ---------------------------------------------------------------------------
# 2. DEPARTMENT SUGGESTION KEYWORDS
#    Format: { "Department Name": [ "keyword1", "keyword2", ... ] }
#    Keywords are matched case-insensitively in the full OCR text.
#    Each match scores +1.0 (or more if listed in DEPARTMENT_SCORE_WEIGHTS).
# ---------------------------------------------------------------------------

DEPARTMENT_KEYWORDS: dict[str, list[str]] = {
    "Finance": [
        "budget", "expenditure", "sanction", "funds", "accounts",
        "payment", "invoice", "grant", "allocation", "appropriation", "audit",
        "revenue", "tax", "gst", "financial", "fiscal", "treasury",
        "reimbursement", "advance", "loan", "interest", "receipt", "voucher",
        "ledger", "balance sheet", "cash", "subsidy", "utilization certificate",
        "fund release", "contingency", "pay bill", "deduction", "salary", "disbursement",
        "tender", "purchase", "quotation", "vendor", "supply", "order",
        "rfp", "rfq", "bid", "contractor", "rate contract", "empanelment",
        "procurement", "goods", "services", "gem", "catalogue",
        "open tender", "limited tender", "single tender", "price bid",
        "technical bid", "l1", "lowest bid", "purchase order", "work order",
        "equipment requisition", "indents", "storekeeper", "inventory",
        "contract", "agreement", "billing", "capital grant",
    ],
    "HR": [
        "leave", "recruitment", "appointment", "transfer", "promotion",
        "personnel", "employee", "resignation", "retirement", "posting",
        "seniority", "increment", "deputation", "noc", "service record",
        "disciplinary", "suspension", "termination", "joining",
        "probation", "regularization", "manpower", "workforce", "hr",
        "human resources", "staff cadre", "grade pay", "annual increment", "medical fitness",
        "circular", "notice", "event", "office order", "meeting", "training",
        "stationery", "housekeeping", "security", "dak", "tour", "attendance",
        "cghs", "esi", "pension", "gratuity", "staff welfare",
    ],
    "Technical": [
        "software", "hardware", "network", "cybersecurity", "data", "system",
        "server", "database", "application", "website", "portal", "it",
        "technical", "systems engineer", "sysadmin", "infrastructure",
        "digital", "computer", "laptop", "firewall", "backup", "cloud",
        "bandwidth", "license", "erp", "crm", "api",
        "internet", "email", "antivirus", "encryption", "vpn", "domain",
        "engineering", "computer engineering", "laboratory", "practical",
        "journal", "ppt", "presentation", "hackathon", "sih", "project",
        "code", "programming", "python", "developer", "lab", "prerequisite",
        "unit test", "ut1", "department of computer", "technical session",
        "maintenance", "facility", "repair", "electrical", "plumbing", "civil",
        "hvac", "generator", "lift", "sanitation", "estate", "building",
        "renovation", "carpentry", "preventive maintenance", "equipment servicing",
    ],
}


# ---------------------------------------------------------------------------
# 3. SCORE WEIGHTS
#    Certain keywords are stronger signals — their hit score is multiplied.
#    Default score per keyword match = 1.0
# ---------------------------------------------------------------------------

DEPARTMENT_SCORE_WEIGHTS: dict[str, float] = {
    # Finance
    "sanction":                 3.0,
    "budget":                   2.5,
    "expenditure":              2.5,
    "audit":                    2.0,
    "fund release":             3.0,
    "utilization certificate":  3.0,
    "disbursement":             2.5,
    "tender":                   3.5,
    "purchase order":           3.5,
    "procurement":              3.0,
    "quotation":                2.5,
    "vendor":                   2.0,
    "rfp":                      3.0,

    # Human Resources
    "recruitment":              3.0,
    "appointment":              2.5,
    "transfer":                 2.0,
    "deputation":               2.5,
    "human resources":          3.5,
    "personnel":                2.5,
    "disciplinary":             3.0,
    "cghs":                     3.0,
    "esi":                      3.0,

    # Technical / IT
    "computer engineering":     5.0,
    "department of computer":   5.0,
    "cybersecurity":            3.0,
    "firewall":                 3.0,
    "software":                 2.0,
    "hardware":                 2.0,
    "hackathon":                3.5,
    "sih":                      3.5,
    "systems engineer":         3.0,
    "technical":                2.5,
    "laboratory":               2.0,
    "server maintenance":       3.5,
    "preventive maintenance":   3.0,
}

# ---------------------------------------------------------------------------
# 4. DOCUMENT TYPE CANONICAL MAP
#    Normalises free-form OCR output to a standard label.
# ---------------------------------------------------------------------------

DOCUMENT_TYPE_CANONICAL: dict[str, str] = {
    "memorandum":                   "Office Memorandum",
    "memo":                         "Office Memorandum",
    "circular":                     "Circular",
    "notice":                       "Notice",
    "order":                        "Office Order",
    "notification":                 "Notification",
    "gazette":                      "Gazette Notification",
    "letter":                       "Letter",
    "d.o":                          "D.O. Letter",
    "do":                           "D.O. Letter",
    "report":                       "Report",
    "minutes":                      "Meeting Minutes",
    "agenda":                       "Meeting Agenda",
    "directive":                    "Directive",
    "tender":                       "Tender Document",
    "policy":                       "Policy Document",
    "guideline":                    "Guidelines",
    "endorsement":                  "Endorsement",
    "forwarding letter":            "Forwarding Letter",
    "inter-departmental note":      "Inter-Departmental Note",
    "interdepartmental note":       "Inter-Departmental Note",
}

# ---------------------------------------------------------------------------
# 5. OCR ENGINE CONFIGURATION
#    Controls PaddleOCR behaviour for printed vs handwritten documents.
#    Adjust det_db_thresh / rec_score_thresh to trade speed vs accuracy.
# ---------------------------------------------------------------------------

PRINT_CONFIG: dict = {
    "use_angle_cls":    True,       # Auto-correct rotated/flipped text
    "lang":             "en",
    "det_db_thresh":    0.3,        # Box detection threshold (0–1)
    "det_db_box_thresh":0.5,
    "rec_score_thresh": 0.5,        # Recognition confidence threshold (0–1)
    "use_space_char":   True,
    "show_log":         False,
}

HANDWRITING_CONFIG: dict = {
    "use_angle_cls":    True,
    "lang":             "en",
    "det_db_thresh":    0.2,        # Lower — catches faint handwriting strokes
    "det_db_box_thresh":0.35,
    "rec_score_thresh": 0.3,        # Lower — accept lower-confidence handwriting
    "use_space_char":   True,
    "show_log":         False,
    # Image pre-processing (executed in ocr.py before passing to PaddleOCR)
    "preprocess_contrast": True,    # Adaptive histogram equalisation
    "preprocess_deskew":   True,    # Rotate tilted pages back to horizontal
    "preprocess_denoise":  True,    # Gaussian + median blur to reduce noise
}

# If average page confidence is below this value, treat as handwritten
HANDWRITING_CONFIDENCE_THRESHOLD: float = 0.72

# Minimum OCR character count to attempt field extraction
MIN_TEXT_LENGTH_FOR_EXTRACTION: int = 20


# ---------------------------------------------------------------------------
# 6. STANDALONE FIELD EXTRACTION & DEPARTMENT SUGGESTION HELPERS
#    PZ_26/08: Added standalone helpers for pure Python regex/keyword execution
#    without OpenCV or PaddleOCR dependencies.
# ---------------------------------------------------------------------------

def extract_fields(text: str) -> dict:
    """Apply all FIELD_PATTERNS from rules.py to text."""
    import re
    if not text or len(text.strip()) < MIN_TEXT_LENGTH_FOR_EXTRACTION:
        return {}

    extracted: dict = {}

    for field, patterns in FIELD_PATTERNS.items():
        if field == "designation":
            found: list = []
            for pat in patterns:
                for m in re.finditer(pat, text, re.IGNORECASE):
                    val = m.group("val").strip()
                    if val and val not in found:
                        found.append(val)
            if found:
                extracted[field] = found
        else:
            for pat in patterns:
                try:
                    m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
                except re.error:
                    continue
                if m:
                    try:
                        val = m.group("val").strip()
                    except IndexError:
                        val = m.group(0).strip()
                    if val:
                        extracted[field] = val
                        break

    # Normalise document_type
    if "document_type" in extracted:
        raw = extracted["document_type"].lower().strip()
        for key, canonical in DOCUMENT_TYPE_CANONICAL.items():
            if key in raw:
                extracted["document_type"] = canonical
                break

    return extracted


def suggest_department(text: str) -> dict:
    """Score each department against text using keyword + weight rules."""
    import re
    if not text or len(text.strip()) < MIN_TEXT_LENGTH_FOR_EXTRACTION:
        return {"suggested": None, "confidence": 0.0, "scores": {}}

    text_lower = text.lower()
    scores: dict = {}

    for dept, keywords in DEPARTMENT_KEYWORDS.items():
        dept_score = 0.0
        for kw in keywords:
            count = len(re.findall(re.escape(kw), text_lower))
            if count:
                weight = DEPARTMENT_SCORE_WEIGHTS.get(kw, 1.0)
                dept_score += count * weight
        if dept_score > 0:
            scores[dept] = round(dept_score, 2)

    if not scores:
        return {"suggested": None, "confidence": 0.0, "scores": {}}

    sorted_scores = dict(
        sorted(scores.items(), key=lambda x: x[1], reverse=True)
    )
    top_dept = next(iter(sorted_scores))
    top_score = sorted_scores[top_dept]
    total = sum(sorted_scores.values())
    confidence = round(top_score / total, 4) if total else 0.0

    return {
        "suggested": top_dept,
        "confidence": confidence,
        "scores": sorted_scores,
    }

