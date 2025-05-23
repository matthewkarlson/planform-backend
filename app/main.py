from dotenv import load_dotenv
load_dotenv(dotenv_path=".env.local")

from fastapi import FastAPI, Request, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select # Removed as select is imported from sqlalchemy directly or not used for this query type
from sqlalchemy.orm import selectinload
from sqlalchemy import select # Ensure select is imported if it was meant to be from here
from app.schemas import ClientResponses, DisplayServiceRecommendation
from app.services.limiter import check as check_rate
from app.services.scraper import screenshot, crawl_website
from app.services.openai_llm import analyse_website, recommend_services, extract_company_insights
from app.db import get_db, Agency as App_DB_Agency, Service as App_DB_Service, Client as App_DB_Client, Plan as App_DB_Plan # Add Client, Plan
import logging # Import logging
import uuid # Added for taskId generation
import asyncio # Added for parallel execution
from typing import Dict, Any # Added for typing

app = FastAPI()

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory store for task statuses. 
# TODO: Replace with a more robust solution like Redis or a database table for production.
task_statuses: Dict[str, Dict[str, Any]] = {}

async def generate_plan_async(task_id: str, payload: ClientResponses, db: AsyncSession, agency_api_key: str, client_host: str):
    try:
        task_statuses[task_id]["status"] = "processing"
        
        # Fetch agency and services from DB (Replicated from original endpoint)
        agency_query_statement = (
            select(App_DB_Agency)
            .where(App_DB_Agency.api_key == agency_api_key) # Use passed apiKey
            .options(selectinload(App_DB_Agency.services))
        )
        agency_result = await db.execute(agency_query_statement)
        db_agency = agency_result.scalars().first()

        if not db_agency:
            task_statuses[task_id] = {"status": "failed", "error": "Agency not found."}
            logger.error(f"Task {task_id}: Agency not found for API key.")
            return

        agency_desc = db_agency.description
        services = [
            {
                "name": service.name,
                "description": service.description,
                "outcomes": service.outcomes,
                "price_lower": service.price_lower,
                "price_upper": service.price_upper,
                "when_to_recommend": service.when_to_recommend,
            }
            for service in db_agency.services
        ]
        website_analysis = None
        b64 = None
        company_insights = None
        all_payload_data_for_analysis = payload.model_dump()
        if payload.model_extra:
            all_payload_data_for_analysis.update(payload.model_extra)
            
        if payload.websiteUrl:
            # Run screenshot and website crawling in parallel for speed
            screenshot_task = screenshot(payload.websiteUrl)
            crawl_task = crawl_website(payload.websiteUrl, max_pages=6)
            
            # Execute both tasks in parallel
            (b64, _), crawled_content = await asyncio.gather(screenshot_task, crawl_task)
            
            # Analyze the screenshot
            website_analysis = await analyse_website(b64, payload.websiteUrl, all_payload_data_for_analysis)
            
            # Extract company insights from crawled content
            if crawled_content:
                company_insights = await extract_company_insights(crawled_content, all_payload_data_for_analysis)
                logger.info(f"Task {task_id}: Extracted insights from {len(crawled_content)} pages")
            else:
                logger.warning(f"Task {task_id}: No content found during website crawl")

        all_payload_data_for_recommend = payload.model_dump()
        if payload.model_extra:
            all_payload_data_for_recommend.update(payload.model_extra)

        ai_response_data = await recommend_services(agency_desc, services, all_payload_data_for_recommend, website_analysis, company_insights)

        # Find or create client
        db_client = None
        if payload.email:
            client_query = await db.execute(
                select(App_DB_Client).where(App_DB_Client.email == payload.email, App_DB_Client.agency_id == db_agency.id)
            )
            db_client = client_query.scalars().first()

        if not db_client and payload.email:
            db_client = App_DB_Client(
                email=payload.email,
                name=payload.name,
                website_url=payload.websiteUrl,
                agency_id=db_agency.id
            )
            db.add(db_client)
            await db.flush()

        # Save plan to DB
        new_plan = App_DB_Plan(
            client_id=db_client.id if db_client else None,
            agency_id=db_agency.id,
            plan_data=ai_response_data.model_dump()
        )
        db.add(new_plan)
        
        await db.commit()
        await db.refresh(new_plan)
        if db_client:
            await db.refresh(db_client)

        display_recommendations = []
        for recommendation in ai_response_data.recommendations:
            display_recommendations.append(DisplayServiceRecommendation(
                id=recommendation.id,
                serviceId=recommendation.serviceId,
                reason=recommendation.reason,
                description=services[recommendation.id]["description"]
            ))

        plan_data_for_response = {
            "planId": new_plan.id,
            "clientId": db_client.id if db_client else None,
            "recommendations": display_recommendations,
            "executiveSummary": ai_response_data.executiveSummary,
            "websiteAnalysis": website_analysis,
            "screenshotBase64": b64,
            "planTitle": ai_response_data.planTitle,
            "subTitle": ai_response_data.subTitle,
            "callToAction": ai_response_data.callToAction
        }
        task_statuses[task_id] = {"status": "completed", "planData": plan_data_for_response}
        logger.info(f"Task {task_id}: Plan generation completed successfully.")

    except Exception as e:
        logger.error(f"Task {task_id}: Error during plan generation: {e}", exc_info=True)
        task_statuses[task_id] = {"status": "failed", "error": str(e)}
    finally:
        pass


@app.post("/plan")
async def generate_plan_request(
    payload: ClientResponses, 
    req: Request, 
    background_tasks: BackgroundTasks, # Added BackgroundTasks
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"Received request for /plan. API Key: {payload.apiKey}, Email: {payload.email}, Website URL: {payload.websiteUrl}")
    ident = payload.apiKey or req.client.host
    rl = await check_rate(ident)
    if not rl["allowed"]:
        raise HTTPException(status_code=429, detail=rl)

    task_id = str(uuid.uuid4())
    task_statuses[task_id] = {"status": "pending", "request_payload": payload.model_dump(mode='json')} # Store payload if needed
    background_tasks.add_task(generate_plan_async, task_id, payload, db, payload.apiKey, req.client.host)
    
    logger.info(f"Task {task_id} created for /plan request. Returning 202 Accepted.")
    return JSONResponse(status_code=202, content={"taskId": task_id})


@app.get("/plan/status/{task_id}")
async def get_plan_status(task_id: str):
    logger.info(f"Received request for /plan/status/{task_id}")
    status_info = task_statuses.get(task_id)
    if not status_info:
        logger.warning(f"Task {task_id} not found in status check.")
        raise HTTPException(status_code=404, detail="Task not found")
    
    logger.info(f"Returning status for task {task_id}: {status_info.get('status')}")
    return status_info
