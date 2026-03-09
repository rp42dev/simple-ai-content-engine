from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate


def p(text: str, style: ParagraphStyle):
    return Paragraph(text, style)


def bullets(items, style):
    return ListFlowable(
        [ListItem(Paragraph(i, style), value='*') for i in items],
        bulletType='bullet',
        leftIndent=12,
        bulletFontName=style.fontName,
        bulletFontSize=style.fontSize,
        bulletDedent=6,
        spaceBefore=1,
        spaceAfter=2,
    )


def build_pdf(out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=LETTER,
        leftMargin=0.55 * inch,
        rightMargin=0.55 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        title='AI Content Engine - One Page Summary',
    )

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=18,
        textColor=colors.HexColor('#111827'),
        spaceAfter=5,
    )
    h = ParagraphStyle(
        'H',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=12,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=5,
        spaceAfter=2,
    )
    body = ParagraphStyle(
        'Body',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=8.6,
        leading=10.4,
        textColor=colors.HexColor('#111827'),
        spaceAfter=1,
    )
    meta = ParagraphStyle(
        'Meta',
        parent=body,
        fontSize=8.2,
        textColor=colors.HexColor('#374151'),
    )

    story = []
    story.append(p('AI Content Engine - One Page App Summary', title))
    story.append(
        p(
            'Evidence sources: main.py, dashboard.py, crews/content_crew.py, agents/*, tasks/*, tools/*, requirements.txt, project_context.md, todo.md',
            meta,
        )
    )

    story.append(p('What It Is', h))
    story.append(
        p(
            'AI Content Engine is a Python app that orchestrates multi-step SEO content production with CrewAI agents. It runs a phased workflow that creates topic clusters, writes pillar and spoke markdown articles, applies SEO updates, and injects internal links.',
            body,
        )
    )

    story.append(p('Who It Is For', h))
    story.append(
        p(
            'Primary persona: SEO/content operators or marketing teams managing high-volume topic queues and approving strategy before content generation.',
            body,
        )
    )

    story.append(p('What It Does', h))
    story.append(
        bullets(
            [
                'Processes a JSON topic queue with priority ordering (high, medium, low).',
                'Generates a pillar-plus-spokes cluster plan per topic and stores it under outputs/*_cluster.json.',
                'Supports approval-gated production: writing waits until cluster_approved is set.',
                'Writes pillar and spoke markdown articles in batch-limited runs (CLI --limit).',
                'Runs SEO optimization and internal-link suggestion tasks, outputting *_seo.md artifacts.',
                'Performs final link injection to produce *_final.md files using cluster/global anchor mapping.',
                'Provides a Streamlit dashboard for queue management, execution status, autopilot looping, and artifact review.',
            ],
            body,
        )
    )

    story.append(p('How It Works (Repo-Evidenced Architecture)', h))
    story.append(
        bullets(
            [
                'UI + control plane: dashboard.py (Streamlit) manages queue edits, approvals, run triggers, status table, and starts main.py as a subprocess.',
                'Pipeline orchestrator: main.py executes four phases across queued topics (cluster -> writing -> SEO -> link injection).',
                'Agent/task layer: crews/content_crew.py composes CrewAI agents/tasks from agents/* and tasks/* with sequential execution.',
                'Tooling layer: tools/state_manager.py tracks per-topic workflow JSON; tools/link_injector.py resolves markdown link placeholders; tools/wordpress_tool.py provides CMS posting utility.',
                'Data flow: topics_queue.json -> phase outputs in outputs/ -> state/*.json progress updates -> dashboard reads state/artifacts for monitoring and control.',
                'Competitor intelligence components exist (agents/intelligence_agents.py + tasks/intelligence_tasks.py + ScrapeWebsiteTool) but are not called in main.py pipeline. Not found in repo: evidence of active integration in run flow.',
            ],
            body,
        )
    )

    story.append(p('How To Run (Minimal)', h))
    story.append(
        bullets(
            [
                'Create/activate venv and install dependencies: python -m venv .venv then .venv\\Scripts\\python -m pip install -r requirements.txt.',
                'Set .env values: OPENAI_API_KEY is required; WordPress variables are optional unless publishing.',
                'Add topics in topics_queue.json or via dashboard sidebar (topic, competitor_url, priority).',
                'Run UI: .venv\\Scripts\\python -m streamlit run dashboard.py.',
                'Run CLI directly: .venv\\Scripts\\python main.py --topic "Your Topic" --limit 2.',
                'Not found in repo: an official README/getting-started guide or canonical production run command.',
            ],
            body,
        )
    )

    doc.build(story)


if __name__ == '__main__':
    build_pdf(Path('output/pdf/ai_content_engine_one_page_summary.pdf'))
