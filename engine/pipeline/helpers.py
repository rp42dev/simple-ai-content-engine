import json
import os
import re

from config.profile_resolver import resolve_content_profile


def clean_json_output(content):
    if content.startswith("```"):
        content = re.sub(r"^```[a-z]*\n", "", content)
        content = re.sub(r"\n```$", "", content)
    return content.strip()


def safe_slug(value):
    slug = re.sub(r"[^a-zA-Z0-9]", "_", value.lower()).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug


def load_queue():
    json_path = "topics_queue.json"
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        if not isinstance(raw, list):
            return []

        normalized = []
        for item in raw:
            if not isinstance(item, dict) or not item.get("topic"):
                continue

            queue_item = dict(item)
            queue_item["location"] = item.get("location") if isinstance(item.get("location"), dict) else {}
            queue_item["business"] = item.get("business") if isinstance(item.get("business"), dict) else {}
            profile_overrides = item.get("profile") if isinstance(item.get("profile"), dict) else {}
            for key in [
                "industry",
                "topic_type",
                "language",
                "audience",
                "tone",
                "intent",
                "compliance_level",
                "brand_voice",
                "cta_style",
            ]:
                if key in item and key not in profile_overrides:
                    profile_overrides[key] = item.get(key)

            queue_item["profile"] = resolve_content_profile(
                queue_item.get("topic"),
                location=queue_item["location"],
                provided=profile_overrides,
            )
            normalized.append(queue_item)

        return normalized
    return []


def format_location_context(location):
    if not isinstance(location, dict):
        return "No specific location provided."

    labels = []
    if location.get("city"):
        labels.append(f"city={location['city']}")
    if location.get("area"):
        labels.append(f"area={location['area']}")
    if location.get("country"):
        labels.append(f"country={location['country']}")
    return ", ".join(labels) if labels else "No specific location provided."


def format_business_context(business):
    if not isinstance(business, dict):
        return "No business details provided."

    labels = []
    if business.get("name"):
        labels.append(f"name={business['name']}")
    if business.get("phone"):
        labels.append(f"phone={business['phone']}")
    return ", ".join(labels) if labels else "No business details provided."


def format_profile_context(profile):
    if not isinstance(profile, dict):
        return "No profile provided."

    labels = []
    for key in ["industry", "language", "tone", "audience", "intent", "compliance_level", "cta_style", "region"]:
        value = (profile.get(key) or "").strip() if isinstance(profile.get(key), str) else profile.get(key)
        if value:
            labels.append(f"{key}={value}")
    return ", ".join(labels) if labels else "No profile provided."


def build_pricing_context(topic, location, profile=None):
    country = (location or {}).get("country", "") if isinstance(location, dict) else ""
    topic_lower = (topic or "").lower()
    profile = profile if isinstance(profile, dict) else {}

    currency = (profile.get("currency") or "").strip()
    industry = (profile.get("industry") or "").strip().lower()

    if currency:
        return (
            f"Use {currency} for pricing in this content. Keep pricing realistic for {country or 'the target market'} "
            "and avoid currency-less treatment prices."
        )

    if industry == "healthcare":
        return "For healthcare pricing, use cautious and realistic ranges with a currency symbol where possible; avoid definitive guarantees."

    if country.strip().lower() == "ireland":
        if "implant" in topic_lower:
            return (
                "Use euro (€). If discussing dental implant pricing, mention that treatment in Ireland "
                "typically ranges from €2,000 to €3,500 per tooth depending on complexity. "
                "Never use currency-less treatment prices."
            )
        return "Use euro (€) for any cost discussion and never use currency-less treatment prices."

    return "If mentioning treatment costs, always include a currency symbol and keep the pricing realistic and local where possible."


def build_cta_context(location, business, profile=None):
    location = location if isinstance(location, dict) else {}
    business = business if isinstance(business, dict) else {}
    profile = profile if isinstance(profile, dict) else {}

    city = (location.get("city") or "").strip()
    area = (location.get("area") or city).strip()
    business_name = (business.get("name") or "").strip()
    phone = (business.get("phone") or "").strip()
    email = (business.get("email") or "").strip()
    website = (business.get("website") or "").strip()
    cta_style = (profile.get("cta_style") or "consultative").strip().lower()

    contact_parts = []
    if phone:
        contact_parts.append(f"📞 {phone}")
    if email:
        contact_parts.append(f"✉ {email}")
    if website:
        contact_parts.append(f"🌐 {website}")
    contact_suffix = " " + " | ".join(contact_parts) if contact_parts else ""

    if business_name and city and phone:
        if cta_style == "direct":
            return (
                f"CTA template: Ready to get started? Contact {business_name} in {city} today to schedule your consultation. "
                f"📍 {area or city}{contact_suffix}"
            )
        if cta_style == "educational":
            return (
                f"CTA template: Want to learn your options? Book a consultation with {business_name} in {city} to review suitability, expected outcomes, and next steps. "
                f"📍 {area or city}{contact_suffix}"
            )
        return (
            f"CTA template: Thinking about treatment? Book a consultation with {business_name} in {city}. "
            f"📍 {area or city}{contact_suffix}"
        )

    if business_name and phone:
        return (
            f"CTA template: Thinking about treatment? Contact {business_name} to book a consultation and discuss your options. "
            f"{contact_suffix.strip()}"
        )

    if city:
        return (
            f"CTA template: Thinking about treatment? Book a consultation with a qualified dental professional in {city} "
            f"to discuss your options, likely costs, and next steps."
        )

    return (
        "CTA template: Thinking about treatment? Book a consultation with a qualified dental professional "
        "to discuss your options, likely costs, and next steps."
    )


def get_global_anchor_map(queue):
    anchor_map = {}
    for item in queue:
        topic = item["topic"]
        topic_slug = safe_slug(topic)
        cluster_file = os.path.join("outputs", f"{topic_slug}_cluster.json")
        if not os.path.exists(cluster_file):
            continue
        try:
            with open(cluster_file, "r", encoding="utf-8") as f:
                data = json.loads(clean_json_output(f.read()))

            pillar = get_cluster_pillar(data)
            if pillar:
                anchor_map[pillar.lower()] = f"{topic_slug}_pillar.md"

            for spoke in get_cluster_spokes(data):
                spoke_topic = spoke.get("title") or spoke.get("topic") or spoke.get("sub_topic")
                if not spoke_topic:
                    continue
                anchor_map[spoke_topic.lower()] = f"spoke_{safe_slug(spoke_topic)}.md"
        except Exception:
            pass
    return anchor_map


def get_cluster_pillar(data, fallback_topic=None):
    if not isinstance(data, dict):
        return f"Ultimate Guide to {fallback_topic}" if fallback_topic else None
    return data.get("pillar_topic") or data.get("pillar") or (f"Ultimate Guide to {fallback_topic}" if fallback_topic else None)


def get_cluster_spokes(data):
    if not isinstance(data, dict):
        return []
    spokes = data.get("spoke_topics")
    if isinstance(spokes, list):
        return spokes
    spokes = data.get("spokes")
    return spokes if isinstance(spokes, list) else []
