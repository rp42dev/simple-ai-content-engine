from crewai import Crew, Process
from agents.strategist import get_cluster_map_agent, get_strategist_agent
from agents.writer import get_article_qa_agent, get_outline_agent, get_writer_agent, get_human_editor_agent
from agents.seo_agents import get_seo_optimizer_agent, get_internal_linker_agent
from agents.intelligence_agents import get_crawler_agent, get_gap_detector_agent, get_serp_analysis_agent
from tasks.strategist_tasks import get_cluster_map_task, get_cluster_task
from tasks.writer_tasks import get_article_qa_task, get_outline_task, get_writer_task, get_human_editor_task
from tasks.seo_tasks import get_seo_optimization_task, get_internal_linking_task
from tasks.intelligence_tasks import get_crawling_task, get_gap_analysis_task, get_serp_analysis_task
from dotenv import load_dotenv
from engine.pipeline.helpers import build_cta_context, build_pricing_context, format_business_context, format_location_context, format_profile_context

load_dotenv()


def _build_inputs(topic, item=None, subtopic=None, article_content=None, cluster_info=None, cluster_size=None, cluster_map_context=None, serp_analysis=None, topic_query=None, serp_research=None, outline_content=None):
    item = item or {}
    location = item.get("location") if isinstance(item.get("location"), dict) else {}
    business = item.get("business") if isinstance(item.get("business"), dict) else {}
    profile = item.get("profile") if isinstance(item.get("profile"), dict) else {}
    inputs = {
        "topic": topic,
        "location_context": format_location_context(location),
        "business_context": format_business_context(business),
        "profile_context": format_profile_context(profile),
        "pricing_context": build_pricing_context(topic, location, profile=profile),
        "cta_context": build_cta_context(location, business, profile=profile),
        "spoke_count": max(1, int(cluster_size) - 1) if cluster_size is not None else 5,
        "cluster_map_context": cluster_map_context or "No pre-generated cluster map provided.",
        "serp_headings": (serp_analysis or {}).get("top_headings", []),
        "common_questions": (serp_analysis or {}).get("questions", []),
        "recommended_word_range": (serp_analysis or {}).get("recommended_word_range", "Use the default range for the article type."),
        "topic_query": topic_query or topic,
        "serp_research": serp_research or "No SERP research provided.",
    }

    if subtopic is not None:
        inputs["subtopic"] = subtopic
    if article_content is not None:
        inputs["article_content"] = article_content
    if cluster_info is not None:
        inputs["cluster_info"] = cluster_info
    if outline_content is not None:
        inputs["outline_content"] = outline_content

    return inputs


def run_cluster_map_crew(topic, item=None, cluster_size=6):
    cluster_map_agent = get_cluster_map_agent()
    cluster_map_task = get_cluster_map_task(cluster_map_agent)

    crew = Crew(
        agents=[cluster_map_agent],
        tasks=[cluster_map_task],
        process=Process.sequential,
        verbose=True
    )

    return crew.kickoff(inputs=_build_inputs(topic, item=item, cluster_size=cluster_size))


def run_serp_analysis_crew(topic, topic_query, serp_research, item=None):
    serp_agent = get_serp_analysis_agent()
    serp_task = get_serp_analysis_task(serp_agent)

    crew = Crew(
        agents=[serp_agent],
        tasks=[serp_task],
        process=Process.sequential,
        verbose=True
    )

    return crew.kickoff(
        inputs=_build_inputs(
            topic,
            item=item,
            topic_query=topic_query,
            serp_research=serp_research,
        )
    )


def run_cluster_crew(topic, item=None, cluster_map_context=None):
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
    result = crew.kickoff(inputs=_build_inputs(topic, item=item, cluster_map_context=cluster_map_context))
    return result


def run_outline_crew(topic, subtopic, item=None, serp_analysis=None):
    outliner = get_outline_agent()
    outline_task = get_outline_task(outliner)

    crew = Crew(
        agents=[outliner],
        tasks=[outline_task],
        process=Process.sequential,
        verbose=True
    )

    return crew.kickoff(inputs=_build_inputs(topic, item=item, subtopic=subtopic, serp_analysis=serp_analysis))


def run_writer_from_outline_crew(topic, subtopic, outline_content, item=None, serp_analysis=None):
    writer = get_writer_agent()
    writer_task = get_writer_task(writer)

    crew = Crew(
        agents=[writer],
        tasks=[writer_task],
        process=Process.sequential,
        verbose=True
    )

    return crew.kickoff(
        inputs=_build_inputs(
            topic,
            item=item,
            subtopic=subtopic,
            serp_analysis=serp_analysis,
            outline_content=outline_content,
        )
    )

def run_writing_crew(topic, subtopic, item=None, serp_analysis=None):
    """Crew to write a single article (Pillar or Spoke)"""
    outline = run_outline_crew(topic, subtopic, item=item, serp_analysis=serp_analysis)
    return run_writer_from_outline_crew(
        topic,
        subtopic,
        str(outline),
        item=item,
        serp_analysis=serp_analysis,
    )

def run_seo_suggestions_crew(article_content, topic, item=None):
    """Crew to produce structured SEO suggestions only"""
    seo_agent = get_seo_optimizer_agent()
    seo_task = get_seo_optimization_task(seo_agent)
    
    crew = Crew(
        agents=[seo_agent],
        tasks=[seo_task],
        process=Process.sequential,
        verbose=True
    )
    
    result = crew.kickoff(
        inputs=_build_inputs(
            topic,
            item=item,
            article_content=article_content,
        )
    )
    return result


def run_link_suggestions_crew(article_content, cluster_info, topic, item=None):
    """Crew to produce structured internal link suggestions only"""
    linker_agent = get_internal_linker_agent()
    linking_task = get_internal_linking_task(linker_agent)

    crew = Crew(
        agents=[linker_agent],
        tasks=[linking_task],
        process=Process.sequential,
        verbose=True
    )

    return crew.kickoff(
        inputs=_build_inputs(
            topic,
            item=item,
            article_content=article_content,
            cluster_info=cluster_info,
        )
    )


def run_human_editor_crew(article_content, topic, item=None):
    editor = get_human_editor_agent()
    editor_task = get_human_editor_task(editor)

    crew = Crew(
        agents=[editor],
        tasks=[editor_task],
        process=Process.sequential,
        verbose=True
    )

    return crew.kickoff(inputs=_build_inputs(topic, item=item, article_content=article_content))


def run_article_qa_crew(article_content, topic, item=None):
    reviewer = get_article_qa_agent()
    qa_task = get_article_qa_task(reviewer)

    crew = Crew(
        agents=[reviewer],
        tasks=[qa_task],
        process=Process.sequential,
        verbose=True
    )

    return crew.kickoff(inputs=_build_inputs(topic, item=item, article_content=article_content))

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
