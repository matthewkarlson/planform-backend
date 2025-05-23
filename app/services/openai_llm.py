import os, json
from openai import AsyncOpenAI
from app.schemas import WebsiteAnalysis, AIResponse

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def extract_company_insights(crawled_content: dict[str, str], client_answers: dict) -> str:
    """
    Extract key company insights from crawled website content to personalize recommendations.
    
    Args:
        crawled_content: Dictionary mapping URLs to their text content
        client_answers: Client's questionnaire responses for context
    
    Returns:
        String containing key insights about the company
    """
    if not crawled_content:
        return "No additional company information available from website crawl."
    
    # Prepare content summary for AI analysis
    content_summary = ""
    for url, content in crawled_content.items():
        page_type = "Main Page"
        url_lower = url.lower()
        if "about" in url_lower:
            page_type = "About Page"
        elif "team" in url_lower:
            page_type = "Team Page"
        elif "service" in url_lower or "product" in url_lower:
            page_type = "Services/Products Page"
        elif "contact" in url_lower:
            page_type = "Contact Page"
        elif "career" in url_lower:
            page_type = "Careers Page"
        
        content_summary += f"\n--- {page_type} ({url}) ---\n{content[:1000]}...\n"
    
    prompt = f"""Analyze the following website content from multiple pages and extract key insights about this company that would be valuable for personalizing business recommendations.

Client Context:
{json.dumps(client_answers, indent=2)}

Website Content:
{content_summary}

Extract and summarize:
1. Company mission, values, and unique positioning
2. Target audience and market focus
3. Current business model and revenue streams  
4. Company culture and team characteristics
5. Growth stage and business challenges
6. Competitive advantages and differentiators
7. Industry expertise and specializations

Provide specific, actionable insights that reveal:
- What makes this company unique
- Their current business challenges and opportunities
- Their target market and customer base
- Their growth stage and aspirations
- Key decision-making factors and business priorities

Keep the response concise but highly specific - focus on insights that would help personalize service recommendations and sales messaging. Avoid generic observations.

If there is a small amount of content, extract what you can but also return an insight that indicts the clients website has poor SEO, indicated by the lack of content available to the crawler.
"""

    messages = [
        {
            "role": "system", 
            "content": "You are an expert business analyst specializing in company research and competitive intelligence. Extract specific, actionable insights from website content that reveal business opportunities and challenges."
        },
        {"role": "user", "content": prompt}
    ]
    
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=800,
        temperature=0.3
    )
    
    return response.choices[0].message.content

async def analyse_website(b64_png: str, url: str, answers: dict) -> WebsiteAnalysis:
    messages = [
        {
            "role": "system",
            "content": "You are an expert web design and marketing consultant. Analyze this website screenshot and provide specific, actionable feedback. Format the output according to the website_analysis schema."
        },
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": f"Analyze the first fold of this website ({url}) and provide insights on its design, user experience, and effectiveness. Focus on strengths, weaknesses, and actionable recommendations. The client has provided the following answers to a questionnaire: {json.dumps(answers, indent=2)}" },
                {
                    "type": "input_image",
                    "image_url": f"data:image/png;base64,{b64_png}",
                    "detail": "high"
                }
            ]
        }
    ]
    
    response = await client.responses.parse(
        model="gpt-4.1-mini",
        input=messages,
        text_format=WebsiteAnalysis
    )
    return response.output_parsed

async def recommend_services(agency_desc: str, services: list,
                             answers: dict, website: WebsiteAnalysis, company_insights: str = None) -> AIResponse:
    
    # Build the website analysis section
    website_section = f"""We have analyzed the first fold of their website and provided the following feedback:
These is was the overall impression of the website:
{website.overallImpression}

These are the strengths of the website:
{website.strengths}

These are the weaknesses of the website:
{website.weaknesses}

These are the recommendations for the website:
{website.recommendations}"""

    # Add company insights section if available
    company_insights_section = ""
    if company_insights and company_insights.strip():
        company_insights_section = f"""

Additionally, from our comprehensive analysis of their website content, we have extracted these key company insights:
{company_insights}

Use these insights to create highly personalized recommendations that speak directly to their unique business situation, challenges, and opportunities."""

    prompt_text = f"""I have a client with the following responses to a questionnaire:
{json.dumps(answers, indent=2)}

{website_section}{company_insights_section}

Based on these responses and insights, recommend the most appropriate services from this catalog:
{json.dumps(services, indent=2)}

For each recommended service, provide a clear justification based on the client's specific needs and company characteristics.
Your response will be shown to the client so it should be addressed to them.
You should be specific with the transformation that the service you are recommending will deliver to the client.
Use the company insights to create personalized messaging that resonates with their unique business situation.

The plan title should be a a powerful hook that grips the reader and makes them want to read on. Remember this is a title
Its in large text and should be ultra brief and punchy.
The sub title should elaborate on the title and really lock in the client and get them to read on. It should be one short punchy sentence.
The sub title will be just below the title and will be in smaller text.
The call to action should be a powerful call to action that makes the client want to act now. It is displayed at the bottom of the page
in large text on a button so keep it brief, just a few powerful, personalised words.

Your ultimate goal is to craft the ultimate plan and sales pitch that converts clients using 
powerfuls sales tactics. Use well researched human psychology and sales tactics to speak to the client's
emotions and show them exactly we take them to their dream outcome.

Not overly focussed on the features of the services, but on the outcomes and emotions they will feel, a business they can be proud of.
Also keep it brief but powerful.
"""

    system_prompt = f"""You are an expert business consultant that works for the agency and helps match client needs
        to appropriate services. Provide structured, specific recommendations that are directly tied to the client's responses.
        A brief description of the agency is: {agency_desc}. Keep this in mind and remember you work for this agency.
        Format the output according to the service_recommendations schema. When recommending services, your reason for
        recommending should be based on powerful sales tactices and proving value to the client.
        The Executice summary should be a masterpiece of sales copy, delivering an exceptional level of insight and making
        it impossible for the client to ignore the opportunity. Demonstrating exactly what they will get from our services.
        Not selling them on features, but on the outcomes and emotions they will feel, a business they can be proud of.
        Their competitors won't stand a chance, with this agency at their side? They are unstoppable.
        """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt_text}
    ]
    
    response = await client.responses.parse(
        model="gpt-4.1-mini",
        input=messages,
        text_format=AIResponse
    )
    return response.output_parsed
