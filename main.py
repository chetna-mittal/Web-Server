import logging
import uuid
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import init_db, get_db, ValidatorRequest, ValidatorKey
from models import (
    CreateValidatorRequest,
    CreateValidatorResponse,
    ValidatorStatusResponse,
    HealthResponse
)
from tasks import spawn_validator_task

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup"""
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Validator API",
    description="API for managing validator creation requests",
    version="1.0.0",
    lifespan=lifespan
)


@app.post("/validators", response_model=CreateValidatorResponse, status_code=202)
async def create_validator_request(
    request: CreateValidatorRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new validator request.
    Accepts the request and immediately returns a UUID.
    Spawns an async task to process validator creation in the background.
    """
    request_id = str(uuid.uuid4())
    logger.info(f"Creating validator request {request_id} for {request.num_validators} validators")
    
    # Create request record with status 'started'
    validator_request = ValidatorRequest(
        request_id=request_id,
        num_validators=request.num_validators,
        fee_recipient=request.fee_recipient,
        status="started"
    )
    
    db.add(validator_request)
    await db.commit()
    await db.refresh(validator_request)
    
    # Spawn async task to process validator creation
    spawn_validator_task(request_id, request.num_validators, request.fee_recipient)
    
    logger.info(f"Validator request {request_id} created and processing started")
    
    return CreateValidatorResponse(
        request_id=request_id,
        message="Validator creation in progress"
    )


@app.get("/validators/{request_id}", response_model=ValidatorStatusResponse)
async def get_validator_status(
    request_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve the status of a validator request by its UUID.
    If successful, includes a list of generated keys.
    """
    logger.info(f"Checking status for request {request_id}")
    
    # Get request
    result = await db.execute(
        select(ValidatorRequest).where(ValidatorRequest.request_id == request_id)
    )
    request = result.scalar_one_or_none()
    
    if not request:
        logger.warning(f"Request {request_id} not found")
        raise HTTPException(status_code=404, detail="Request not found")
    
    response_data = {"status": request.status}
    
    if request.status == "successful":
        # Get all keys for this request
        keys_result = await db.execute(
            select(ValidatorKey.key).where(ValidatorKey.request_id == request_id)
        )
        keys = [row[0] for row in keys_result.fetchall()]
        response_data["keys"] = keys
        logger.info(f"Request {request_id} is successful with {len(keys)} keys")
    elif request.status == "failed":
        response_data["message"] = "Error processing request"
        logger.info(f"Request {request_id} failed")
    
    return ValidatorStatusResponse(**response_data)


@app.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint to monitor system status and database connectivity.
    """
    try:
        # Test database connectivity
        await db.execute(select(1))
        logger.debug("Health check: Database connection successful")
        return HealthResponse(status="healthy", database="connected")
    except Exception as e:
        logger.error(f"Health check: Database connection failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Database connection failed")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)


