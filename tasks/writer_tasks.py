from crewai import Task

def get_outline_task(agent, topic, subtopic):
    return Task(
        description=f"""Create a detailed article outline for the sub-topic: '{subtopic}'. 
        This is part of a larger cluster for the main topic: '{topic}'. 
        The outline should include:
        - Catchy SEO title
        - Introduction structure
        - Key H2 and H3 headings
        - Bullet points of what to cover in each section
        - A conclusion section.""",
        expected_output="A structured markdown outline for the article.",
        agent=agent
    )

def get_writer_task(agent, outline):
    return Task(
        description=f"""Write a full blog post based on the following outline:
        {outline}
        
        The article should be:
        - SEO-optimized
        - Conversational yet professional
        - Approximately 800-1200 words
        - Properly formatted with markdown (H1, H2, H3, lists).""",
        expected_output="A high-quality, formatted markdown article.",
        agent=agent
    )
