from crewai import Task

def get_seo_optimization_task(agent, article_content):
    return Task(
        description=f"""Review and optimize the following article content for SEO:
        {article_content}
        
        Tasks:
        - Suggest a compelling meta description (max 160 chars).
        - Verify keyword inclusion (natural flow).
        - Suggest better H2/H3 headers if needed.
        - Check for internal linking opportunities.""",
        expected_output="A report containing the meta description and specific SEO improvement suggestions.",
        agent=agent
    )

def get_internal_linking_task(agent, current_article, cluster_info):
    return Task(
        description=f"""Based on this cluster information:
        {cluster_info}
        
        Analyze the current article and search for opportunities to link to other articles in the cluster:
        {current_article}
        
        Tasks:
        1. Identify 3-5 places where internal links to other topics in the cluster would be natural.
        2. Rewrite the article to include these links using the following Markdown syntax: [Anchor Text](Topic Name).
           Example: "...when considering [Invisalign treatment](Invisalign Treatment Process) you should..."
        3. Ensure the full article content is preserved, with the links seamlessly integrated.
        4. Append a 'Meta Description' at the very top of the article.""",
        expected_output="The full article in markdown format with internal link placeholders [Link Text](Topic Name) inserted.",
        agent=agent
    )
