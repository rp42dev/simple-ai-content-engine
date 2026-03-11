from crewai import Task

def get_cluster_map_task(agent):
        return Task(
                description="""You are an SEO strategist designing a topic cluster.

                Given the primary topic '{topic}', create:
                - 1 pillar article
                - {spoke_count} spoke articles

                Local context:
                - Location: {location_context}
                - Business: {business_context}

                Rules:
                - The pillar should cover the main topic broadly
                - Spokes should cover areas such as procedures, comparisons, costs, risks, supporting treatments, and FAQs when relevant
                - Spokes must represent real search queries
                - Spokes must target different search intents
                - Spokes must avoid overlapping with the pillar
                - Spokes must be specific enough to rank individually
                - If location metadata exists, generate at least one spoke with local intent when it makes sense

                Each spoke must include an intent label using one of:
                - informational
                - commercial
                - comparison
                - supporting

                Return JSON in this shape:
                {
                    "pillar": "...",
                    "spokes": [
                        {"title": "...", "intent": "informational"}
                    ]
                }""",
                expected_output="A JSON cluster map with one pillar and a list of spoke titles plus intent labels.",
                agent=agent
        )


def get_cluster_task(agent):
    return Task(
        description="""Research and define a topic cluster for the main topic: {topic}.
        
        Local context:
        - Location: {location_context}
        - Business: {business_context}
                - Pre-generated cluster map: {cluster_map_context}
        
        Identify 2 distinct 'spoke' topics that support the main 'pillar' topic.
        For each spoke topic, provide a brief justification of why it's important for SEO authority.
                If location details are provided, prefer useful local-intent angles that would work well for a clinic website without making every title sound overly promotional.
                If a pre-generated cluster map exists, use it as the planning baseline and expand it into structured final cluster JSON.""",
        expected_output="""A structured list of 2 sub-topics with brief descriptions and SEO justifications. 
        Formatted as a JSON string for easy processing.""",
        agent=agent
    )
