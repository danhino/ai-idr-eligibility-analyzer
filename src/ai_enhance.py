"""
Optional AI enhancement for ERA parsing and validation.

Supports OpenAI, Anthropic (Claude), and Ollama providers.
All data is redacted (PHI stripped) before being sent to external APIs.
"""
from typing import Optional, Dict, List, Any
import json
import sys
import re
from pathlib import Path

# Ensure parent directory is in path for imports
_parent_dir = Path(__file__).parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

from src.utils.logging import logger
from src.utils.redaction import redact_text, redact_name, redact_id


def _get_config():
    """Get current AI config values (re-reads after settings changes)."""
    from src import config
    return {
        "enabled": config.AI_ENABLED,
        "provider": config.AI_PROVIDER,
        "model": config.AI_MODEL,
        "timeout": config.AI_TIMEOUT,
        "openai_key": config.OPENAI_API_KEY,
        "anthropic_key": config.ANTHROPIC_API_KEY,
        "ollama_url": config.OLLAMA_BASE_URL,
    }


def _redact_segment(segment: str) -> str:
    """Redact PHI from a single ERA segment before sending to AI."""
    seg_id = segment.split("*")[0].split("~")[0].strip() if segment else ""

    # NM1 segments contain patient/provider names — redact name fields
    if seg_id == "NM1":
        parts = segment.split("*")
        if len(parts) > 3:
            parts[3] = redact_name(parts[3])  # last name
        if len(parts) > 4:
            parts[4] = redact_name(parts[4])  # first name
        # Redact identifier (e.g. SSN, member ID) in position 9
        if len(parts) > 9:
            parts[9] = redact_id(parts[9])
        return "*".join(parts)

    # CLP segments contain claim IDs and patient account numbers
    if seg_id == "CLP":
        parts = segment.split("*")
        if len(parts) > 1:
            parts[1] = redact_id(parts[1])  # patient control number
        if len(parts) > 7:
            parts[7] = redact_id(parts[7])  # payer claim control number
        return "*".join(parts)

    # REF segments can contain subscriber IDs, SSNs, etc.
    if seg_id == "REF":
        parts = segment.split("*")
        if len(parts) > 2:
            parts[2] = redact_id(parts[2])
        return "*".join(parts)

    # For all other segments, apply general-purpose text redaction
    return redact_text(segment)


def _redact_segments(segments: List[str]) -> List[str]:
    """Redact PHI from a list of ERA segments."""
    return [_redact_segment(s) for s in segments]


def _redact_service_line(svc: Dict[str, Any]) -> Dict[str, Any]:
    """Redact PHI from a service line dict before sending to AI."""
    redacted = {}
    for key, value in svc.items():
        if key == "description" and isinstance(value, str):
            redacted[key] = redact_text(value)
        elif key in ("patient_name", "patient_id", "claim_id", "member_id"):
            redacted[key] = redact_id(str(value)) if value else value
        else:
            redacted[key] = value
    return redacted


def is_available() -> bool:
    """Check if AI enhancement is available."""
    return _get_config()["enabled"]


def get_provider_name() -> str:
    """Return the display name of the active AI provider."""
    names = {"openai": "OpenAI", "anthropic": "Claude (Anthropic)", "ollama": "Ollama"}
    return names.get(_get_config()["provider"], "OpenAI")


def _chat(system: str, user: str, max_tokens: Optional[int] = None) -> Optional[str]:
    """Send a chat completion request via the configured AI provider."""
    cfg = _get_config()
    provider = cfg["provider"]

    if provider == "anthropic":
        return _chat_anthropic(system, user, cfg, max_tokens)
    if provider == "ollama":
        return _chat_ollama(system, user, cfg, max_tokens)
    return _chat_openai(system, user, cfg, max_tokens)


def _chat_openai(system: str, user: str, cfg: dict, max_tokens: Optional[int] = None) -> Optional[str]:
    from openai import OpenAI
    client = OpenAI(api_key=cfg["openai_key"])
    kwargs: Dict[str, Any] = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "timeout": cfg["timeout"],
        "temperature": 0.1,
    }
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content


def _chat_anthropic(system: str, user: str, cfg: dict, max_tokens: Optional[int] = None) -> Optional[str]:
    from anthropic import Anthropic
    client = Anthropic(api_key=cfg["anthropic_key"])
    response = client.messages.create(
        model=cfg["model"],
        max_tokens=max_tokens or 4096,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text


def _chat_ollama(system: str, user: str, cfg: dict, max_tokens: Optional[int] = None) -> Optional[str]:
    from openai import OpenAI
    client = OpenAI(
        base_url=f"{cfg['ollama_url'].rstrip('/')}/v1",
        api_key="ollama",
    )
    kwargs: Dict[str, Any] = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.1,
    }
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content


def _parse_json_response(content: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from an AI response, handling markdown code blocks."""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
    return None


def summarize_segments(segments: List[str]) -> Optional[Dict[str, Any]]:
    """Use AI to summarize and validate ERA segments (PHI is redacted before sending)."""
    if not is_available():
        return None

    try:
        redacted = _redact_segments(segments[:50])

        prompt = f"""You are an expert in medical billing and ANSI 835 ERA files.
Analyze the following ERA segments and provide:
1. Identify any malformed segments
2. Suggest corrections for delimiter issues
3. Extract key information (RARC, CAS, CPT codes, amounts, dates)

Segments:
{chr(10).join(redacted)}

Respond in JSON format with:
{{
    "malformed_segments": ["list of problematic segments"],
    "suggestions": ["list of corrections"],
    "extracted_info": {{
        "cpt_codes": ["list"],
        "dates": ["list"],
        "amounts": ["list"]
    }}
}}"""

        content = _chat(
            "You are a medical billing expert specializing in ANSI 835 ERA files.",
            prompt,
        )
        if not content:
            return None

        parsed = _parse_json_response(content)
        return parsed if parsed else {"raw_response": content}

    except Exception as e:
        logger.warning(f"AI enhancement failed: {e}")
        return None


def validate_line_items(service_lines: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
    """Use AI to validate and enhance service line items (PHI is redacted before sending)."""
    if not is_available():
        return None

    try:
        redacted = [_redact_service_line(svc) for svc in service_lines[:20]]

        prompt = f"""You are an expert in medical billing. Validate and enhance the following service line items:
1. Confirm CPT codes match descriptions
2. Map free-text denial notes to CAS/RARC codes
3. Suggest missing modifiers if appropriate

Service Lines:
{json.dumps(redacted, indent=2)}

Respond in JSON format:
{{
    "validated_lines": [
        {{
            "index": 0,
            "cpt_suggestion": "99283",
            "cas_mappings": ["CO-45"],
            "rarc_mappings": ["MA130"],
            "notes": "validation notes"
        }}
    ]
}}"""

        content = _chat("You are a medical billing expert.", prompt)
        if not content:
            return None
        return _parse_json_response(content)

    except Exception as e:
        logger.warning(f"AI validation failed: {e}")
        return None


def infer_cpt_from_description(description: str) -> Optional[str]:
    """Use AI to infer CPT code from procedure description (PHI is redacted before sending)."""
    if not is_available() or not description:
        return None

    try:
        redacted_desc = redact_text(description)

        prompt = f"""Given this medical procedure description, suggest the most likely CPT code (5 digits).

Description: {redacted_desc}

Respond with ONLY the 5-digit CPT code, nothing else."""

        content = _chat(
            "You are a medical billing expert. Respond with only the CPT code.",
            prompt,
            max_tokens=10,
        )
        if content:
            code = content.strip()
            if re.match(r'^\d{5}$', code):
                return code

    except Exception as e:
        logger.warning(f"AI CPT inference failed: {e}")

    return None

