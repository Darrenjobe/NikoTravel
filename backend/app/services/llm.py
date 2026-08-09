"""LLM abstraction. Anthropic (Claude) is the primary implementation and the
only one wired for tool use + structured output; OpenAI is a plain-chat
fallback kept behind the same interface so a provider swap is one env var
(for the concierge path — journal extraction and jobs require Anthropic in V1).
"""
from __future__ import annotations

import json
from typing import Any

from app import config


class LLMError(RuntimeError):
    pass


class AnthropicLLM:
    def __init__(self) -> None:
        import anthropic

        self._sdk = anthropic
        self.client = anthropic.Anthropic()

    def chat_with_tools(
        self,
        model: str,
        system: str,
        messages: list[dict],
        tools: list[dict],
        execute_tool,
        max_iterations: int = 3,
    ) -> dict:
        """Manual tool loop. execute_tool(name, input) -> str.
        Returns {"text": str, "tool_calls": [{"name", "input", "result"}]}.
        """
        msgs = list(messages)
        tool_calls: list[dict] = []
        response = None
        for _ in range(max_iterations + 1):
            response = self.client.messages.create(
                model=model,
                max_tokens=4096,
                system=system,
                tools=tools or self._sdk.NOT_GIVEN,
                messages=msgs,
            )
            if response.stop_reason == "refusal":
                raise LLMError("The model declined this request.")
            if response.stop_reason != "tool_use":
                break
            msgs.append({"role": "assistant", "content": response.content})
            results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = execute_tool(block.name, block.input)
                    tool_calls.append(
                        {"name": block.name, "input": block.input, "result": result}
                    )
                    results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )
            msgs.append({"role": "user", "content": results})
        text = "".join(b.text for b in response.content if b.type == "text")
        return {"text": text, "tool_calls": tool_calls}

    def complete(self, model: str, system: str, prompt: str, max_tokens: int = 4096) -> str:
        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        if response.stop_reason == "refusal":
            raise LLMError("The model declined this request.")
        return "".join(b.text for b in response.content if b.type == "text")

    def extract_json(self, model: str, system: str, prompt: str, schema: dict) -> dict:
        """Structured extraction — guaranteed-valid JSON via output_config.format."""
        response = self.client.messages.create(
            model=model,
            max_tokens=4096,
            system=system,
            output_config={"format": {"type": "json_schema", "schema": schema}},
            messages=[{"role": "user", "content": prompt}],
        )
        if response.stop_reason == "refusal":
            raise LLMError("The model declined this request.")
        text = next(b.text for b in response.content if b.type == "text")
        return json.loads(text)


class OpenAILLM:
    """Fallback provider: plain chat only (concierge without tool use)."""

    def __init__(self) -> None:
        from openai import OpenAI

        self.client = OpenAI()

    def chat_with_tools(self, model, system, messages, tools, execute_tool, max_iterations=3):
        text_messages = [{"role": "system", "content": system}] + [
            {"role": m["role"], "content": m["content"] if isinstance(m["content"], str) else ""}
            for m in messages
        ]
        r = self.client.chat.completions.create(
            model=config.OPENAI_MODEL, messages=text_messages
        )
        return {"text": r.choices[0].message.content or "", "tool_calls": []}

    def complete(self, model, system, prompt, max_tokens=4096):
        r = self.client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        return r.choices[0].message.content or ""

    def extract_json(self, model, system, prompt, schema):
        r = self.client.chat.completions.create(
            model=config.OPENAI_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system + "\nRespond with JSON only."},
                {"role": "user", "content": prompt},
            ],
        )
        return json.loads(r.choices[0].message.content or "{}")


_instance: Any = None


def get_llm():
    global _instance
    if _instance is None:
        _instance = OpenAILLM() if config.LLM_PROVIDER == "openai" else AnthropicLLM()
    return _instance
