import json
import re
from copy import deepcopy
from functools import lru_cache
from pathlib import Path


CONFIG_DIR = Path(__file__).resolve().parent
DEFAULT_PROFILE_FILE = CONFIG_DIR / "profile_defaults.json"
POLICY_DIR = CONFIG_DIR / "policies"


def _deep_merge(base, override):
    merged = deepcopy(base) if isinstance(base, dict) else {}
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


@lru_cache(maxsize=1)
def _load_defaults():
    if not DEFAULT_PROFILE_FILE.exists():
        return {}
    with open(DEFAULT_PROFILE_FILE, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload if isinstance(payload, dict) else {}


@lru_cache(maxsize=16)
def _load_policy(industry):
    safe = re.sub(r"[^a-z0-9_\-]", "", (industry or "").strip().lower())
    if not safe:
        safe = "generic_business"
    target = POLICY_DIR / f"{safe}.json"
    if not target.exists():
        target = POLICY_DIR / "generic_business.json"
    if not target.exists():
        return {}
    with open(target, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload if isinstance(payload, dict) else {}


def infer_industry(topic):
    lowered = (topic or "").lower()
    healthcare_markers = [
        "dental", "dentist", "clinic", "implant", "braces", "orthodont", "medical", "health",
        "invisalign", "tooth", "teeth", "whitening", "oral",
    ]
    finance_markers = [
        "finance", "financial", "investment", "investing", "retirement", "mortgage", "loan", "credit",
        "tax", "budget", "wealth", "portfolio", "insurance",
    ]
    legal_markers = [
        "legal", "law", "lawyer", "attorney", "contract", "compliance", "regulation", "litigation",
        "employment law", "family law", "estate planning", "immigration law",
    ]
    if any(marker in lowered for marker in healthcare_markers):
        return "healthcare"
    if any(marker in lowered for marker in finance_markers):
        return "finance"
    if any(marker in lowered for marker in legal_markers):
        return "legal"
    return "generic_business"


def _country_currency(country):
    mapping = {
        "ireland": "€",
        "united kingdom": "£",
        "uk": "£",
        "united states": "$",
        "usa": "$",
        "canada": "C$",
        "australia": "A$",
        "new zealand": "NZ$",
        "eurozone": "€",
        "germany": "€",
        "france": "€",
        "spain": "€",
        "italy": "€",
    }
    return mapping.get((country or "").strip().lower(), "")


def resolve_content_profile(topic, location=None, provided=None):
    location = location if isinstance(location, dict) else {}
    provided = provided if isinstance(provided, dict) else {}

    defaults = _load_defaults()
    industry = (provided.get("industry") or "").strip().lower() or infer_industry(topic)
    policy = _load_policy(industry)

    profile = _deep_merge(defaults, policy)
    profile = _deep_merge(profile, provided)

    profile["industry"] = (profile.get("industry") or industry or "generic_business").strip().lower()
    profile["language"] = (profile.get("language") or "en").strip().lower()
    profile["tone"] = (profile.get("tone") or "professional").strip()
    profile["cta_style"] = (profile.get("cta_style") or "consultative").strip().lower()

    region = (location.get("country") or "").strip()
    if region and not (profile.get("region") or "").strip():
        profile["region"] = region

    if not (profile.get("currency") or "").strip():
        profile["currency"] = _country_currency(region)

    return profile
