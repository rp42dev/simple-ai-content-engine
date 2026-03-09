from crewai import Task

def get_crawling_task(agent, url):
    return Task(
        description=f"""Crawl and analyze the following URL: {url}.
        Identify the main topics, sub-topics, and the overall content structure.
        List the titles of the articles or sections found on this page or site.""",
        expected_output="A structured list of topics and content structure found on the website.",
        agent=agent
    )

def get_gap_analysis_task(agent, competitor_content, our_content_cluster):
    return Task(
        description=f"""Compare the following competitor content:
        {competitor_content}
        
        With our current content cluster:
        {our_content_cluster}
        
        Identify 3-5 high-value topics or sub-topics that the competitor covers but we are missing.
        For each gap, explain why it's a valuable opportunity for our SEO strategy.""",
        expected_output="A list of content gaps with justifications and suggested new topics.",
        agent=agent
    )
