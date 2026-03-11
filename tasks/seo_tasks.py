from crewai import Task

def get_seo_optimization_task(agent):
    return Task(
        description="""Review and optimize the following article content for SEO.

        Topic: {topic}
        Location: {location_context}
        Business: {business_context}

        Current article:
        {article_content}

        Tasks:
                - Suggest a compelling meta title
                - Suggest a compelling meta description (max 160 chars)
                - Suggest a short list of keyword or phrase opportunities only where needed
                - Suggest 0-3 heading refinements if needed
                - Suggest 0-4 FAQ question improvements for real search intent
                - If location context exists, suggest local SEO signals without keyword stuffing

        Important constraints:
                - Return JSON only
                - Do not rewrite the article
                - Do not return markdown article content

                Return JSON in this shape:
                {
                    "meta_title": "",
                    "meta_description": "",
                    "keywords": [""],
                    "heading_suggestions": [""],
                    "faq_suggestions": [""],
                    "local_seo_notes": [""]
                }""",
                expected_output="A JSON object containing SEO suggestions only.",
        agent=agent
    )

def get_internal_linking_task(agent):
    return Task(
        description="""Based on this cluster information:
        {cluster_info}

        Analyze the current article and search for opportunities to link to other articles in the cluster:
        {article_content}

        Tasks:
        1. Identify 3-5 places where internal links to other topics in the cluster would be natural.
                2. Return natural anchor phrases and their link targets.
        3. Use descriptive anchor text that matches the linked topic naturally.
          4. Avoid raw title repetition as anchor text unless it reads naturally.
                5. Do not use standalone parentheses or awkward trailing fragments.

        Local context:
        - Location: {location_context}
                - Business: {business_context}

                Return JSON only in this shape:
                {
                    "internal_links": [
                        {
                            "anchor": "",
                            "target_topic": "",
                            "url": ""
                        }
                    ]
                }""",
                expected_output="A JSON object containing internal link suggestions only.",
        agent=agent
    )
