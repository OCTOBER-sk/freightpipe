#!/bin/bash
cd /home/santhosh/projects/freight-doc-normalizer/backend

opencode run --agent default --model opencode-go/mimo-v2.5-pro "
PHASE 2: Pipeline Implementation (Classify + Split + Extract + Normalize + Validate)

Read /home/santhosh/projects/freight-doc-normalizer/BACKEND.md sections 5.1-5.5 for the full spec.

STEP 1: Complete src/freightpipe/pipeline/classify.py
- Rules-first: regex/keyword scoring against freight doc headers (RATE CONFIRMATION, BILL OF LADING, PROOF OF DELIVERY, INVOICE)
- Each doc type gets a rule-based score 0-1
- LLM escalation when top score < 0.75 or top-2 within 0.1
- Classification prompt template from BACKEND.md section 6.1
- Result: doc_type + classification_confidence

STEP 2: Complete src/freightpipe/pipeline/split.py
- Header-repeat detection (new doc header mid-file)
- Font/layout discontinuity heuristics via pdfplumber
- LLM fallback with summarized page digest (not full pages)
- Output: list of segments with page_start/page_end

STEP 3: Complete src/freightpipe/pipeline/extract.py
- Born-digital path: pdfplumber/pypdf text extraction
- Scan detection: text density threshold (>20 chars/page)
- OCR path: Gemini Flash vision (primary) -> pytesseract (fallback) -> PaddleOCR (secondary)
- LLM extraction prompt templates from BACKEND.md section 6.1
- Structured output enforcement (JSON schema where supported)
- Store per-field in extracted_fields with confidence + source bbox

STEP 4: Complete src/freightpipe/pipeline/normalize.py
- Dates -> ISO 8601 (reference_date = job submission)
- Money -> {amount: float, currency: USD}
- Units -> weight to lbs
- Accessorial vocabulary mapping (controlled vocab + synonym table)
- 100% deterministic, no LLM

STEP 5: Complete src/freightpipe/pipeline/validate.py
- Required fields check per doc type (BACKEND.md section 3.2)
- Date sanity: pickup <= delivery <= due date
- Money sanity: total ≈ linehaul + fuel + accessorials ($0.02 tolerance)
- Load number cross-reference

STEP 6: Write tests
- tests/test_classify.py: rule scoring, LLM escalation, all 5 doc types
- tests/test_split.py: single-page, multi-page header split, LLM fallback
- tests/test_extract.py: born-digital, scan detection, structured output parsing
- tests/test_normalize.py: dates, money, units, accessorial vocab
- tests/test_validate.py: required fields, date sanity, money sanity

STEP 7: SELF-REVIEW (mandatory):
- Run: python -m pytest tests/ -v --tb=short
- Verify all pipeline modules are importable and have proper type hints
- Verify prompt templates match BACKEND.md section 6.1 exactly
- Report: files changed, test count, any risks

Do NOT touch files in db/repos/ or llm/ (already complete from Phase 1).
Do NOT add new pip dependencies.
" 2>&1 | tee /tmp/zeus-phase2.log
