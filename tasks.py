import asyncio
import logging
from sqlalchemy import select
from database import AsyncSessionLocal, ValidatorRequest, ValidatorKey
from key_manager import MockKeyManager
logger = logging.getLogger(__name__)


async def process_validator_creation(request_id: str, num_validators: int, fee_recipient: str):
    """
    Asynchronous task to process validator creation.
    Generates keys one by one, stores them, and updates request status.
    """
    try:
        logger.info(f"Starting validator creation task for request {request_id}")
        
        # Process each validator one by one (matching Go implementation)
        for _ in range(num_validators):
            # Generate key with 20ms delay
            key = await MockKeyManager.generate_key()
            
            # Store each generated key with its fee recipient immediately
            async with AsyncSessionLocal() as session:
                validator_key = ValidatorKey(
                    request_id=request_id,
                    key=key,
                    fee_recipient=fee_recipient
                )
                session.add(validator_key)
                try:
                    await session.commit()
                except Exception as e:
                    logger.error(f"Failed to store key for request {request_id}: {str(e)}")
                    # Update status to failed
                    await update_request_status(request_id, "failed")
                    return
        
        # Update request status to successful upon completion
        await update_request_status(request_id, "successful")
        logger.info(f"Successfully completed validator creation for request {request_id}")
                
    except Exception as e:
        logger.error(f"Error processing validator creation for request {request_id}: {str(e)}", exc_info=True)
        # Update request status to failed
        await update_request_status(request_id, "failed")


async def update_request_status(request_id: str, status: str):
    """Helper function to update request status"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ValidatorRequest).where(ValidatorRequest.request_id == request_id)
            )
            request = result.scalar_one_or_none()
            
            if request:
                request.status = status
                await session.commit()
                logger.info(f"Updated request {request_id} status to {status}")
            else:
                logger.error(f"Request {request_id} not found in database")
    except Exception as e:
        logger.error(f"Failed to update request {request_id} status to {status}: {str(e)}")


def spawn_validator_task(request_id: str, num_validators: int, fee_recipient: str):
    """
    Spawn an async task to process validator creation in the background.
    """
    asyncio.create_task(process_validator_creation(request_id, num_validators, fee_recipient))


