# Five-minute Demo Script

> Say clearly: “Everything shown is synthetic, and the payment adapter is simulated/test mode. No real charge occurs.”

## 0:00–0:35 — Problem and solution

Failed recurring payments create involuntary churn. RecoverAI triages every event, chooses one bounded action, blocks unsafe behavior, and makes every decision explainable.

## 0:35–1:05 — Architecture

Show the README diagram. Explain React, FastAPI, SQLite, and the LangGraph sequence. Mention that Gemini is optional; deterministic rules make the demo free and reproducible.

## 1:05–2:00 — Process a failed payment

Open a pending `technical_error` case below ₹25,000 with fewer than three attempts. Process it, then open the decision drawer. Walk through Scorer, Strategist, Safety Gate, Sender, and Audit entries.

## 2:00–2:35 — Block unsafe retry

Open an `expired_card` or three-attempt case. Show that the deterministic safety rule prevents retry and records the exact rule. Emphasize that AI recommendations never bypass policy.

## 2:35–3:10 — Human escalation

Process a case above ₹25,000. Open Human Review and approve or reject it. Explain explicit human control and the second audit trace.

## 3:10–3:35 — Idempotency

In `/docs`, POST the same synthetic event twice to `/api/cases` using one idempotency key. The second call returns 409, and the stored duplicate-prevention metric increases.

## 3:35–4:30 — Dashboard

Click Process All Pending Cases. Explain revenue at risk, explicitly recovered revenue, success rate, failure distribution, strategy rate, safety counters, and CSV export. A reminder always records zero revenue.

## 4:30–5:00 — Results and limitations

State the values currently visible; do not memorize hard-coded numbers. Clarify these are measured simulator results, not production Razorpay outcomes. Close with production next steps: signed Razorpay test webhooks, scalable database/workers, stronger identity, and live notifications.

