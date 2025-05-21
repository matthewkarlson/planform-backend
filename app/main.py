from dotenv import load_dotenv
load_dotenv(dotenv_path=".env.local")

from fastapi import FastAPI, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select # Removed as select is imported from sqlalchemy directly or not used for this query type
from sqlalchemy.orm import selectinload
from sqlalchemy import select # Ensure select is imported if it was meant to be from here
from app.schemas import ClientResponses
from app.services.limiter import check as check_rate
from app.services.scraper import screenshot
from app.services.openai_llm import analyse_website, recommend_services
from app.db import get_db, Agency as App_DB_Agency, Service as App_DB_Service, Client as App_DB_Client, Plan as App_DB_Plan # Add Client, Plan

app = FastAPI()

@app.post("/plan")
async def generate_plan(payload: ClientResponses, req: Request, db: AsyncSession = Depends(get_db)):
    ident = payload.apiKey or req.client.host
    rl = await check_rate(ident)
    if not rl["allowed"]:
        raise HTTPException(429, detail=rl)

    # Fetch agency and services from DB
    agency_query_statement = (
        select(App_DB_Agency)
        .where(App_DB_Agency.api_key == payload.apiKey)
        .options(selectinload(App_DB_Agency.services))
    )
    agency_result = await db.execute(agency_query_statement)
    db_agency = agency_result.scalars().first() # Renamed to db_agency to avoid conflict with relationship name

    if not db_agency:
        raise HTTPException(status_code=404, detail="Agency not found for the provided API key.")

    agency_desc = db_agency.description
    services = [
        {
            "name": service.name,
            "description": service.description,
            "outcomes": service.outcomes,
            "price_lower": service.price_lower,
            "price_upper": service.price_upper,
            "when_to_recommend": service.when_to_recommend,
            "is_active": service.is_active,
        }
        for service in db_agency.services
    ]

    website_analysis = None
    b64 = None
    all_payload_data_for_analysis = payload.model_dump()
    if payload.model_extra:
        all_payload_data_for_analysis.update(payload.model_extra)
        
    if payload.websiteUrl:
        b64, _ = await screenshot(payload.websiteUrl)
        website_analysis = await analyse_website(b64, payload.websiteUrl, all_payload_data_for_analysis)

    all_payload_data_for_recommend = payload.model_dump()
    if payload.model_extra:
        all_payload_data_for_recommend.update(payload.model_extra)

    ai_response_data = await recommend_services(agency_desc, services, all_payload_data_for_recommend, website_analysis)

    # Find or create client
    db_client = None
    if payload.email:
        client_query = await db.execute(
            select(App_DB_Client).where(App_DB_Client.email == payload.email, App_DB_Client.agency_id == db_agency.id)
        )
        db_client = client_query.scalars().first()

    if not db_client and payload.email: # Create client if email is provided and client not found
        db_client = App_DB_Client(
            email=payload.email,
            name=payload.name,
            website_url=payload.websiteUrl,
            agency_id=db_agency.id
        )
        db.add(db_client)
        await db.flush() # Flush to get client ID if needed before commit, or rely on commit

    # Save plan to DB
    new_plan = App_DB_Plan(
        client_id=db_client.id if db_client else None,
        agency_id=db_agency.id,
        plan_data=ai_response_data.model_dump() # Assuming ai_response_data is a Pydantic model
    )
    db.add(new_plan)
    
    await db.commit()
    await db.refresh(new_plan) # Refresh to get created_at, id etc.
    if db_client: # Refresh client if it was newly created
        await db.refresh(db_client)

    return {
        "planId": new_plan.id, # Optionally return the new plan ID
        "clientId": db_client.id if db_client else None, # Optionally return client ID
        "recommendations": ai_response_data.recommendations,
        "executiveSummary": ai_response_data.executiveSummary,
        "websiteAnalysis": website_analysis,
        "screenshotBase64": b64
    }
