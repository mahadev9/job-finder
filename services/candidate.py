from pathlib import Path

import aiofiles

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

_templates_cache: tuple[str, str] | None = None


async def load_profile_cv() -> tuple[str, str]:
    """Load and cache the candidate's profile and CV templates."""
    global _templates_cache
    if _templates_cache is not None:
        return _templates_cache
    async with aiofiles.open(_TEMPLATES_DIR / "profile.md") as f:
        profile = await f.read()
    async with aiofiles.open(_TEMPLATES_DIR / "cv.md") as f:
        cv = await f.read()
    _templates_cache = (profile, cv)
    return _templates_cache
