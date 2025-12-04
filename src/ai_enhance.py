"""
Optional OpenAI enhancement for ERA parsing and validation.
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

from src.config import AI_ENABLED, OPENAI_API_KEY, AI_MODEL, AI_TIMEOUT
from src.utils.logging import logger


def is_available() -> bool:
    """Check if AI enhancement is available."""
    return AI_ENABLED


def summarize_segments(segments: List[str]) -> Optional[Dict[str, Any]]:
    """
    Use AI to summarize and validate ERA segments.
    
    Args:
        segments: List of segment strings
    
    Returns:
        Dict with summaries/validations or None if unavailable
    """
    if not is_available():
        return None
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        prompt = f"""You are an expert in medical billing and ANSI 835 ERA files.
Analyze the following ERA segments and provide:
1. Identify any malformed segments
2. Suggest corrections for delimiter issues
3. Extract key information (RARC, CAS, CPT codes, amounts, dates)

Segments:
{chr(10).join(segments[:50])}  # Limit to first 50 segments

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
        
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": "You are a medical billing expert specializing in ANSI 835 ERA files."},
                {"role": "user", "content": prompt}
            ],
            timeout=AI_TIMEOUT,
            temperature=0.1
        )
        
        content = response.choices[0].message.content
        # Try to parse JSON from response
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Extract JSON from markdown code blocks if present
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            return {"raw_response": content}
    
    except Exception as e:
        logger.warning(f"AI enhancement failed: {e}")
        return None


def validate_line_items(service_lines: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
    """
    Use AI to validate and enhance service line items.
    
    Args:
        service_lines: List of service line dicts
    
    Returns:
        Enhanced service lines or None if unavailable
    """
    if not is_available():
        return None
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        prompt = f"""You are an expert in medical billing. Validate and enhance the following service line items:
1. Confirm CPT codes match descriptions
2. Map free-text denial notes to CAS/RARC codes
3. Suggest missing modifiers if appropriate

Service Lines:
{json.dumps(service_lines[:20], indent=2)}  # Limit to first 20

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
        
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": "You are a medical billing expert."},
                {"role": "user", "content": prompt}
            ],
            timeout=AI_TIMEOUT,
            temperature=0.1
        )
        
        content = response.choices[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            return None
    
    except Exception as e:
        logger.warning(f"AI validation failed: {e}")
        return None


def infer_cpt_from_description(description: str) -> Optional[str]:
    """
    Use AI to infer CPT code from procedure description.
    
    Args:
        description: Procedure description text
    
    Returns:
        Suggested CPT code or None
    """
    if not is_available() or not description:
        return None
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        prompt = f"""Given this medical procedure description, suggest the most likely CPT code (5 digits).

Description: {description}

Respond with ONLY the 5-digit CPT code, nothing else."""
        
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": "You are a medical billing expert. Respond with only the CPT code."},
                {"role": "user", "content": prompt}
            ],
            timeout=AI_TIMEOUT,
            temperature=0.1,
            max_tokens=10
        )
        
        code = response.choices[0].message.content.strip()
        # Validate it's a 5-digit number
        if __import__("re").match(r'^\d{5}$', code):
            return code
    
    except Exception as e:
        logger.warning(f"AI CPT inference failed: {e}")
    
    return None

