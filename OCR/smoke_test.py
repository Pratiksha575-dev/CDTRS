import sys, os
sys.path.insert(0, '.')

# Verify imports
from ocr import DocumentOCR, ALL_EXTENSIONS
from rules import FIELD_PATTERNS, DEPARTMENT_KEYWORDS, PRINT_CONFIG

print('=== Import Test PASSED ===')
print('Supported extensions:', sorted(ALL_EXTENSIONS))
print('Field patterns:', list(FIELD_PATTERNS.keys()))
print('Departments:', list(DEPARTMENT_KEYWORDS.keys()))

# Test field extraction with sample text (no PaddleOCR needed)
engine = DocumentOCR.__new__(DocumentOCR)
engine.use_gpu = False
engine.force_handwriting = False

sample_text = """
F.No. 25/HR/2025/001
Date: 15/08/2025
Subject: Transfer of Senior Officer to Finance Division

To,
The Director General
Ministry of Finance

This is regarding the Urgent transfer order sanctioned for
budget reallocation of Rs. 5,00,000.
Please route to Finance department immediately.
Deadline: 31/08/2025.

Yours faithfully,
Sd/-
Joint Secretary
"""

fields = engine._extract_fields(sample_text)
dept   = engine._suggest_department(sample_text)

print()
print('=== Extracted Fields ===')
for k, v in fields.items():
    print('  {}: {}'.format(k, v))

print()
print('=== Department Suggestion ===')
print('  Suggested:', dept['suggested'])
print('  Confidence:', '{:.1%}'.format(dept['confidence']))
print('  Top scores:')
for d, s in list(dept['scores'].items())[:4]:
    print('    {} -> {}'.format(d, s))

print()
print('=== Smoke Test PASSED ===')
