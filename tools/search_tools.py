from crewai_tools import ScrapeWebsiteTool

def get_search_tool():
    """Returns a tool for scraping/crawling websites."""
    return ScrapeWebsiteTool()
