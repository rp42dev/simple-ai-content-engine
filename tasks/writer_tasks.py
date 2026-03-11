from crewai import Task

def get_outline_task(agent):
    return Task(
        description="""Create a detailed article outline for the sub-topic: '{subtopic}'.
        This is part of a larger cluster for the main topic: '{topic}'.

        Local context:
        - Location: {location_context}
        - Business: {business_context}
        - Pricing guidance: {pricing_context}
        - SERP heading inspiration: {serp_headings}
        - Common search questions: {common_questions}
        - Recommended word range: {recommended_word_range}

        The outline should include:
        - Catchy SEO title
        - Introduction structure with local relevance if appropriate
        - Key H2 and H3 headings
        - Bullet points of what to cover in each section
        - A benefits section
        - A cost/pricing section when relevant
        - A short consultation CTA after the benefits section
        - A FAQ section with 4-6 real patient search-intent questions
        - A conclusion section
        - A final local CTA block after the conclusion

        Writing goals:
        - Write for a local dental clinic website
        - Focus on patient concerns: pain, cost, recovery, results, and suitability
        - Avoid generic filler or vague SEO headings
        - Keep the structure suitable for a pillar article around 1500-1800 words or a spoke article around 800-1200 words

                Pillar-specific rules:
                - If '{subtopic}' is the main guide for '{topic}', treat it as the pillar article
                - A pillar article should cover all major aspects of the topic at a high level
                - Do not go extremely deep into subtopics that belong in spoke articles
                - Subtopics such as procedures, costs, recovery, risks, and materials should be introduced clearly but not exhausted in detail
                - The pillar should naturally create room for related spoke articles
                - Use this pillar structure when relevant:
                    Introduction
                    What Are Dental Implants
                    Benefits of Dental Implants
                    Types of Dental Implants (overview)
                    Dental Implant Procedure (overview)
                    Dental Implant Costs (overview)
                    Risks and Considerations
                    Dental Implant Recovery
                    Dental Implant FAQ
                    Conclusion

        If local context is available, include places where local relevance can be added naturally for readers in that area.""",
        expected_output="A structured markdown outline for the article.",
        agent=agent
    )

def get_writer_task(agent):
    return Task(
        description="""Write a full blog post for '{subtopic}' based on the outline provided below.

        Outline:
        {outline_content}

        Local context:
        - Location: {location_context}
        - Business: {business_context}
        - Pricing guidance: {pricing_context}
        - CTA guidance: {cta_context}
        - SERP heading inspiration: {serp_headings}
        - Common search questions: {common_questions}
        - Recommended word range: {recommended_word_range}

        The article should be:
        - SEO-optimized
        - Professional but conversational
        - Written in clear, human, patient-friendly language
        - Free from generic phrases like 'has revolutionized dentistry'
        - Built around patient concerns: pain, cost, recovery, results, and next steps
        - A pillar article around 1500-1800 words or a spoke article around 800-1200 words depending on the topic scope
        - Properly formatted with markdown (H1, H2, H3, lists)

        Required content rules:
        - Mention the city or service area naturally in the introduction, conclusion, and CTA sections if local context exists
        - Mention consultation availability naturally where relevant
        - Add a useful cost section with explicit currency when costs are mentioned
        - For Ireland, use euro (€) and mention typical Irish dental implant ranges when relevant
        - Add 4-6 FAQ questions based on real search intent
        - Add a CTA block after the benefits section and another after the conclusion using the CTA guidance
        - Keep explanations simple and avoid academic tone

                Pillar article rules:
                - If '{subtopic}' is the main guide for '{topic}', treat it as the pillar article for the topic cluster
                - The pillar article is the central guide and should provide a complete overview without becoming too detailed on spoke topics
                - Cover all major aspects of the topic at a high level
                - Do NOT explain spoke topics in extreme detail
                - Subtopics such as procedures, costs, recovery, risks, and materials should be introduced clearly but kept concise
                - When a subtopic is mentioned, explain it briefly and naturally reference the related dedicated article when relevant
                - Avoid repeating the same information more than once
                - Use clear headings and short paragraphs
                - Target 1500-1800 words for the pillar article
                - Use this structure when writing the pillar article:
                    Introduction
                    What Are Dental Implants
                    Benefits of Dental Implants
                    Types of Dental Implants (overview)
                    Dental Implant Procedure (overview)
                    Dental Implant Costs (overview)
                    Risks and Considerations
                    Dental Implant Recovery
                    Dental Implant FAQ
                    Conclusion

                Introduction rules for pillar articles:
                - Do not begin with generic phrases such as 'Dental implants have revolutionized dentistry'
                - Start with a real patient concern, question, or practical problem
                - Then explain what the treatment is in simple language
                - Then tell the reader what the guide will help them understand

                Local context rules for pillar articles:
                - If location metadata is available, include subtle local signals naturally
                - Example style: patients in the city may ask about recovery time, cost, or suitability
                - Do not overuse the location

                CTA rules for pillar articles:
                - After the benefits section, include a short soft consultation CTA using the CTA guidance
                - Keep it helpful, not pushy

                FAQ rules for pillar articles:
                - End with a dedicated FAQ section
                - Generate 4-6 concise patient-focused questions based on common search intent
                - Keep answers short and clear

                Downstream-agent rule:
                - Do not insert SEO keyword lists, metadata blocks, or schema
                - Those are handled by downstream SEO-related agents

                SERP guidance rule:
                - Use the supplied SERP headings and questions as inspiration for structure only
                - Do not copy competitor wording or headings exactly
                - Keep the article original while covering similar logical ground

        Do not sound like a generic AI blog. Write as if a dentist is explaining the treatment to a patient.""",
        expected_output="A high-quality, formatted markdown article.",
        agent=agent
    )


def get_human_editor_task(agent):
    return Task(
        description="""Review the following near-final dental article for readability and human tone.

        Topic: {topic}
        Location: {location_context}
        Business: {business_context}

        Article:
        {article_content}

        Responsibilities:
        - Shorten long sentences where needed
        - Remove AI clichés and generic marketing phrasing
        - Simplify explanations without dumbing them down
        - Improve flow and readability
                - Preserve headings, structure, internal links, meta description, and SEO intent
                - Preserve CTA blocks and contact details

        Important:
                - Do NOT rewrite the entire article from scratch
                - Do NOT remove headings or links
                - Do NOT change the core meaning
                - Return JSON only

                Return JSON in this shape:
                {
                    "phrase_rewrites": [
                        {
                            "source": "",
                            "replacement": "",
                            "reason": ""
                        }
                    ]
                }

                Keep the list small and high-confidence. Only suggest direct phrase rewrites that can be applied safely.""",
                expected_output="A JSON object containing small phrase-level rewrite suggestions only.",
        agent=agent
    )


def get_article_qa_task(agent):
        return Task(
                description="""Review this final article for publish readiness.

                Topic: {topic}
                Location: {location_context}
                Business: {business_context}

                Final article:
                {article_content}

                Review criteria:
                - Flag placeholders such as 'our clinic', 'your local area', dummy phone text, or fake-local phrasing when real business/location data is missing
                - Flag missing or weak metadata, especially blank Meta Title or Meta Description
                - Flag AI-sounding wording such as 'revolutionized dentistry', hype, filler, or generic clinic claims
                - Flag weak CTA language, duplicated ideas, awkward transitions, and contradictions
                - Flag spoke articles that repeat too much pillar-level content instead of focusing on the assigned subtopic
                - Preserve article structure; do not rewrite the article

                Important:
                - Return JSON only
                - Be specific and brief
                - Mark blockers only when the article should not be published as-is

                Return JSON in this shape:
                {
                    "publish_ready": false,
                    "score": 0,
                    "summary": "",
                    "blockers": [
                        {
                            "issue": "",
                            "evidence": "",
                            "suggestion": ""
                        }
                    ],
                    "warnings": [
                        {
                            "issue": "",
                            "evidence": "",
                            "suggestion": ""
                        }
                    ],
                    "strengths": [""],
                    "suggested_edits": [
                        {
                            "severity": "high",
                            "issue": "",
                            "suggestion": ""
                        }
                    ]
                }

                Scoring guidance:
                - 90-100: publish ready with only minor polish
                - 70-89: usable but needs edits before publish
                - below 70: substantial issues remain""",
                expected_output="A JSON quality review with publish readiness, blockers, warnings, and suggested edits.",
                agent=agent,
        )
