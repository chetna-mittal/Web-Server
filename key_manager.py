import secrets
import asyncio
import logging
from typing import List

logger = logging.getLogger(__name__)


class MockKeyManager:
    """Mock key manager that simulates validator key generation"""
    
    @staticmethod
    async def generate_key() -> str:
        """
        Generate a random validator key (simulated).
        Introduces a 20ms delay to simulate processing.
        """
        await asyncio.sleep(0.02)  # 20ms delay
        key = secrets.token_hex(16)
        logger.debug(f"Generated key: {key[:16]}...")
        return key
    
    @staticmethod
    async def generate_keys(num_keys: int) -> List[str]:
        """
        Generate multiple validator keys with 20ms delay per key.
        """
        keys = []
        for i in range(num_keys):
            key = await MockKeyManager.generate_key()
            keys.append(key)
            logger.debug(f"Generated key {i+1}/{num_keys}")
        return keys

