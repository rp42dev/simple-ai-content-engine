# AI Content Engine

This project builds an AI-powered SEO content generation system using CrewAI.

Goal:
Generate SEO content clusters and articles.

Workflow:
1. User enters topic
2. AI generates topic cluster
3. AI writes pillar article
4. AI writes spoke articles
5. AI adds internal links

Architecture:

agents/
AI agents definitions

tasks/
Agent tasks

crews/
Agent orchestration

state/
Workflow state storage

outputs/
Generated articles
