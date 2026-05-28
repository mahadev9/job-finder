import logging
from typing import Any
from uuid import UUID

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import LLMResult

from database.core import SessionLocal
from database.models.token_usage import TokenUsage

logger = logging.getLogger("job-finder")


class UsageCallbackHandler(AsyncCallbackHandler):
    def __init__(self, pipeline: str | None = None) -> None:
        self.pipeline = pipeline

    async def on_llm_end(
        self, response: LLMResult, *, run_id: UUID, **kwargs: Any
    ) -> None:
        try:
            input_tokens = output_tokens = total_tokens = reasoning_tokens = 0
            model = "unknown"

            # Primary: usage_metadata + response_metadata on AIMessage (langchain-core 0.3+)
            for gen_list in response.generations:
                for gen in gen_list:
                    msg = getattr(gen, "message", None)
                    if msg is None:
                        continue

                    um = getattr(msg, "usage_metadata", None) or {}
                    input_tokens += um.get("input_tokens") or 0
                    output_tokens += um.get("output_tokens") or 0
                    total_tokens += um.get("total_tokens") or 0
                    reasoning_tokens += (
                        (um.get("output_token_details") or {}).get("reasoning") or 0
                    )

                    if model == "unknown":
                        rm = getattr(msg, "response_metadata", None) or {}
                        model = rm.get("model") or rm.get("model_name") or "unknown"

            # Fallback: llm_output dict (provider-specific keys)
            if total_tokens == 0:
                llm_out = response.llm_output or {}
                usage = llm_out.get("token_usage") or llm_out.get("usage") or {}
                input_tokens = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
                output_tokens = (
                    usage.get("completion_tokens") or usage.get("output_tokens") or 0
                )
                total_tokens = usage.get("total_tokens") or (input_tokens + output_tokens)
                reasoning_tokens = (
                    (usage.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0
                )
                if model == "unknown":
                    model = llm_out.get("model_name") or llm_out.get("model") or "unknown"

            async with SessionLocal() as session:
                session.add(
                    TokenUsage(
                        request_id=str(run_id),
                        model=model,
                        pipeline=self.pipeline,
                        input_tokens=int(input_tokens),
                        output_tokens=int(output_tokens),
                        total_tokens=int(total_tokens),
                        reasoning_tokens=int(reasoning_tokens),
                    )
                )
                await session.commit()
        except Exception:
            logger.warning("Failed to record token usage", exc_info=True)
