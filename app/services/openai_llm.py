import os, json
from openai import AsyncOpenAI
from app.schemas import WebsiteAnalysis, AIResponse

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
                             answers: dict, website: WebsiteAnalysis) -> AIResponse:
    prompt_text = f"""I have a client with the following responses to a questionnaire:
{json.dumps(answers, indent=2)}

We have analyzed the first fold of their website and provided the following feedback:
These is was the overall impression of the website:
{website.overallImpression}

These are the strengths of the website:
{website.strengths}

These are the weaknesses of the website:
{website.weaknesses}

These are the recommendations for the website:
{website.recommendations}

Based on these responses, recommend the most appropriate services from this catalog:
{json.dumps(services, indent=2)}

For each recommended service, provide a clear justification based on the client's specific needs.
Your response will be shown to the client so it should be addressed to them.
You should be specific with the transformation that the service you are recommending will deliver to the client.
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
