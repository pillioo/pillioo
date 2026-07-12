from __future__ import annotations

from types import SimpleNamespace

from app.chat.planner import _CONDENSE_SYSTEM_PROMPT, reformulate_followup_query
from app.db.models.chat_model import ChatMessage


class _FakeCompletionMessage:
    def __init__(self, content: str | None) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str | None) -> None:
        self.message = _FakeCompletionMessage(content)


class _FakeCompletions:
    def __init__(self, *, response: str | None = "resolved standalone question", raise_error: bool = False) -> None:
        self.response = response
        self.raise_error = raise_error
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.raise_error:
            raise RuntimeError("LLM call failed")
        return SimpleNamespace(choices=[_FakeChoice(self.response)])


class _FakeLLMClient:
    def __init__(self, **kwargs) -> None:
        self.completions = _FakeCompletions(**kwargs)
        self.chat = SimpleNamespace(completions=self.completions)


def _message(role: str, content: str) -> ChatMessage:
    return ChatMessage(role=role, content=content)


def test_reformulate_followup_query_returns_none_when_no_history():
    client = _FakeLLMClient()

    result = reformulate_followup_query(
        user_query="what about that?",
        recent_messages=[],
        llm_client=client,
        model="gpt-test",
    )

    assert result is None
    assert client.completions.calls == []


def test_reformulate_followup_query_returns_none_when_history_has_no_content():
    client = _FakeLLMClient()
    history = [_message("user", ""), _message("assistant", "")]

    result = reformulate_followup_query(
        user_query="what about that?",
        recent_messages=history,
        llm_client=client,
        model="gpt-test",
    )

    assert result is None
    assert client.completions.calls == []


def test_reformulate_followup_query_returns_resolved_text_on_success():
    client = _FakeLLMClient(response="Is there an alternative to midazolam for pediatric patients?")
    history = [
        _message("user", "Is midazolam affected by this recall?"),
        _message("assistant", "Yes, lot LOT-A is affected."),
    ]

    result = reformulate_followup_query(
        user_query="is there an alternative?",
        recent_messages=history,
        llm_client=client,
        model="gpt-test",
    )

    assert result == "Is there an alternative to midazolam for pediatric patients?"
    assert len(client.completions.calls) == 1
    call = client.completions.calls[0]
    assert call["messages"][0]["content"] == _CONDENSE_SYSTEM_PROMPT
    assert "Is midazolam affected by this recall?" in call["messages"][1]["content"]
    assert "is there an alternative?" in call["messages"][1]["content"]


def test_reformulate_followup_query_returns_none_on_empty_response():
    client = _FakeLLMClient(response="   ")
    history = [_message("user", "prior question")]

    result = reformulate_followup_query(
        user_query="follow up",
        recent_messages=history,
        llm_client=client,
        model="gpt-test",
    )

    assert result is None


def test_reformulate_followup_query_returns_none_when_llm_raises():
    client = _FakeLLMClient(raise_error=True)
    history = [_message("user", "prior question")]

    result = reformulate_followup_query(
        user_query="follow up",
        recent_messages=history,
        llm_client=client,
        model="gpt-test",
    )

    assert result is None
