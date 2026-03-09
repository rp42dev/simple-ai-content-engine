from crewai import Agent
from tools.search_tools import get_search_tool

def get_crawler_agent():
    search_tool = get_search_tool()
    return Agent(
        role='Website Crawler & Researcher',
        goal='Extract key information and structure from competitor websites or specific URLs.',
        backstory="""You are a digital detective. You excel at navigating websites, 
        identifying the main topics they cover, and extracting the hierarchical structure 
        of their content. You gather the raw data needed to find what's missing in a content strategy.""",
        allow_delegation=False,
        verbose=True,
        tools=[search_tool]
    )

def get_gap_detector_agent():
    return Agent(
        role='Content Gap Analyst',
        goal='Identify missing topics and opportunities by comparing competitor content with our own.',
        backstory="""You are a strategic mastermind. You take data from competitors and 
        compare it against a current content cluster to find 'gaps'—topics that 
        competitors are ranking for but we aren't covering yet. You turn these gaps 
        into new content opportunities.""",
        allow_delegation=False,
        verbose=True
    )
