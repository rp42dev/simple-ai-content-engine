from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate


def para(text, style):
    return Paragraph(text, style)


def bullets(items, style):
    return ListFlowable(
        [ListItem(Paragraph(item, style), value='-') for item in items],
        bulletType='bullet',
        leftIndent=11,
        bulletDedent=6,
        bulletFontName=style.fontName,
        bulletFontSize=style.fontSize,
        spaceBefore=1,
        spaceAfter=1,
    )


def build(out_pdf: Path):
    out_pdf.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(out_pdf),
        pagesize=LETTER,
        leftMargin=0.55 * inch,
        rightMargin=0.55 * inch,
        topMargin=0.48 * inch,
        bottomMargin=0.48 * inch,
        title='AI Content Engine - PDF Skill Summary',
    )

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        'title',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=17,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=4,
    )
    h = ParagraphStyle(
        'h',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=10.2,
        leading=11.8,
        textColor=colors.HexColor('#111827'),
        spaceBefore=4,
        spaceAfter=2,
    )
    body = ParagraphStyle(
        'body',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=10.1,
        textColor=colors.HexColor('#111827'),
        spaceAfter=1,
    )
    meta = ParagraphStyle(
        'meta',
        parent=body,
        fontSize=7.9,
        textColor=colors.HexColor('#4B5563'),
    )

    story = [
        para('AI Content Engine - One Page PDF Skill Summary', title),
        para(
            'Evidence used: main.py, dashboard.py, crews/content_crew.py, tasks/, tools/, project_context.md, todo.md, requirements.txt',
            meta,
        ),

        para('What It Is', h),
        para(
            'AI Content Engine is a Python app that orchestrates an AI-assisted SEO content pipeline with CrewAI. It executes phased runs that generate topic clusters, produce pillar/spoke markdown articles, optimize for SEO, and finalize internal links.',
            body,
        ),

        para('Who It Is For', h),
        para(
            'Primary persona: SEO/content operations teams or solo marketers who manage topic queues and want guided approvals before production.',
            body,
        ),

        para('What It Does', h),
        bullets([
            'Loads topics from topics_queue.json and processes by priority (high, medium, low).',
            'Builds per-topic cluster plans and saves outputs/*_cluster.json.',
            'Supports approval-gated production (cluster_approved) before writing.',
            'Writes pillar and spoke articles to markdown with per-run spoke limits (--limit).',
            'Runs SEO and link-suggestion pass, creating *_seo.md artifacts.',
            'Injects final internal links via mapping and writes *_final.md files.',
            'Provides Streamlit dashboard controls: queue add/reset, run status, autopilot, and artifact preview.',
        ], body),

        para('How It Works (Repo-Evidenced Architecture)', h),
        bullets([
            'Presentation/control: dashboard.py (Streamlit UI) edits queue, captures approvals, and launches main.py as subprocess.',
            'Orchestration: main.py runs four phases across topics: cluster -> writing -> SEO -> final link injection.',
            'Agent orchestration: crews/content_crew.py wires CrewAI agents/tasks (strategist, outliner/writer, SEO/linker).',
            'State + files: tools/state_manager.py writes per-topic JSON in state/; artifacts flow through outputs/ as cluster/article/seo/final files.',
            'Link finalization: tools/link_injector.py rewrites markdown placeholders to target files.',
            'Intelligence crawler/gap modules exist (agents/intelligence_agents.py, tasks/intelligence_tasks.py) but are not invoked in main.py flow. Not found in repo: active production wiring for competitor-intelligence phase.',
        ], body),

        para('How To Run (Minimal)', h),
        bullets([
            'Create venv and install deps: python -m venv .venv, then .venv\\Scripts\\python -m pip install -r requirements.txt.',
            'Set .env with OPENAI_API_KEY (required). WordPress values are optional for CMS posting.',
            'Add topics via dashboard sidebar or edit topics_queue.json.',
            'Run dashboard: .venv\\Scripts\\python -m streamlit run dashboard.py.',
            'Run CLI directly: .venv\\Scripts\\python main.py --topic "Your Topic" --limit 2.',
            'Not found in repo: ARCHITECTURE.md and an official README quickstart.',
        ], body),
    ]

    doc.build(story)


if __name__ == '__main__':
    build(Path('output/pdf/ai_content_engine_pdf_skill_summary_one_page.pdf'))
