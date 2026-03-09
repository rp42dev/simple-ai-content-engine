from crewai import Crew, Process, Task
from agents.strategist import get_strategist_agent
from agents.writer import get_outline_agent, get_writer_agent
from agents.seo_agents import get_seo_optimizer_agent, get_internal_linker_agent
from agents.intelligence_agents import get_crawler_agent, get_gap_detector_agent
from tasks.strategist_tasks import get_cluster_task
from tasks.writer_tasks import get_outline_task, get_writer_task
from tasks.seo_tasks import get_seo_optimization_task, get_internal_linking_task
from tasks.intelligence_tasks import get_crawling_task, get_gap_analysis_task
from dotenv import load_dotenv
import os

load_dotenv()

def run_cluster_crew(topic):
    # Initialize agents
    strategist = get_strategist_agent()
    
    # Initialize tasks
    cluster_task = get_cluster_task(strategist)
    
    # Create Crew
    crew = Crew(
        agents=[strategist],
        tasks=[cluster_task],
        process=Process.sequential,
        verbose=True
    )
    
    # Execute
    result = crew.kickoff(inputs={'topic': topic})
    return result

def run_writing_crew(topic, subtopic):
    """Crew to write a single article (Pillar or Spoke)"""
    # Initialize agents
    outliner = get_outline_agent()
    writer = get_writer_agent()
    
    # Initialize tasks
    outline_task = get_outline_task(outliner, topic, subtopic)
    
    # Re-defining writer task within the crew context to use the previous output
    writer_task = Task(
        description=f"Write a full blog post for '{subtopic}' based on the outline provided by the outliner.",
        expected_output="A high-quality, formatted markdown article.",
        agent=writer
    )

    crew = Crew(
        agents=[outliner, writer],
        tasks=[outline_task, writer_task],
        process=Process.sequential,
        verbose=True
    )
    
    result = crew.kickoff()
    return result

def run_seo_crew(article_content, cluster_info):
    """Crew to optimize an article and suggest internal links"""
    seo_agent = get_seo_optimizer_agent()
    linker_agent = get_internal_linker_agent()
    
    seo_task = get_seo_optimization_task(seo_agent, article_content)
    linking_task = get_internal_linking_task(linker_agent, article_content, cluster_info)
    
    crew = Crew(
        agents=[seo_agent, linker_agent],
        tasks=[seo_task, linking_task],
        process=Process.sequential,
        verbose=True
    )
    
    result = crew.kickoff()
    return result

def run_intelligence_crew(competitor_url, our_cluster_info):
    """Crew to crawl a competitor and find content gaps"""
    crawler = get_crawler_agent()
    gap_detector = get_gap_detector_agent()
    
    crawl_task = get_crawling_task(crawler, competitor_url)
    # The gap detector needs the output of the crawler
    gap_task = get_gap_analysis_task(gap_detector, "{crawling_output}", our_cluster_info)
    
    # In CrewAI, we can use the output of one task in another by referencing it or just relying on sequential process.
    # To be explicit in the task description:
    gap_task.description = gap_task.description.replace("{competitor_content}", "the information gathered by the crawler")

    crew = Crew(
        agents=[crawler, gap_detector],
        tasks=[crawl_task, gap_task],
        process=Process.sequential,
        verbose=True
    )
    
    result = crew.kickoff()
    return result
