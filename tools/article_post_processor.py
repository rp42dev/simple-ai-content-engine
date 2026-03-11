import json
import re


LOCK_MARKER = "<!-- ARTICLE_LOCKED -->"
INTRO_MARKER = "<!-- SLOT:INTRO -->"
CONCLUSION_MARKER = "<!-- SLOT:CONCLUSION -->"


def ensure_article_template(article_content):
    content = (article_content or "").strip()
    if not content:
        return content

    if LOCK_MARKER not in content:
        content = f"{LOCK_MARKER}\n{content}"

    if INTRO_MARKER not in content:
        match = re.search(r"(^# .+$\n)", content, flags=re.MULTILINE)
        if match:
            insert_at = match.end(1)
            content = content[:insert_at] + f"\n{INTRO_MARKER}\n" + content[insert_at:]

    if CONCLUSION_MARKER not in content:
        match = re.search(r"(^## Conclusion.*$)", content, flags=re.MULTILINE)
        if match:
            content = content[:match.start(1)] + f"{CONCLUSION_MARKER}\n" + content[match.start(1):]

    return content


def parse_json_payload(raw_content):
    text = (raw_content or "").strip()
    text = re.sub(r"^```[a-zA-Z0-9_\-]*\n", "", text)
    text = re.sub(r"\n```$", "", text)
    return json.loads(text)


def apply_seo_suggestions(article_content, suggestions):
    content = article_content
    meta_title = (suggestions or {}).get("meta_title", "").strip()
    meta_description = (suggestions or {}).get("meta_description", "").strip()

    lines = [line.rstrip() for line in content.splitlines()]
    body = []
    removed_meta = False
    for line in lines:
        if re.match(r"^Meta (Title|Description):", line.strip(), flags=re.IGNORECASE):
            removed_meta = True
            continue
        if removed_meta and not line.strip():
            continue
        removed_meta = False
        body.append(line)

    metadata = []
    if meta_title:
        metadata.append(f"Meta Title: {meta_title}")
    if meta_description:
        metadata.append(f"Meta Description: {meta_description}")

    if metadata:
        return "\n".join(metadata + [""] + body).strip() + "\n"
    return "\n".join(body).strip() + "\n"


def _extract_meta_value(content, key):
    pattern = re.compile(rf"^{re.escape(key)}:\s*(.+)$", flags=re.IGNORECASE | re.MULTILINE)
    match = pattern.search(content or "")
    return (match.group(1).strip() if match else "")


def ensure_metadata_guardrails(article_content, seo_suggestions=None, reference_content=None):
    content = article_content or ""
    reference = reference_content or ""
    suggestions = seo_suggestions if isinstance(seo_suggestions, dict) else {}

    current_title = _extract_meta_value(content, "Meta Title")
    current_description = _extract_meta_value(content, "Meta Description")

    fallback_title = (
        _extract_meta_value(reference, "Meta Title")
        or (suggestions.get("meta_title") or "").strip()
    )
    fallback_description = (
        _extract_meta_value(reference, "Meta Description")
        or (suggestions.get("meta_description") or "").strip()
    )

    if current_title and current_description:
        return content

    return apply_seo_suggestions(
        content,
        {
            "meta_title": current_title or fallback_title,
            "meta_description": current_description or fallback_description,
        },
    )


def count_internal_links(article_content):
    return len(re.findall(r"\[[^\]]+\]\(/[^)]+\)", article_content or ""))


def ensure_internal_link_coverage(article_content, link_suggestions, min_links=1):
    content = article_content or ""
    if count_internal_links(content) >= max(0, int(min_links)):
        return content

    suggestions = (link_suggestions or {}).get("internal_links", []) if isinstance(link_suggestions, dict) else []
    candidates = []
    for item in suggestions:
        if not isinstance(item, dict):
            continue
        anchor = (item.get("anchor") or "").strip()
        url = (item.get("url") or "").strip()
        if not anchor or not url or not url.startswith("/"):
            continue
        if url in content:
            continue
        short_anchor = " ".join(anchor.split()[:7]).strip()
        if len(short_anchor) < 8:
            continue
        candidates.append((short_anchor, url))

    if not candidates:
        return content

    selected = candidates[:2]
    joined = " and ".join([f"[{anchor}]({url})" for anchor, url in selected])
    sentence = f"For related reading, see {joined}."

    cta_header = "\n## Local Consultation Call to Action"
    insert_at = content.find(cta_header)
    if insert_at != -1:
        return content[:insert_at].rstrip() + "\n\n" + sentence + "\n\n" + content[insert_at:].lstrip("\n")

    return content.rstrip() + "\n\n" + sentence + "\n"


def _replace_first_plaintext(content, anchor, replacement):
    pattern = re.compile(rf"(?<!\]\()(?<!\[){re.escape(anchor)}(?!\]\()", flags=re.IGNORECASE)
    return pattern.sub(replacement, content, count=1)


def _replace_first_whole_word(content, word, replacement):
    pattern = re.compile(rf"(?<!\]\()(?<!\[)\b{re.escape(word)}\b(?!\]\()", flags=re.IGNORECASE)
    return pattern.sub(replacement, content, count=1)


def _keywords_from_text(text):
    tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
    stopwords = {
        "the", "and", "for", "with", "that", "this", "from", "into", "your", "what", "when", "where",
        "which", "about", "before", "during", "after", "guide", "ultimate", "overview", "option", "options",
        "right", "best", "step", "steps",
    }
    keywords = []
    seen = set()
    for token in tokens:
        if len(token) < 4 or token in stopwords:
            continue
        if token in seen:
            continue
        seen.add(token)
        keywords.append(token)
    return keywords


def _candidate_phrases_from_topic(topic):
    words = _keywords_from_text(topic)
    phrases = []
    for n in (4, 3):
        for idx in range(0, max(0, len(words) - n + 1)):
            phrase = " ".join(words[idx: idx + n])
            if phrase not in phrases:
                phrases.append(phrase)
    return phrases


def _best_fallback_phrase(line, fallback_keywords):
    tokens = re.findall(r"[a-z0-9]+", (line or "").lower())
    if len(tokens) < 2:
        return None

    keyword_set = set(fallback_keywords)
    generic_tokens = {"dental", "implant", "implants", "replacement", "tooth", "teeth"}
    edge_stopwords = {"the", "a", "an", "to", "for", "and", "or", "with", "in", "of", "on", "might", "may"}
    candidates = []
    for n in (3, 2):
        for idx in range(0, len(tokens) - n + 1):
            chunk = tokens[idx: idx + n]
            overlap = sum(1 for token in chunk if token in keyword_set)
            if overlap < 2:
                continue
            specific_overlap = sum(1 for token in chunk if token in keyword_set and token not in generic_tokens)
            if specific_overlap < 1:
                continue
            if chunk[0] in edge_stopwords or chunk[-1] in edge_stopwords:
                continue
            if all(token in generic_tokens for token in chunk):
                continue
            if not any(token not in generic_tokens for token in chunk):
                continue
            phrase = " ".join(chunk)
            candidates.append((specific_overlap, overlap, len(phrase), phrase))

    if not candidates:
        return None

    candidates.sort(reverse=True)
    return candidates[0][3]


def apply_link_suggestions(article_content, link_suggestions, topic_map):
    lines = article_content.splitlines()
    used_urls = set()
    for item in (link_suggestions or {}).get("internal_links", []):
        anchor = (item.get("anchor") or "").strip()
        url = (item.get("url") or "").strip()
        target_topic = (item.get("target_topic") or "").strip().lower()
        if not anchor:
            continue
        if not url and target_topic:
            url = topic_map.get(target_topic, "")
        if not url:
            continue
        if url in used_urls:
            continue

        linked = f"[{anchor}]({url})"
        linked_inserted = False
        for index, line in enumerate(lines):
            if line.lstrip().startswith("#"):
                continue
            updated_line = _replace_first_plaintext(line, anchor, linked)
            if updated_line != line:
                lines[index] = updated_line
                linked_inserted = True
                used_urls.add(url)
                break

        if linked_inserted:
            continue

        url_tokens = _keywords_from_text(url.replace("/", " ").replace("-", " "))
        fallback_keywords = _keywords_from_text(target_topic) + _keywords_from_text(anchor) + url_tokens
        fallback_keywords = list(dict.fromkeys(fallback_keywords))
        fallback_phrases = _candidate_phrases_from_topic(target_topic)

        if not fallback_keywords and not fallback_phrases:
            continue

        for index, line in enumerate(lines):
            stripped = line.lstrip()
            if not stripped or stripped.startswith("#"):
                continue
            if re.match(r"^(?:[-*]\s|\d+\.\s)", stripped):
                continue
            if stripped.lower().startswith("meta title:") or stripped.lower().startswith("meta description:"):
                continue
            if "](" in line:
                continue

            phrase_matched = False
            for phrase in fallback_phrases:
                phrase_pattern = re.compile(rf"\b{re.escape(phrase)}\b", flags=re.IGNORECASE)
                if not phrase_pattern.search(line):
                    continue
                fallback_link = f"[{phrase}]({url})"
                updated_line = _replace_first_plaintext(line, phrase, fallback_link)
                if updated_line != line:
                    lines[index] = updated_line
                    used_urls.add(url)
                    phrase_matched = True
                    break
            if phrase_matched:
                break

            lowered = line.lower()
            hits = [keyword for keyword in fallback_keywords if re.search(rf"\b{re.escape(keyword)}\b", lowered)]
            if "procedure" in fallback_keywords and re.search(r"\bprocess\b", lowered):
                hits.append("process")
            if len(hits) < 2:
                continue

            generic_hits = {"dental", "implant", "implants", "replacement", "tooth", "teeth"}
            specific_hits = [keyword for keyword in hits if keyword not in generic_hits]
            if not specific_hits:
                continue

            fallback_anchor = _best_fallback_phrase(line, hits)
            if not fallback_anchor:
                continue
            fallback_link = f"[{fallback_anchor}]({url})"
            updated_line = _replace_first_plaintext(line, fallback_anchor, fallback_link)
            if updated_line != line:
                lines[index] = updated_line
                used_urls.add(url)
                break

    return "\n".join(lines)


def apply_humanization_suggestions(article_content, suggestions):
    content = article_content
    for item in (suggestions or {}).get("phrase_rewrites", []):
        source = (item.get("source") or "").strip()
        replacement = (item.get("replacement") or "").strip()
        if not source or not replacement:
            continue
        content = content.replace(source, replacement, 1)
    return content


def sanitize_placeholder_text(article_content, location=None, business=None):
    content = article_content or ""
    location = location if isinstance(location, dict) else {}
    business = business if isinstance(business, dict) else {}

    city = (location.get("city") or "").strip()
    area = (location.get("area") or city).strip()
    country = (location.get("country") or "").strip()
    business_name = (business.get("name") or "").strip()
    phone = (business.get("phone") or "").strip()
    email = (business.get("email") or "").strip()
    website = (business.get("website") or "").strip()

    contact_parts = []
    if phone:
        contact_parts.append(f"📞 {phone}")
    if email:
        contact_parts.append(f"✉ {email}")
    if website:
        contact_parts.append(f"🌐 {website}")
    contact_suffix = " " + " | ".join(contact_parts) if contact_parts else ""

    clickable_contact_parts = []
    if phone:
        tel_value = re.sub(r"[^0-9+]", "", phone)
        clickable_contact_parts.append(f"📞 [{phone}](tel:{tel_value})")
    if email:
        clickable_contact_parts.append(f"✉ [{email}](mailto:{email})")
    if website:
        website_label = re.sub(r"^https?://", "", website).rstrip("/")
        clickable_contact_parts.append(f"🌐 [{website_label}]({website})")
    clickable_contact_suffix = " " + " | ".join(clickable_contact_parts) if clickable_contact_parts else contact_suffix

    specific_place = ", ".join([part for part in [area, city, country] if part])
    if specific_place:
        content = re.sub(r"\byour local area\b", specific_place, content, flags=re.IGNORECASE)
        content = re.sub(r"\bin your area\b", f"in {specific_place}", content, flags=re.IGNORECASE)
        content = re.sub(r"\blocal patients\b", f"patients in {specific_place}", content, flags=re.IGNORECASE)
    else:
        content = re.sub(r"\byour local area\b", "your area", content, flags=re.IGNORECASE)
        content = re.sub(r"\bin your area\b", "near you", content, flags=re.IGNORECASE)
        content = re.sub(r"\bsurrounding communities\b", "nearby communities", content, flags=re.IGNORECASE)
        content = re.sub(r"\bsurrounding areas\b", "nearby areas", content, flags=re.IGNORECASE)

    content = re.sub(r"\bClinics in your area often\b", "Many clinics", content, flags=re.IGNORECASE)
    content = re.sub(r"\bPatients in many local communities\b", "Many patients", content, flags=re.IGNORECASE)
    content = re.sub(r"\bMany local communities\b", "many patients", content, flags=re.IGNORECASE)
    content = re.sub(r"\blocal dental team\b", "dental team", content, flags=re.IGNORECASE)
    content = re.sub(r"\bcontact our dental team today\b", "book a consultation with a qualified dental professional today", content, flags=re.IGNORECASE)
    content = re.sub(r"\bOur team near you offers consultations tailored to your needs\.\b", "A consultation with a qualified dental professional can help you understand your options and next steps.", content, flags=re.IGNORECASE)
    content = re.sub(r"\bThis article was crafted to help patients near you understand\b", "This article was written to help patients understand", content, flags=re.IGNORECASE)
    content = re.sub(r"\bHere near you, we see more patients looking for\b", "Many patients look for", content, flags=re.IGNORECASE)
    content = re.sub(r"\bIn most dental practices near you,\b", "In many dental practices,", content, flags=re.IGNORECASE)
    content = re.sub(r"\bClinics near you often provide\b", "Many clinics provide", content, flags=re.IGNORECASE)
    content = re.sub(r"\bnear you, typical costs are roughly:?\b", "Typical costs are roughly:", content, flags=re.IGNORECASE)
    content = re.sub(r"\ba qualified dental clinic also offers financing options\b", "Some dental clinics also offer financing options", content, flags=re.IGNORECASE)
    content = re.sub(
        r"SCR Dental Clinic also offers financing options to help manage the investment in your oral health\.",
        "SCR Dental Clinic also offers financing options; ask during your consultation for current plans and eligibility.",
        content,
        flags=re.IGNORECASE,
    )
    content = re.sub(r"\bpatients often ask\b", "many patients ask", content, flags=re.IGNORECASE)
    content = re.sub(
        r"By the end, you should feel better equipped to understand the options and decide what may work best for your lifestyle and oral health\.",
        "By the end, you'll have a clearer understanding of both options and what may suit your oral health, lifestyle, and budget.",
        content,
        flags=re.IGNORECASE,
    )
    content = re.sub(r"\bOur experienced local team can evaluate your oral health, discuss your preferences, and develop a treatment plan tailored just for you\.\b", "A qualified dental professional can evaluate your oral health, discuss your preferences, and help you compare your treatment options.", content, flags=re.IGNORECASE)
    content = re.sub(r"📍 Serving patients near you and surroundings", "", content, flags=re.IGNORECASE)
    content = re.sub(r"here near you", "in many clinics", content, flags=re.IGNORECASE)
    content = re.sub(r"\bnear you\b", "locally", content, flags=re.IGNORECASE)
    content = re.sub(r"Thinking about dental implants\? Our team locally offers consultations tailored to your needs\. From initial imaging to a custom treatment plan, we’re here to answer your questions and help you see the possibilities for your smile\.", "Thinking about dental implants? A consultation with a qualified dental professional can help you understand the procedure, likely costs, and the next steps for your smile.", content)
    content = re.sub(r"Unsure which option suits you best\? Schedule a personalized tooth replacement consultation with us\. Our experienced local team can evaluate your oral health, discuss your preferences, and develop a treatment plan tailored just for you\.", "Unsure which option suits you best? A consultation with a qualified dental professional can help you compare implants, dentures, and other options based on your oral health, budget, and goals.", content)
    content = re.sub(r"📞 Contact us for appointment availability today", "Book a consultation with a qualified dental professional when you are ready to discuss your options.", content)
    content = re.sub(r"📞 Contact us today to schedule your appointment or learn about flexible payment plans\. Don’t wait—take the first step toward a comfortable, confident smile!", "Book a consultation with a qualified dental professional to discuss treatment options and likely costs.", content)
    content = re.sub(r"Ready to restore your smile\? Visit a qualified dental clinic for a no-obligation consultation to explore dental implants, dentures, or other tooth replacement options tailored for you\. We pride ourselves on patient-focused care using the latest technology in many clinics\.", "Ready to restore your smile? Book a consultation with a qualified dental professional to compare dental implants, dentures, and other tooth replacement options based on your needs.", content)
    content = re.sub(r"Many local patients have found dental implants life-changing", "Many patients find dental implants life-changing", content, flags=re.IGNORECASE)
    content = re.sub(
        r"Advances in dental care mean both options now provide better results to restore your smile and confidence\.",
        "Both implants and modern dentures can provide reliable functional and cosmetic results when planned by an experienced dental team.",
        content,
        flags=re.IGNORECASE,
    )

    if business_name:
        content = re.sub(r"\bour clinic\b", business_name, content, flags=re.IGNORECASE)
    else:
        content = re.sub(r"\bour clinic\b", "a qualified dental clinic", content, flags=re.IGNORECASE)

    if phone:
        content = re.sub(r"\bcontact us for availability\b", phone, content, flags=re.IGNORECASE)
        content = content.replace("[Local Clinic Phone Number]", phone)
    else:
        content = re.sub(
            r"\bcontact us for availability\b",
            "book a consultation to discuss your options",
            content,
            flags=re.IGNORECASE,
        )
        content = content.replace("[Local Clinic Phone Number]", "your preferred dental clinic")

    if business_name and specific_place and phone:
        content = re.sub(
            r"Thinking about treatment\?[^\n]*",
            f"Thinking about treatment? Book a consultation with {business_name} in {specific_place}. 📍 {specific_place}{clickable_contact_suffix}",
            content,
        )
    elif business_name and phone:
        content = re.sub(
            r"Thinking about treatment\?[^\n]*",
            f"Thinking about treatment? Contact {business_name} to book a consultation.{contact_suffix}",
            content,
        )
    else:
        content = re.sub(
            r"Thinking about treatment\?[^\n]*",
            "Thinking about treatment? Book a consultation with a qualified dental professional to discuss your options and next steps.",
            content,
        )

    content = re.sub(
        r"\*\*?Thinking about dental implants\?\*\*?[^\n]*",
        "Thinking about dental implants? A consultation with a qualified dental professional can help you understand the treatment steps, likely costs, and whether implants are right for you.",
        content,
    )

    content = re.sub(
        r"\*\*Start your journey to a renewed smile today!.*?years to come\.\*\*",
        "**If you are considering treatment, book a consultation with a qualified dental professional to discuss suitability, costs, and next steps.**",
        content,
        flags=re.DOTALL,
    )

    content = re.sub(
        r"Thinking about treatment\? Book a consultation with a qualified dental professional to discuss your options and next steps\.\n\n\*\*If you are considering treatment, book a consultation with a qualified dental professional to discuss suitability, costs, and next steps\.\*\*",
        "Thinking about treatment? Book a consultation with a qualified dental professional to discuss your options, likely costs, and next steps.",
        content,
        flags=re.IGNORECASE,
    )
    content = re.sub(
        r"Thinking about treatment\? Book a consultation with a qualified dental professional to discuss your options and next steps\.\n\nIf you are considering dental implants, a consultation with a qualified dental professional can help you understand your options and next steps\.",
        "Thinking about treatment? Book a consultation with a qualified dental professional to discuss your options, likely costs, and next steps.",
        content,
        flags=re.IGNORECASE,
    )
    content = re.sub(
        r"Unsure which option suits you best\? A consultation with a qualified dental professional can help you compare implants, dentures, and other options based on your oral health, budget, and goals\.\n\n\nBook a consultation with a qualified dental professional when you are ready to discuss your options\.",
        "Unsure which option suits you best? A consultation with a qualified dental professional can help you compare implants, dentures, and other options based on your oral health, budget, and goals.",
        content,
        flags=re.IGNORECASE,
    )
    content = re.sub(
        r"Ready to restore your smile\? Book a consultation with a qualified dental professional to compare dental implants, dentures, and other tooth replacement options based on your needs\.\n\nBook a consultation with a qualified dental professional to discuss treatment options and likely costs\.",
        "Ready to restore your smile? Book a consultation with a qualified dental professional to compare dental implants, dentures, and other tooth replacement options based on your needs and budget.",
        content,
        flags=re.IGNORECASE,
    )

    content = re.sub(
        r"If you’re considering dental implants and want to learn more about the procedure tailored specifically for your smile, book a consultation with a qualified dental professional today\. We’re here to guide you every step of the way!",
        "If you are considering dental implants, a consultation with a qualified dental professional can help you understand your options and next steps.",
        content,
    )

    content = re.sub(r"Patients in Many patients", "Many patients", content)
    content = content.replace("roughly::", "roughly:")

    if not business_name and not specific_place:
        content = content.replace("## Local Consultation Call to Action", "## Next Steps")
        content = content.replace("## Final Local Call to Action", "## Next Steps")

    if business_name:
        content = re.sub(
            r"Book a consultation with a qualified dental professional when you are ready to discuss your options\.",
            f"Book a consultation with {business_name} when you are ready to discuss your options.",
            content,
            flags=re.IGNORECASE,
        )
        content = re.sub(
            r"Book a consultation with a qualified dental professional to discuss treatment options and likely costs\.",
            f"Book a consultation with {business_name} to discuss treatment options and likely costs.",
            content,
            flags=re.IGNORECASE,
        )
        content = re.sub(
            r"\n\n\*\*If you are considering treatment, book a consultation with a qualified dental professional to discuss suitability, costs, and next steps\.\*\*",
            "",
            content,
            flags=re.IGNORECASE,
        )
        content = re.sub(
            r"\n\nIf you are considering dental implants, a consultation with a qualified dental professional can help you understand your options and next steps\.",
            "",
            content,
            flags=re.IGNORECASE,
        )

    content = re.sub(r"[ \t]+\n", "\n", content)
    return content
