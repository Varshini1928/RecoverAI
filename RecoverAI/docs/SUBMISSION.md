# Submission Guide

## Final checklist

- Repository title: `RecoverAI — AI Revenue Recovery Agent`
- Track: `03: AI Revenue Recovery`
- README disclaimer remains visible.
- Run `pytest -q` and `npm run build`; include the results in the submission form.
- Record the demo from a freshly seeded database for a clean, reproducible story.
- Never add a real secret, live Razorpay key, customer record, or payment credential.

## Suggested submission description

RecoverAI is a safety-first multi-agent MVP that recovers failed recurring payments through a LangGraph workflow. It scores recoverability, selects one action, applies deterministic policy controls, executes a reproducible test-mode simulation, and persists an end-to-end audit trail. The dashboard reports only metrics calculated from stored synthetic cases.

## Fresh demo

```bash
cp .env.example .env
python -m backend.app.seed
docker compose up --build
```

To reset locally, remove only `data/recoverai.db`, then rerun the seed command. Do not delete the full `data` directory if it contains your own exports.

## Evidence to attach

1. Login screen with synthetic/test-mode wording.
2. Dashboard after batch processing.
3. One complete five-agent audit trail.
4. A blocked safety rule.
5. Human-review queue.
6. Passing test output.

