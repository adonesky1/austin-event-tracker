from src.admin.service import get_prompt_config
from src.llm.synthesis import SYNTHESIS_SYSTEM_PROMPT, SYNTHESIS_USER_PROMPT


async def get_effective_synthesis_prompts(session) -> tuple[str, str]:
    prompt = await get_prompt_config(session, "synthesis")
    if prompt is None:
        return SYNTHESIS_SYSTEM_PROMPT, SYNTHESIS_USER_PROMPT
    return prompt.system_prompt, prompt.user_prompt_template
