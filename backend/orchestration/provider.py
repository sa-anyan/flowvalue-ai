"""OpenAI Responses adapter for one bounded engineering proposal (no tool execution)."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

from backend.revenue.advisor import NoRedirects, RevenueAIError, strict_object


class EngineeringProvider:
    def __init__(self):
        self.model = os.environ.get("OPENAI_MODEL", "").strip()
        self._key = os.environ.get("OPENAI_API_KEY", "").strip()
        if (
            os.environ.get("AI_ENABLED", "false").lower() != "true"
            or not self.model
            or not self._key
        ):
            raise RevenueAIError(
                "Configure server-side AI_ENABLED, OPENAI_MODEL and OPENAI_API_KEY"
            )

    def generate(self, *, instructions, context, schema):
        from .ai_audit import audited

        return audited("call", self.model, instructions, context,
                       lambda: self._generate(instructions=instructions, context=context, schema=schema))

    def _generate(self, *, instructions, context, schema):
        payload = {
            "model": self.model,
            "instructions": instructions,
            "input": json.dumps(context),
            "store": False,
            "max_output_tokens": (3500 if context.get("specialist") else
                                  8000 if context.get("requested_sections") == ["equipment", "capex"] else 12000),
            "reasoning": {"effort": "low"},
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "flowvalue_engineering_plan",
                    "schema": schema,
                    "strict": True,
                }
            },
        }
        request = Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": "Bearer " + self._key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with build_opener(NoRedirects()).open(request, timeout=90) as response:
                raw = response.read(524289)
            if len(raw) > 524288:
                raise ValueError("Response limit")
            result = json.loads(raw, object_pairs_hook=strict_object)
            if result.get("status") != "completed":
                raise RevenueAIError(
                    "OpenAI response incomplete: "
                    + str(result.get("incomplete_details", {}).get("reason", "unknown"))
                )
            texts = []
            for message in result.get("output", []):
                if message.get("type") == "reasoning":
                    continue
                if message.get("type") != "message":
                    raise ValueError("Unexpected action")
                for item in message.get("content", []):
                    if item.get("type") != "output_text":
                        raise ValueError("Refused or unsupported response")
                    texts.append(item["text"])
            return json.loads("".join(texts), object_pairs_hook=strict_object)
        except RevenueAIError:
            raise
        except HTTPError as exc:
            try:
                code = json.loads(exc.read(20000)).get("error", {}).get("code")
                code = str(code) if isinstance(code, (str, int)) else "request_rejected"
                code = "".join(c for c in code if c.isalnum() or c == "_")[:80]
            except (ValueError, TypeError):
                code = "request_rejected"
            raise RevenueAIError(f"OpenAI HTTP {exc.code}: {code}") from None
        except TimeoutError:
            raise RevenueAIError(
                "OpenAI response timed out; workbook interpretation and prior stages retained"
            ) from None
        except URLError as exc:
            raise RevenueAIError(
                "OpenAI network error: " + type(exc.reason).__name__
            ) from None
        except Exception:  # noqa: BLE001 -- never leak provider payloads or credentials
            raise RevenueAIError(
                "Engineering provider unavailable or proposal incomplete"
            ) from None

    def research(self, *, instructions, context):
        """Explicit research only: bounded hosted web searches; no browser/code tools."""
        from .ai_audit import audited

        return audited("research", self.model, instructions, context,
                       lambda: self._research(instructions=instructions, context=context))

    def _research(self, *, instructions, context):
        payload = {'model': self.model, 'store': False, 'instructions': instructions,
                   'input': json.dumps(context), 'tools': [{'type': 'web_search', 'search_context_size': 'low'}],
                   'tool_choice': 'required', 'max_tool_calls': 3,
                   'include': ['web_search_call.action.sources'], 'max_output_tokens': 4500,
                   'reasoning': {'effort': 'low'}}
        request = Request('https://api.openai.com/v1/responses', data=json.dumps(payload).encode(),
                          headers={'Authorization': 'Bearer ' + self._key, 'Content-Type': 'application/json'}, method='POST')
        try:
            with build_opener(NoRedirects()).open(request, timeout=120) as response:
                raw = response.read(1048577)
            if len(raw) > 1048576:
                raise ValueError('Research response exceeds limit')
            result = json.loads(raw)
            if result.get('status') != 'completed':
                raise ValueError('Research response incomplete')
            return result
        except Exception as exc:  # noqa: BLE001 -- keep secrets/provider bodies out of API errors
            raise RevenueAIError('Research unavailable (' + type(exc).__name__ + '); existing calculations retained') from None
