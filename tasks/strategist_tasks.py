from crewai import Task

def get_cluster_task(agent):
    return Task(
        description="""Research and define a topic cluster for the main topic: {topic}. 
        Identify 2 distinct 'spoke' topics that support the main 'pillar' topic. 
        For each spoke topic, provide a brief justification of why it's important for SEO authority.""",
        expected_output="""A structured list of 2 sub-topics with brief descriptions and SEO justifications. 
        Formatted as a JSON string for easy processing.""",
        agent=agent
    )
