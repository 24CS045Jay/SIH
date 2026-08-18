# KMRL Portal Demo Rehearsal Checklist

This checklist is the fixed Phase 13 sequence for the synthetic KMRL Document Intelligence & Action Portal demonstration. It is designed for a single operator and a five-to-six-minute run-through. All records and documents are fictional and must remain visibly marked as **SYNTHETIC DEMO DATA — NOT CONFIDENTIAL KMRL DATA**.

## Before the audience arrives

Start PostgreSQL, Redis, the API, the worker, and the frontend. From `backend/`, run `python scripts/reset_demo_environment.py --yes` with `KMRL_API_BASE` pointing to the running API. The reset command clears the demo records and storage, reseeds the seven role accounts, regenerates the seven watermarked PDFs, and uploads them through the normal API processing path. Confirm that the reset output reports seven review-ready documents and three Maintenance Manual V2-to-V3 changes. Run `python scripts/evaluate_known_answers.py` and confirm the known-answer evaluation passes before opening the browser.

Use `demo-password` with the seeded accounts. The preferred presenter account is `reviewer.demo@kmrl.example`. The Engineering User is `engineering.demo@kmrl.example`, the Executive Viewer is `executive.demo@kmrl.example`, and the Auditor is `auditor.demo@kmrl.example`.

## Fixed live sequence

| Step | Screen and action | Evidence to state aloud |
|---|---|---|
| 1 | Open the landing screen and identify the operational problem: important circulars are difficult to route, obligations can be missed, and reviewers need source evidence before acting. | “This portal turns approved document evidence into reviewable operational work; it does not replace human approval.” |
| 2 | Log in through **Demo Login** as the Reviewer. | Point out the role, department, protected navigation, and persistent synthetic-data indicator. |
| 3 | Open **Documents**, upload `Safety Circular S-101.pdf`, and show the queued/processing state. | Explain that the HTTP request returns immediately and OCR/intelligence run through the processing pipeline. |
| 4 | Open the processed document’s Intelligence Card. | Show classification, entities, deadline, priority reason codes, suggested routing, confidence, and the **AI-generated** label. |
| 5 | Open the source and click a field or alert to populate the Trust Panel. | Show page number, extracted span, reviewer state, model version, and the synthetic-data watermark. |
| 6 | Open **Alert Center**. Move the critical alert from Draft to Needs review. Attempting direct approval must fail; then approve it after one manual edit to the suggested action. | “Critical alerts cannot skip human review; the API enforces this transition.” |
| 7 | Use **Quick Share** to route the minimum excerpt, summary, action, and deadline to Engineering User. Create the action from the approved alert. | Emphasize that the raw document is not shared by default and that the route is auditable. |
| 8 | Switch to the Engineering User or use the existing owner session. Open **Action Center**, acknowledge the action, move it to In progress, then Completed with completion evidence. Return to Reviewer and verify/close it. | Show the append-only status-history timeline and the final human verification. |
| 9 | Open **Ask portal** and ask: “What changed in the brake inspection frequency, who is affected, and what action is required?” | Show the cited answer and open one source citation. State that answers require approved evidence. |
| 10 | Ask: “What is the lunar depot expansion launch date?” | Show the exact refusal: “Information not available in the approved documents.” |
| 11 | Upload `Maintenance Manual V3.pdf` after V2 is already present. Open **What’s Changed?** and show exactly three changes: brake inspection frequency, new checklist section, and new deadline. | Explain each change in operational language and convert one change into a draft action candidate. |
| 12 | Open the resulting action and show its status history, then finish on the **Analytics** or **Audit log** screen. | Close with: “Every important AI output is tied to source evidence, human review, workflow history, and an append-only audit record.” |

## Recovery notes

If a file was accidentally uploaded twice, do not delete database rows manually during the presentation; reset the demo environment and repeat the sequence. If the API is unavailable, stop the live flow rather than presenting stale or uncited output. If a supported RAG question refuses, run the known-answer evaluator after reset before retrying. The Auditor view is read-only and should be used to show the recorded view, upload, route, share, query, edit, and status-change events.

## Automated checks

Run `python -m unittest discover -s tests -p 'test_*.py'` for the focused backend unit suite. Run `KMRL_API_BASE=http://127.0.0.1:8000/api/v1 python scripts/test_core_loop_e2e.py` for the full upload-to-close integration flow. Run `KMRL_API_BASE=http://127.0.0.1:8000/api/v1 python scripts/evaluate_known_answers.py` for the fixed RAG evaluation set. The reset script is intentionally guarded and requires `--yes` because it clears the demo database and storage.
