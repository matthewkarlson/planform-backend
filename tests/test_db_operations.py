import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import Agency as App_DB_Agency, Service as App_DB_Service, Client as App_DB_Client, Plan as App_DB_Plan

@pytest.mark.asyncio
async def test_db_connection(db_session: AsyncSession):
    """Test basic database connection by executing a simple query."""
    result = await db_session.execute(select(1))
    assert result.scalar_one() == 1

@pytest.mark.asyncio
async def test_create_and_read_agency(db_session: AsyncSession):
    """Test creating and reading an Agency."""
    new_agency = App_DB_Agency(name="Test Agency", api_key="testkey123", description="A test agency")
    db_session.add(new_agency)
    await db_session.commit()
    await db_session.refresh(new_agency)

    retrieved_agency = await db_session.get(App_DB_Agency, new_agency.id)
    assert retrieved_agency is not None
    assert retrieved_agency.name == "Test Agency"
    assert retrieved_agency.api_key == "testkey123"

@pytest.mark.asyncio
async def test_create_and_read_service_for_agency(db_session: AsyncSession):
    """Test creating a service associated with an agency and reading it."""
    # 1. Create an agency
    agency = App_DB_Agency(name="Service Test Agency", api_key="servicekey", description="Agency for services")
    db_session.add(agency)
    await db_session.commit()
    await db_session.refresh(agency)

    # 2. Create a service for that agency
    new_service = App_DB_Service(
        name="Test Service",
        description="A service for testing",
        outcomes=["Good outcome"],
        when_to_recommend=["Always"],
        agency_id=agency.id
    )
    db_session.add(new_service)
    await db_session.commit()
    await db_session.refresh(new_service)

    # 3. Retrieve the service
    retrieved_service = await db_session.get(App_DB_Service, new_service.id)
    assert retrieved_service is not None
    assert retrieved_service.name == "Test Service"
    assert retrieved_service.agency_id == agency.id

    # 4. Verify it's linked to the agency (optional, via relationship)
    retrieved_agency_with_service = await db_session.get(App_DB_Agency, agency.id)
    assert retrieved_agency_with_service is not None
    # To check services relationship, you might need eager loading in the get or refresh, 
    # or a separate query. For simplicity, we check agency_id on service.
    # For a more thorough check, you'd query agency.services. 