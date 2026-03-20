from app.core.prompt_loader import load_prompt
from app.core.schemas import PromptReference

KAGUYA_SYSTEM_PROMPT = load_prompt(PromptReference("system/kaguya/production.md"))
