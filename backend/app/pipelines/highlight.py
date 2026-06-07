import logging

from app.llm import get_llm_provider
from app.models.segment import Segment

logger = logging.getLogger(__name__)


async def llm_pick_best_window(
    segments: list[Segment],
    candidates: list[tuple[int, int]],
) -> tuple[int, int] | None:
    """Send candidate window transcripts to LLM and ask for the best one."""
    if not candidates:
        return None

    provider = get_llm_provider()

    context_parts = []
    for idx, (start_i, end_i) in enumerate(candidates):
        window_segments = segments[start_i:end_i]
        start_time = window_segments[0].start_time
        end_time = window_segments[-1].end_time
        transcript = " ".join(s.transcript for s in window_segments)
        context_parts.append(
            f"[{idx}] {start_time:.1f}s-{end_time:.1f}s: {transcript}"
        )

    prompt = (
        "You are a video editor choosing the most engaging 45-60 second segment "
        "from a video. The following are candidate windows with their timestamps "
        "and transcripts. Pick the single best window that has the strongest hook, "
        "most emotional engagement, or most powerful statement.\n\n"
        + "\n".join(context_parts)
        + "\n\nReturn only the index number of the best window in square brackets, "
        "e.g. [2]. Nothing else."
    )

    result = await provider.generate(prompt, max_tokens=32)
    logger.info("LLM highlight pick: %s", result)

    try:
        idx = int(result.strip("[] \n"))
        if 0 <= idx < len(candidates):
            return candidates[idx]
    except (ValueError, IndexError):
        logger.warning("LLM returned invalid index: %s, falling back to top candidate", result)

    return candidates[0]
