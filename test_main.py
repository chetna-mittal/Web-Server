import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from main import app
from database import Base, get_db, init_db

# Use in-memory database for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db():
    """Override database dependency for testing"""
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest.fixture(scope="function")
async def setup_db():
    """Setup test database before each test"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(setup_db):
    """Create test client with database override"""
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_validator_request(client):
    """Test creating a validator request"""
    response = await client.post(
        "/validators",
        json={
            "num_validators": 3,
            "fee_recipient": "0x1234567890abcdef1234567890abcdef12345678"
        }
    )
    
    assert response.status_code == 202
    data = response.json()
    assert "request_id" in data
    assert "message" in data
    assert data["message"] == "Validator creation in progress"
    assert len(data["request_id"]) == 36  # UUID length


@pytest.mark.asyncio
async def test_create_validator_request_invalid_address(client):
    """Test creating a validator request with invalid Ethereum address"""
    response = await client.post(
        "/validators",
        json={
            "num_validators": 3,
            "fee_recipient": "invalid_address"
        }
    )
    
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_validator_request_negative_validators(client):
    """Test creating a validator request with negative number of validators"""
    response = await client.post(
        "/validators",
        json={
            "num_validators": -1,
            "fee_recipient": "0x1234567890abcdef1234567890abcdef12345678"
        }
    )
    
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_validator_request_zero_validators(client):
    """Test creating a validator request with zero validators"""
    response = await client.post(
        "/validators",
        json={
            "num_validators": 0,
            "fee_recipient": "0x1234567890abcdef1234567890abcdef12345678"
        }
    )
    
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_validator_status_not_found(client):
    """Test getting status for non-existent request"""
    response = await client.get("/validators/non-existent-id")
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_validator_status_started(client):
    """Test getting status for a request that's still processing"""
    # Create a request
    create_response = await client.post(
        "/validators",
        json={
            "num_validators": 2,
            "fee_recipient": "0x1234567890abcdef1234567890abcdef12345678"
        }
    )
    
    request_id = create_response.json()["request_id"]
    
    # Immediately check status (should be started)
    status_response = await client.get(f"/validators/{request_id}")
    
    assert status_response.status_code == 200
    data = status_response.json()
    assert data["status"] == "started"


@pytest.mark.asyncio
async def test_get_validator_status_successful(client):
    """Test getting status for a successful request"""
    # Create a request
    create_response = await client.post(
        "/validators",
        json={
            "num_validators": 2,
            "fee_recipient": "0x1234567890abcdef1234567890abcdef12345678"
        }
    )
    
    request_id = create_response.json()["request_id"]
    
    # Wait for async task to complete (2 validators * 20ms = 40ms, add buffer)
    await asyncio.sleep(0.2)
    
    # Check status
    status_response = await client.get(f"/validators/{request_id}")
    
    assert status_response.status_code == 200
    data = status_response.json()
    assert data["status"] == "successful"
    assert "keys" in data
    assert len(data["keys"]) == 2
    assert all(isinstance(key, str) for key in data["keys"])


@pytest.mark.asyncio
async def test_health_check(client):
    """Test health check endpoint"""
    response = await client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "database" in data
    assert "connected" in data["database"].lower()


@pytest.mark.asyncio
async def test_validator_request_flow(client):
    """Test complete flow: create request, wait, check status"""
    # Create request
    create_response = await client.post(
        "/validators",
        json={
            "num_validators": 5,
            "fee_recipient": "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
        }
    )
    
    assert create_response.status_code == 202
    request_id = create_response.json()["request_id"]
    
    # Wait for processing (5 validators * 20ms = 100ms, add buffer)
    await asyncio.sleep(0.3)
    
    # Check status
    status_response = await client.get(f"/validators/{request_id}")
    
    assert status_response.status_code == 200
    data = status_response.json()
    assert data["status"] == "successful"
    assert len(data["keys"]) == 5

