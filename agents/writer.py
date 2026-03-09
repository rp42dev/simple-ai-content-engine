from crewai import Agent

def get_outline_agent():
    return Agent(
        role='Content Outliner',
        goal='Create detailed SEO-optimized outlines for articles based on specific sub-topics.',
        backstory="""You are a skilled content architect. You tahu how to structure an article 
        to ensure it covers all necessary points for the reader and satisfies search engine 
        requirements (H1, H2, H3 tags). You transform a simple topic into a comprehensive blueprint.""",
        allow_delegation=False,
        verbose=True
    )

def get_writer_agent():
    return Agent(
        role='Content Writer',
        goal='Write engaging, high-quality, and SEO-optimized blog posts based on provided outlines.',
        backstory="""You are a professional copywriter with a knack for making complex topics 
        easy to understand. Your writing is clear, authoritative, and keeps readers engaged. 
        You naturally weave in keywords without keyword stuffing.""",
        allow_delegation=False,
        verbose=True
    )
