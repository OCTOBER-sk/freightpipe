#!/bin/bash
cd /home/santhosh/projects/freight-doc-normalizer/backend

opencode run --agent default --model opencode-go/mimo-v2.5-pro "
PHASE 3: Match Engine + Confidence Scoring + Review Queue

Read /home/santhosh/projects/freight-doc-normalizer/BACKEND.md sections 5.6-5.8 for the full spec.

STEP 1: Complete src/freightpipe/pipeline/match.py
3-way match engine per BACKEND.md section 5.6:
- For each line item category (linehaul, fuel_surcharge, each accessorial type, weight, pieces):
  - Pull value from each source doc that has it
  - Compare pairwise where both exist:
    - rate_con_value != invoice_value beyond tolerance -> rate_delta, amount = invoice - rate_con
    - Accessorial on invoice but not rate-con -> extra_accessorial
    - Accessorial on rate-con but not invoice -> missing_accessorial
    - weight/pieces on BOL vs POD differ -> weight_variance / pieces_variance
- Write one row per line item per shipment to match_results
- Any discrepancy_flag != none -> review_required

STEP 2: Complete src/freightpipe/pipeline/confidence.py
Confidence scoring per BACKEND.md section 5.7:
- Per-field confidence:
  - Rule-extracted: 0.95-0.99 fixed by extraction method
  - LLM-extracted: verification pass (second cheaper LLM call, yes/no + certainty)
  - OCR-sourced: ceiling 0.85 max
- Per-document: weighted average of required fields, floored by classification confidence
- HITL routing: doc_confidence < 0.80 OR any field < 0.70 OR any discrepancy -> review_queue

STEP 3: Implement review queue logic in pipeline
- State machine: pending -> in_review -> resolved/escalated (BACKEND.md section 5.8)
- Create review_queue items when HITL conditions met
- Resolution: approved (accept as-is), corrected (override fields), escalated (manual intervention)

STEP 4: Write tests
- tests/test_match.py: all discrepancy flag types, tolerance handling, multi-line-item matching
- tests/test_confidence.py: rule vs LLM vs OCR confidence, HITL threshold routing, verification pass
- tests/test_review.py: state machine transitions, resolution types, corrections write-back

STEP 5: SELF-REVIEW (mandatory):
- Run: python -m pytest tests/ -v --tb=short
- Verify match engine uses exact flag values from BACKEND.md section 3.1
- Verify confidence thresholds: document=0.80, field=0.70 (from BACKEND.md section 5.7)
- Report: files changed, test count, any risks

Do NOT touch files in db/repos/, llm/, or pipeline/extract.py, normalize.py, validate.py (already complete).
" 2>&1 | tee /tmp/zeus-phase3.log
