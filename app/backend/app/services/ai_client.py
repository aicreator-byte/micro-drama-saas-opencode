"""
AI Client Service for LLM calls with provider fallback.
Reads provider configuration from settings (DB), API keys from environment variables.
"""
import os
import httpx
import logging
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class AIProvider:
    id: str
    provider: str
    model: str
    key_env: str
    enabled: bool
    priority: int


@dataclass
class AIResponse:
    content: str
    provider_id: str
    model: str
    usage: Optional[Dict[str, Any]] = None


class AIClientError(Exception):
    """Raised when all providers fail."""
    def __init__(self, message: str, errors: List[Dict[str, Any]]):
        super().__init__(message)
        self.errors = errors


class AIClient:
    """Client for calling LLM APIs with provider fallback."""

    def __init__(self, providers: List[AIProvider]):
        self.providers = sorted([p for p in providers if p.enabled], key=lambda x: x.priority)

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4000,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> AIResponse:
        """
        Call chat completions with fallback across enabled providers.
        Raises AIClientError if all providers fail.
        """
        errors = []

        for provider in self.providers:
            # .env tidak masuk os.environ — fallback ke Settings (.env).
            api_key = os.getenv(provider.key_env) or getattr(
                settings, provider.key_env, None)
            if not api_key and provider.provider != "mock":
                errors.append({
                    "provider_id": provider.id,
                    "provider": provider.provider,
                    "model": provider.model,
                    "error": f"API key not found in env var {provider.key_env}",
                })
                logger.warning(f"Provider {provider.id} ({provider.provider}) skipped: {errors[-1]['error']}")
                continue

            try:
                response = await self._call_provider(provider, api_key, messages, temperature, max_tokens, response_format)
                logger.info(f"Successfully called provider {provider.id} ({provider.provider})")
                return response
            except Exception as e:
                error_info = {
                    "provider_id": provider.id,
                    "provider": provider.provider,
                    "model": provider.model,
                    "error": str(e),
                }
                errors.append(error_info)
                logger.warning(f"Provider {provider.id} ({provider.provider}) failed: {e}")
                continue

        raise AIClientError("All AI providers failed", errors)

    async def _call_provider(
        self,
        provider: AIProvider,
        api_key: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        response_format: Optional[Dict[str, Any]],
    ) -> AIResponse:
        """Call a specific provider's API."""
        if provider.provider == "nvidia":
            return await self._call_nvidia(provider, api_key, messages, temperature, max_tokens, response_format)
        elif provider.provider == "mock":
            return await self._call_mock(provider, messages, temperature, max_tokens, response_format)
        else:
            raise ValueError(f"Unknown provider: {provider.provider}")

    async def _call_nvidia(
        self,
        provider: AIProvider,
        api_key: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        response_format: Optional[Dict[str, Any]],
    ) -> AIResponse:
        """Call NVIDIA NIM API with robust proxy handling."""
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": provider.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if response_format:
            payload["response_format"] = response_format

        proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
        proxy_url = None
        if proxy:
            try:
                proxy_url = httpx.Proxy(proxy)
            except Exception as e:
                logger.warning(f"Invalid proxy URL '{proxy}': {e}. Falling back to no proxy.")
                proxy_url = None

        async with httpx.AsyncClient(timeout=120.0, trust_env=False, proxy=proxy_url, verify=False) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        if not data.get("choices") or not data["choices"][0].get("message", {}).get("content"):
            raise ValueError("Empty response from NVIDIA API")

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage")

        return AIResponse(
            content=content,
            provider_id=provider.id,
            model=provider.model,
            usage=usage,
        )

    async def _call_mock(
        self,
        provider: AIProvider,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        response_format: Optional[Dict[str, Any]],
    ) -> AIResponse:
        """Call mock provider for testing - returns deterministic JSON responses."""
        user_content = messages[-1]["content"] if messages else ""
        lower_content = user_content.lower()
        
        # Scene Engine prompts (must come before story engine to avoid "episode" collision)
        if "refine the following scene" in lower_content:
            content = json.dumps({
                "refined_output": {"scenes": [{"scene_number": 1, "title": "Refined Scene"}]},
                "refinement_notes": "Refined scene based on feedback",
                "refined_at": "2024-01-01T00:00:00"
            })
        elif "design physical action choreography" in lower_content:
            content = json.dumps({
                "scene_id": "test-scene",
                "action_beats": [
                    {"beat_number": 1, "description": "Action beat 1", "characters": ["Character A"], "props": ["Prop 1"], "choreography_notes": "Notes 1"},
                    {"beat_number": 2, "description": "Action beat 2", "characters": ["Character A"], "props": ["Prop 2"], "choreography_notes": "Notes 2"}
                ],
                "generated_at": "2024-01-01T00:00:00"
            })
        elif "write natural, character-driven dialogue" in lower_content:
            content = json.dumps({
                "scene_id": "test-scene",
                "dialogue_blocks": [
                    {"character": "Character A", "line": "Line 1", "parenthetical": "(neutral)", "action": "Action 1", "beat_number": 1},
                    {"character": "Character B", "line": "Line 2", "parenthetical": "(happy)", "action": "Action 2", "beat_number": 2}
                ],
                "generated_at": "2024-01-01T00:00:00"
            })
        elif "create a detailed shot list" in lower_content:
            content = json.dumps({
                "scene_id": "test-scene",
                "total_shots": 10,
                "shots": [
                    {
                        "shot_number": i,
                        "scene_id": "test-scene",
                        "shot_type": "MEDIUM",
                        "camera_angle": "EYE_LEVEL",
                        "camera_movement": "STATIC",
                        "description": f"Shot {i} description",
                        "characters_in_shot": ["Character A"],
                        "estimated_duration": "3-5 seconds",
                        "visual_notes": "Visual notes",
                        "audio_cues": "Audio cues"
                    }
                    for i in range(1, 11)
                ],
                "generated_at": "2024-01-01T00:00:00"
            })
        elif "break down this episode" in lower_content:
            content = json.dumps({
                "episode_id": "test-episode",
                "total_scenes": 5,
                "scenes": [
                    {
                        "scene_number": i,
                        "title": f"Scene {i}",
                        "description": f"Description for scene {i}",
                        "location": "Location 1",
                        "characters": ["Character A", "Character B"],
                        "estimated_duration": "2-3 minutes",
                        "beat_type": "setup",
                        "key_dialogue_hint": "Key dialogue",
                        "action_summary": "Action summary"
                    }
                    for i in range(1, 6)
                ],
                "generated_at": "2024-01-01T00:00:00"
            })
        # Auto-Generate prompts (checked before story-engine branches:
        # the bible prompt mentions episodes, the cast prompt mentions
        # characters, and the video-prompt prompt mentions episodes).
        elif "create a complete series bible" in lower_content:
            content = json.dumps({
                "genre": "Romance",
                "premise": "Mock premise for the series",
                "main_plot": "Mock main plot",
                "subplots": ["Mock subplot 1: description", "Mock subplot 2: description"],
                "character_relationships": "Mock character relationships",
                "world_settings": "Mock world settings",
                "tone_and_visual_style": "Mock tone",
                "ending_direction": "Mock ending",
                "episode_structure": "Mock episode structure",
            })
        elif "create the main cast" in lower_content:
            content = json.dumps({
                "characters": [
                    {
                        "name": f"Mock Character {i}",
                        "role": "protagonist" if i == 1 else ("antagonist" if i == 2 else "supporting"),
                        "age": str(20 + i),
                        "gender": "female" if i % 2 else "male",
                        "ethnicity": "Mock ethnicity",
                        "background": f"Background for mock character {i}",
                        "motivations": f"Motivation {i}",
                        "fears": f"Fear {i}",
                        "personality_traits": ["brave", "stubborn", "kind"],
                    }
                    for i in range(1, 6)
                ]
            })
        elif "write one video generation prompt for each episode" in lower_content:
            import re as _re2
            # The prompt lists episodes as "- Episode 6: ..." (capital E),
            # so match against the lowercased text — otherwise the numbers
            # are never found and the mock falls back to episodes 1-5,
            # which breaks chunked prompt generation for >5 episodes.
            _nums = sorted({int(n) for n in _re2.findall(r"episode (\d+):", lower_content)})
            if not _nums:
                _nums = [1, 2, 3, 4, 5]
            content = json.dumps({
                "prompts": [
                    {
                        "episode_number": n,
                        "title": f"Video prompt for episode {n}",
                        "prompt_text": f"Cinematic vertical micro-drama scene for episode {n}, same cast and look throughout.",
                        "negative_prompt": "blurry, low quality, distorted faces",
                    }
                    for n in _nums
                ]
            })
        # Story Engine prompts
        elif "detailed outline for one episode" in lower_content:
            # GENERATE_EPISODE: single-episode outline (audit F-18).
            import re as _re
            _m = _re.search(r"\(episode (\d+)\)", user_content)
            _num = int(_m.group(1)) if _m else 1
            content = json.dumps({
                "series_bible_id": "test-series-bible",
                "episode_number": _num,
                "title": f"Episode {_num}",
                "logline": f"Logline for episode {_num}",
                "synopsis": f"Synopsis for episode {_num}",
                "key_beats": ["Setup", "Inciting Incident", "Rising Action", "Climax", "Resolution"],
                "character_focus": ["Character A", "Character B"],
                "generated_at": "2024-01-01T00:00:00"
            })
        elif "character arc" in lower_content:
            content = json.dumps({
                "arcs": [
                    {
                        "character_id": "test-char-1",
                        "character_name": "Character A",
                        "arc_summary": "Transformation summary",
                        "key_moments": [
                            {"episode": 1, "moment": "Moment 1"},
                            {"episode": 5, "moment": "Moment 2"},
                            {"episode": 10, "moment": "Moment 3"},
                            {"episode": 15, "moment": "Moment 4"},
                            {"episode": 20, "moment": "Moment 5"}
                        ],
                        "emotional_journey": "Stage1 -> Stage2 -> Stage3 -> Stage4 -> Stage5"
                    }
                ]
            })
        elif "world building" in lower_content:
            content = json.dumps({
                "series_bible_id": "test-series-bible",
                "locations": [
                    {"name": "Location 1", "type": "urban", "description": "Description"},
                    {"name": "Location 2", "type": "rural", "description": "Description"},
                    {"name": "Location 3", "type": "office", "description": "Description"},
                ],
                "factions": [{"name": "Faction 1", "type": "government", "description": "Description"}],
                "technology": [{"name": "Tech 1", "description": "Description"}],
                "culture": [{"name": "Culture 1", "description": "Description"}],
                "history": [{"event": "Event 1", "year": "2000", "description": "Description"}],
                "generated_at": "2024-01-01T00:00:00"
            })
        elif "refine" in lower_content:
            content = json.dumps({
                "refined_output": {"episodes": [{"episode_number": 1, "title": "Refined Episode"}]},
                "refinement_notes": "Refined based on feedback",
                "refined_at": "2024-01-01T00:00:00"
            })
        elif "story outline" in lower_content or "episode-by-episode outline" in lower_content:
            content = json.dumps({
                "series_bible_id": "test-series-bible",
                "total_episodes": 5,
                "episodes": [
                    {
                        "episode_number": i,
                        "title": f"Episode {i}",
                        "logline": f"Logline for episode {i}",
                        "synopsis": f"Synopsis for episode {i}",
                        "key_beats": ["Setup", "Inciting Incident", "Rising Action", "Climax", "Resolution"],
                        "character_focus": ["Character A", "Character B"]
                    }
                    for i in range(1, 6)
                ],
                "generated_at": "2024-01-01T00:00:00"
            })
        else:
            content = json.dumps({"result": "mock response", "generated_at": "2024-01-01T00:00:00"})

        return AIResponse(
            content=content,
            provider_id=provider.id,
            model=provider.model,
            usage={"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
        )

    @classmethod
    def from_settings(cls, settings_providers: List[Dict[str, Any]]) -> "AIClient":
        """Create AIClient from settings JSON."""
        providers = [
            AIProvider(
                id=p["id"],
                provider=p["provider"],
                model=p["model"],
                key_env=p["key_env"],
                enabled=p.get("enabled", True),
                priority=p.get("priority", 999),
            )
            for p in settings_providers
        ]
        return cls(providers)


async def get_ai_client(db) -> AIClient:
    """Get AI client configured from database settings."""
    from app.models.settings import AppSettings
    from sqlalchemy import select

    result = await db.execute(select(AppSettings).limit(1))
    settings = result.scalar_one_or_none()

    if not settings or not settings.ai_providers:
        # Default to NVIDIA provider only (no mock fallback)
        default_providers = [
            {
                "id": "nvidia-nemotron-550b",
                "provider": "nvidia",
                "model": "nvidia/nemotron-3-ultra-550b-a55b",
                "key_env": "NVIDIA_API_KEY",
                "enabled": True,
                "priority": 1,
            }
        ]
        return AIClient.from_settings(default_providers)

    return AIClient.from_settings(settings.ai_providers)