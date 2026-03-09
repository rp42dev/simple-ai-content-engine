import json
import os
import re


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
            return json.load(f)
    return []


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

            pillar = data.get("pillar_topic")
            if pillar:
                anchor_map[pillar.lower()] = f"{topic_slug}_pillar.md"

            for spoke in data.get("spoke_topics", []):
                spoke_topic = spoke.get("title") or spoke.get("topic") or spoke.get("sub_topic")
                if not spoke_topic:
                    continue
                anchor_map[spoke_topic.lower()] = f"spoke_{safe_slug(spoke_topic)}.md"
        except Exception:
            pass
    return anchor_map
