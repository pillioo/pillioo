from __future__ import annotations

from dataclasses import dataclass

from app.db.models.chat_model import ChatMessage
from app.schemas.workflow import TicketState


WORKFLOW_EXPLANATION = "workflow_explanation"
RECALL_ACTION = "recall_action"
LABEL_SAFETY = "label_safety"
SHORTAGE_HANDLING = "shortage_handling"
EVIDENCE_GAP = "evidence_gap"
GENERAL_TICKET_QUESTION = "general_ticket_question"

TICKET_STATE_ONLY = "ticket_state_only"
RETRIEVAL_REQUIRED = "retrieval_required"
HYBRID = "hybrid"


_CONDENSE_SYSTEM_PROMPT = (
    "You resolve pharmacist follow-up questions into standalone questions. "
    "Given the conversation so far and a follow-up question, rewrite the "
    "follow-up as a standalone question that makes sense with no prior "
    "context, by resolving pronouns, ellipsis, and implicit references "
    "(e.g. \"what about that?\", \"is there an alternative?\") using the "
    "conversation. Do not answer the question. Do not add facts that are "
    "not implied by the conversation. Keep it to one sentence. Reply with "
    "only the rewritten question, nothing else."
)


@dataclass(frozen=True)
class ChatPlan:
    intent: str
    standalone_query: str
    answer_mode: str
    target_profile: str
    retrieved_evidence_scope: str


def build_chat_plan(
    *,
    user_query: str,
    recent_messages: list[ChatMessage],
    state: TicketState,
    resolved_followup: str | None = None,
) -> ChatPlan:
    intent = classify_intent(user_query)
    answer_mode = answer_mode_for_intent(intent)
    target_profile = target_profile_for_intent(intent, state)
    return ChatPlan(
        intent=intent,
        standalone_query=build_standalone_query(
            user_query=user_query,
            recent_messages=recent_messages,
            state=state,
            intent=intent,
            resolved_followup=resolved_followup,
        ),
        answer_mode=answer_mode,
        target_profile=target_profile,
        retrieved_evidence_scope=retrieved_evidence_scope_for_profile(target_profile),
    )


def reformulate_followup_query(
    *,
    user_query: str,
    recent_messages: list[ChatMessage],
    llm_client: object,
    model: str,
) -> str | None:
    """
    Best-effort LLM resolution of a multi-turn follow-up (pronouns, ellipsis,
    implicit references) into a standalone question, e.g. "is there an
    alternative?" -> "is there an alternative to midazolam for pediatric
    patients?". Returns None when there's no prior history to resolve
    against, or on any failure -- callers must fall back to the existing
    raw-last-message heuristic (build_standalone_query already does this
    when resolved_followup is None). This is an enhancement, not a hard
    dependency for chat to keep functioning.
    """
    if not recent_messages:
        return None

    history_text = "\n".join(
        f"{message.role}: {message.content}" for message in recent_messages if message.content
    )
    if not history_text.strip():
        return None

    try:
        completion = llm_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _CONDENSE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Conversation so far:\n{history_text}\n\n"
                        f"Follow-up question: {user_query}\n\n"
                        "Standalone question:"
                    ),
                },
            ],
            temperature=0,
        )
        resolved = completion.choices[0].message.content
        return resolved.strip() if resolved and resolved.strip() else None
    except Exception:
        return None


def classify_intent(user_query: str) -> str:
    query = user_query.casefold()

    if _contains_any(
        query,
        ["missing", "weak", "sufficient", "insufficient", "evidence gap", "근거 부족", "뭐가 부족", "무엇이 부족"],
    ):
        return EVIDENCE_GAP
    if _contains_any(query, ["왜", "why", "review", "routed", "route", "routing", "검토", "리뷰"]):
        return WORKFLOW_EXPLANATION
    if _contains_any(query, ["투여", "위험", "warning", "warnings", "contraindication", "boxed", "safety", "안전"]):
        return LABEL_SAFETY
    if _contains_any(query, ["대체", "대체약", "shortage", "substitute", "substitution", "부족", "품절"]):
        return SHORTAGE_HANDLING
    if _contains_any(query, ["조치", "격리", "보관", "회수", "quarantine", "hold", "recall", "required action", "procedure"]):
        return RECALL_ACTION
    return GENERAL_TICKET_QUESTION


def answer_mode_for_intent(intent: str) -> str:
    if intent == EVIDENCE_GAP:
        return TICKET_STATE_ONLY
    if intent == WORKFLOW_EXPLANATION:
        return HYBRID
    if intent in {RECALL_ACTION, LABEL_SAFETY, SHORTAGE_HANDLING}:
        return RETRIEVAL_REQUIRED
    return HYBRID


def target_profile_for_intent(intent: str, state: TicketState) -> str:
    if intent == RECALL_ACTION:
        return "recall_action"
    if intent == LABEL_SAFETY:
        return "label_safety"
    if intent == SHORTAGE_HANDLING:
        return "shortage_handling"
    if intent == WORKFLOW_EXPLANATION:
        return "workflow_explanation"
    if intent == EVIDENCE_GAP:
        return "evidence_gap"
    if state.event_type:
        return f"{state.event_type.value}_general"
    return "general"


def build_standalone_query(
    *,
    user_query: str,
    recent_messages: list[ChatMessage],
    state: TicketState,
    intent: str,
    resolved_followup: str | None = None,
) -> str:
    event = state.event_normalized
    context_terms = [
        state.event_type.value if state.event_type else None,
        event.drug_name if event else None,
        event.recall_number if event and not event.recall_number_is_fallback else None,
        event.ndc if event else None,
        event.lot if event else None,
        state.classification.value if state.classification else None,
    ]
    # LLM-resolved standalone question (coreference/ellipsis resolved against
    # conversation history) takes priority over the raw last-message
    # heuristic, when available -- see reformulate_followup_query.
    topic = resolved_followup or _recent_user_topic(recent_messages)
    intent_terms = {
        RECALL_ACTION: "required actions quarantine storage recall procedure",
        LABEL_SAFETY: "label safety warnings contraindications boxed warning administration risk",
        SHORTAGE_HANDLING: "shortage substitution alternative escalation procedure",
        WORKFLOW_EXPLANATION: "workflow routing review decision evidence sufficiency",
        EVIDENCE_GAP: "evidence sufficiency missing weak sources citations",
    }.get(intent)

    parts = [term for term in context_terms if term]
    if topic:
        parts.append(topic)
    if intent_terms:
        parts.append(intent_terms)
    parts.append(user_query.strip())
    return _dedupe_words(" ".join(parts))


def retrieved_evidence_scope_for_profile(target_profile: str) -> str:
    return {
        "recall_action": "recall_action",
        "label_safety": "label_safety",
        "shortage_handling": "shortage_handling",
        "workflow_explanation": "workflow_routing_and_ticket_evidence",
        "evidence_gap": "ticket_state",
    }.get(target_profile, "general_ticket_evidence")


def _recent_user_topic(recent_messages: list[ChatMessage]) -> str | None:
    for message in reversed(recent_messages):
        if message.role == "user" and message.content:
            content = message.content.strip()
            if content:
                return content[:160]
    return None


def _contains_any(value: str, needles: list[str]) -> bool:
    return any(needle in value for needle in needles)


def _dedupe_words(value: str) -> str:
    seen: set[str] = set()
    words: list[str] = []
    for word in value.split():
        key = word.casefold()
        if key in seen:
            continue
        seen.add(key)
        words.append(word)
    return " ".join(words)
