"""One question to Claude, one structured answer back. No tools.

Goes through the Claude Agent SDK, which signs in the way the claude CLI does:
CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY in the environment, or a logged-in claude on
this machine.
"""

import logging
from collections.abc import AsyncIterator

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

log = logging.getLogger(__name__)


async def _spoken(content: list[dict]) -> AsyncIterator[dict]:
    yield {"type": "user", "message": {"role": "user", "content": content}}


async def ask(prompt: str | list[dict], *, system: str, schema: dict, model: str | None) -> dict:
    """The answer, shaped like `schema`. `prompt` is text, or content blocks when a picture goes along."""
    options = ClaudeAgentOptions(
        tools=[],
        setting_sources=[],  # nothing from this machine's Claude settings leaks in
        system_prompt=system,
        output_format={"type": "json_schema", "schema": schema},
        max_turns=3,  # the structured answer is a tool call, so one turn is not enough
        model=model,
    )
    result: ResultMessage | None = None
    async for message in query(prompt=prompt if isinstance(prompt, str) else _spoken(prompt), options=options):
        if isinstance(message, ResultMessage):
            result = message
    if result is None or result.is_error or not result.structured_output:
        detail = (result.errors or result.result) if result else "no result"
        raise RuntimeError(f"claude gave no answer: {detail}")
    log.info("claude answered: turns=%s cost=%s", result.num_turns, result.total_cost_usd)
    return result.structured_output
