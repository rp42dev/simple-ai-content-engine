import os
import json
import re
from engine.pipeline.helpers import get_cluster_pillar, get_cluster_spokes

def clean_string(s):
    """Normalize strings for matching: remove slashes, dashes, dots, and lowercase everything."""
    if not s: return ""
    # Remove leading/trailing slashes and make lowercase
    s = s.strip().lower().strip("/")
    # Replace dashes and underscores with spaces
    s = s.replace("-", " ").replace("_", " ")
    # Remove extra spaces
    return " ".join(s.split())

def inject_links(article_path, cluster_data, output_dir):
    """
    Reads an article, finds placeholders like [Link Text](Topic Name),
    and replaces them with real filenames based on cluster_data.
    """
    with open(article_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    pillar_topic = get_cluster_pillar(cluster_data)
    spoke_topics = get_cluster_spokes(cluster_data)
    
    # Create normalized map: cleaned_name -> filename
    topic_map = {}
    
    # Pillar mapping
    if pillar_topic:
        pillar_file = f"{re.sub(r'[^a-zA-Z0-9]', '_', pillar_topic.lower()).strip('_')}_pillar.md"
        topic_map[clean_string(pillar_topic)] = pillar_file
    
    # Spoke mapping
    for spoke in spoke_topics:
        topic = spoke.get("title") or spoke.get("topic") or spoke.get("sub_topic", "")
        if not topic: continue
        
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', topic.lower()).strip("_")
        while "__" in safe_name: safe_name = safe_name.replace("__", "_")
        
        filename = f"spoke_{safe_name}.md"
        topic_map[clean_string(topic)] = filename

    # Find [text](Topic Name)
    def replace_link(match):
        anchor = match.group(1)
        target_raw = match.group(2)
        target_cleaned = clean_string(target_raw)
        
        # 1. Direct match
        if target_cleaned in topic_map:
            return f"[{anchor}]({topic_map[target_cleaned]})"
        
        # 2. Try partial match (if the target is part of a cluster topic, or vice versa)
        for topic_key, filename in topic_map.items():
            if target_cleaned == topic_key or (len(target_cleaned) > 5 and (target_cleaned in topic_key or topic_key in target_cleaned)):
                return f"[{anchor}]({filename})"
        
        # 3. Handle special cases or just keep original
        print(f"Warning: Could not find target topic '{target_raw}' in cluster map.")
        return f"[{anchor}]({target_raw})"

    # Regex to find markdown links: [text](placeholder)
    new_content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', replace_link, content)

    return new_content
