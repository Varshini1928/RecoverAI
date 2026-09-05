import json, logging
from .config import get_settings

log=logging.getLogger("recoverai.llm")
ALLOWED={"RETRY","REMIND","ESCALATE","STOP"}

def gemini_strategy(case, fallback):
    """Use Gemini only when configured; validation failures safely return the deterministic fallback."""
    key=get_settings().gemini_api_key
    if not key: return fallback
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        model=genai.GenerativeModel("gemini-1.5-flash")
        prompt=("Return JSON only with action, confidence, reason. action must be RETRY, REMIND, ESCALATE, or STOP. "
                f"Failed payment: reason={case.failure_reason}, amount_INR={case.amount}, attempts={case.previous_attempts}, history_0_to_1={case.customer_history_score}. "
                "Never retry an expired card and never exceed three retries. Keep reason under 20 words.")
        raw=model.generate_content(prompt).text.strip().removeprefix("```json").removesuffix("```").strip()
        data=json.loads(raw); action=str(data["action"]).upper(); confidence=float(data["confidence"]); reason=str(data["reason"])
        if action not in ALLOWED or not 0<=confidence<=1 or len(reason)>180: raise ValueError("invalid model output")
        return action,confidence,reason
    except Exception as exc:
        log.warning("Gemini unavailable or invalid; deterministic fallback used: %s",type(exc).__name__)
        return fallback
