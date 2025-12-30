# Validator API

A backend API for managing validator creation requests, implemented in Python using FastAPI.

## Features

- **Validator Request Management**: Create and track validator creation requests with UUID identifiers
- **Asynchronous Processing**: Background task processing with 20ms delay per key generation
- **Status Tracking**: Monitor request status (started, successful, failed)
- **Database Persistence**: SQLite database for storing requests and generated keys
- **Validation**: Ethereum address format validation and positive number validation
- **Health Check**: Monitor system status and database connectivity
- **Logging**: Comprehensive logging throughout the application

## Tech Stack

- **Framework**: FastAPI
- **Database**: SQLite (with aiosqlite for async support)
- **Testing**: pytest with pytest-asyncio

## Project Structure

```
.
├── main.py              # FastAPI application and endpoints
├── database.py          # Database models and connection setup
├── models.py            # Pydantic models for request/response validation
├── key_manager.py       # Mock key manager for generating validator keys
├── tasks.py             # Async task processing for validator creation
├── test_main.py         # Unit tests
├── requirements.txt     # Python dependencies
├── pytest.ini           # Pytest configuration
└── README.md            # This file
```

## Setup and Installation

### Prerequisites

- Python 3.11 or higher

### Local Development

1. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application**:

   ```bash
   python main.py
   ```

3. **Access the API**:
   - API: http://localhost:8080
   - Create Validators API: http://localhost:8080/validators
   - Get Validator Details: http://localhost:8080/validators/{requestID}
   - API Documentation: http://localhost:8080/docs
   - Health Check: http://localhost:8080/health

## API Endpoints

### 1. Create Validator Request

**POST** `/validators`

Creates a new validator creation request and returns immediately with a UUID.

**Request Body**:

```json
{
  "num_validators": 5,
  "fee_recipient": "0x1234567890abcdef1234567890abcdef12345678"
}
```

**Response** (202 Accepted):

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Validator creation in progress"
}
```

**Validation**:
- `num_validators`: Must be a positive integer (> 0)
- `fee_recipient`: Must be a valid Ethereum address (0x followed by 40 hex characters)

### 2. Check Request Status

**GET** `/validators/{request_id}`

Retrieves the status of a validator request by its UUID.

**Response (Successful)**:
```json
{
  "status": "successful",
  "keys": [
    "key1",
    "key2",
    "key3"
  ]
}
```

**Response (Failed)**:

```json
{
  "status": "failed",
  "message": "Error processing request"
}
```

**Response (In Progress)**:

```json
{
  "status": "started"
}
```

### 3. Health Check

**GET** `/health`

Monitors system status and database connectivity.

**Response**:

```json
{
  "status": "ok"
}
```

## Asynchronous Task Processing

When a validator request is created:

1. The request is immediately saved to the database with status **started**
2. An async task is spawned to process validator creation in the background
3. For each validator:
   - A random key is generated (32-character hex string)
   - A 20ms delay is introduced to simulate processing
   - The key is stored in the database with its fee recipient
4. Upon completion, the request status is updated to **successful**
5. If any error occurs, the status is updated to **failed**