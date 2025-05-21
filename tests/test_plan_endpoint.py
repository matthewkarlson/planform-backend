import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Agency as App_DB_Agency, Service as App_DB_Service, Client as App_DB_Client, Plan as App_DB_Plan
from app.schemas import AIResponse, ServiceRecommendation # Assuming AIResponse is the type returned by recommend_services

@pytest.mark.asyncio
async def test_hit_plan_endpoint_with_sample_payload(test_client: AsyncClient, db_session: AsyncSession):
    """Test hitting the /plan endpoint with a valid payload and check for successful plan creation."""
    # 1. Setup: Create an Agency and a Service in the test DB so the endpoint can find them.
    test_api_key = "test_plan_endpoint_key"
    agency = App_DB_Agency(name="Plan Endpoint Test Agency", api_key=test_api_key, description="Test desc")
    db_session.add(agency)
    await db_session.commit()
    await db_session.refresh(agency)

    service1 = App_DB_Service(
        name="Test Service for Plan", 
        description="Desc for plan service", 
        outcomes=["Outcome A"], 
        when_to_recommend=["Rec A"],
        agency_id=agency.id
    )
    db_session.add(service1)
    await db_session.commit()

    # 2. Prepare sample payload for the /plan endpoint
    sample_payload = {
        "apiKey": test_api_key,
        "websiteUrl": "http://example.com",
        "email": "test.client@example.com",
        "name": "Test Client for Plan",
        "question1": "answer1", # Example of an extra field
        "someGoal": "achieve something" # Another extra field
    }

    # Mock external services (screenshot, analyse_website, recommend_services) if they make real calls
    # For this example, we'll assume recommend_services is the main one to consider for output structure.
    # If screenshot or analyse_website are problematic (e.g., actual web access), they should be mocked.
    # Here, we are testing the flow *through* these services based on their expected interaction with the endpoint.

    # Expected structure from recommend_services (adjust if your actual AIResponse is different)
    # This mock would typically be more sophisticated using pytest-mock if recommend_services did complex things.
    # For now, the endpoint calls it, and we'll check the data it *would* save from such a response.

    # 3. Make the request to the /plan endpoint
    response = await test_client.post("/plan", json=sample_payload)

    # 4. Assertions
    assert response.status_code == 200
    response_data = response.json()

    assert "planId" in response_data
    assert "clientId" in response_data
    assert "recommendations" in response_data
    assert "executiveSummary" in response_data
    # assert response_data["websiteAnalysis"] is not None # This depends on if screenshot/analyse_website are mocked or run
    # assert response_data["screenshotBase64"] is not None

    # 5. Verify data in the database
    plan_id = response_data["planId"]
    client_id = response_data["clientId"]

    assert client_id is not None
    db_client = await db_session.get(App_DB_Client, client_id)
    assert db_client is not None
    assert db_client.email == sample_payload["email"]
    assert db_client.agency_id == agency.id

    assert plan_id is not None
    db_plan = await db_session.get(App_DB_Plan, plan_id)
    assert db_plan is not None
    assert db_plan.client_id == client_id
    assert db_plan.agency_id == agency.id
    assert "recommendations" in db_plan.plan_data # Check if plan_data structure is as expected
    assert "executiveSummary" in db_plan.plan_data

    # Check that extra payload fields were captured if your services use them
    # This part of the test depends on how `all_payload_data_for_recommend` is used by `recommend_services`
    # and what `ai_response_data.model_dump()` (which becomes `plan_data`) would contain.
    # For instance, if recommend_services echoed back some of these into its response, you could check them in db_plan.plan_data 