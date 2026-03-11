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


def get_serp_analysis_task(agent):
    return Task(
        description="""Analyze the following SERP research for the query '{topic_query}'.

        Topic context:
        - Parent topic: {topic}
        - Location: {location_context}

        SERP research:
        {serp_research}

        Extract structured guidance only.

        Focus on:
        - recurring headings and subtopics
        - common user questions
        - approximate content depth from ranking pages

        Word-range guidance:
        - For broad pillar topics or main-guide queries, prefer 1500-1800
        - For spoke-style subtopics, prefer 900-1200 unless the SERP clearly supports slightly deeper coverage

        Rules:
        - Never copy text from analyzed pages
        - Only extract structure, topic patterns, and questions
        - Do not generate article content

        Return JSON in this shape:
        {
          "query": "...",
          "top_headings": ["..."],
          "questions": ["..."],
          "recommended_word_range": "900-1200",
          "notes": ["..."]
        }""",
        expected_output="A JSON summary of structural SERP insights for writing guidance.",
        agent=agent
    )
