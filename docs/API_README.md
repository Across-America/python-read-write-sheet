# Auto Call and Update API

A FastAPI server that exposes the auto call workflow for automated VAPI calls with Smartsheet integration.

## 🚀 Features

- **Auto Call Workflow**: Complete end-to-end process with Smartsheet integration
- **Quick Calls**: Direct VAPI calls with phone numbers
- **Real-time Monitoring**: Track call progress and status
- **Asynchronous Processing**: Non-blocking API calls with background tasks
- **Session Management**: Track multiple concurrent calls
- **Comprehensive Logging**: Detailed logging for debugging and monitoring

## 📋 API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API information and available endpoints |
| `GET` | `/health` | Health check endpoint |
| `POST` | `/call/auto` | Start auto call workflow |
| `POST` | `/call/quick` | Make quick call with phone number |
| `GET` | `/call/status/{session_id}` | Get call session status |
| `GET` | `/call/{call_id}/status` | Get VAPI call status directly |

### Documentation
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🛠️ Installation & Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file with your configuration:

```env
SMARTSHEET_ACCESS_TOKEN=your_smartsheet_token_here
```

### 3. Start the Server

```bash
# Using uvicorn (recommended for development)
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Or using Python directly
python app.py
```

The server will be available at `http://localhost:8000`

## 📖 Usage Examples

### 1. Auto Call Workflow

Start a complete workflow that automatically:
- Looks up phone number from Smartsheet
- Makes VAPI call
- Monitors call status
- Updates Smartsheet when call ends

```bash
curl -X POST "http://localhost:8000/call/auto" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "24765",
    "policy_number": "BSNDP-2025-012160-01"
  }'
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "initiated",
  "message": "Auto call workflow started successfully",
  "call_id": null
}
```

### 2. Quick Call

Make a direct call with just a phone number:

```bash
curl -X POST "http://localhost:8000/call/quick" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "3239435582"
  }'
```

### 3. Monitor Call Status

Check the progress of a call session:

```bash
curl "http://localhost:8000/call/status/550e8400-e29b-41d4-a716-446655440000"
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "call_id": "vapi_call_123",
  "call_data": {
    "status": "ended",
    "endedReason": "customer-ended-call",
    "cost": 0.0234
  },
  "progress": "Call completed successfully",
  "timestamp": "2025-09-17T10:30:00"
}
```

## 🔄 Call Status Flow

1. **initiated** → Workflow started
2. **processing** → Looking up phone number / Making call
3. **calling** → VAPI call in progress
4. **active** → Call connected and running
5. **completed** → Call finished successfully
6. **failed** → Call or workflow failed
7. **error** → System error occurred
8. **timeout** → Call monitoring timed out

## 🧪 Testing with Python Client

Use the provided `api_client_example.py` for interactive testing:

```bash
python api_client_example.py
```

This provides:
- Interactive menu for testing all endpoints
- Auto call workflow demos
- Quick call demos
- Status monitoring
- Health checks

## 📊 Request/Response Models

### CallRequest
```json
{
  "client_id": "string",
  "policy_number": "string", 
  "phone_number": "string (optional)"
}
```

### QuickCallRequest
```json
{
  "phone_number": "string"
}
```

### CallResponse
```json
{
  "session_id": "string",
  "status": "string",
  "message": "string",
  "call_id": "string | null"
}
```

### CallStatusResponse
```json
{
  "session_id": "string",
  "status": "string",
  "call_id": "string | null",
  "call_data": "object | null",
  "progress": "string",
  "timestamp": "datetime"
}
```

## 🔧 Configuration

### Environment Variables
- `SMARTSHEET_ACCESS_TOKEN`: Your Smartsheet API token

### API Configuration (in `app.py`)
- `VAPI_API_KEY`: VAPI API key
- `ASSISTANT_ID`: VAPI assistant ID
- `PHONE_NUMBER_ID`: VAPI phone number ID

## 🚦 Production Considerations

### Security
- [ ] Configure CORS origins for production
- [ ] Add authentication middleware
- [ ] Validate and sanitize inputs
- [ ] Rate limiting

### Scalability
- [ ] Use Redis/Database for session storage instead of in-memory
- [ ] Add connection pooling
- [ ] Implement proper error retry logic
- [ ] Add metrics and monitoring

### Deployment
- [ ] Use production ASGI server (gunicorn + uvicorn)
- [ ] Configure proper logging
- [ ] Add health check endpoints for load balancers
- [ ] Set up monitoring and alerting

## 🏃‍♂️ Quick Start Example

```python
import requests

# Start auto call workflow
response = requests.post("http://localhost:8000/call/auto", json={
    "client_id": "24765",
    "policy_number": "BSNDP-2025-012160-01"
})
session_id = response.json()["session_id"]

# Monitor progress
import time
while True:
    status = requests.get(f"http://localhost:8000/call/status/{session_id}").json()
    print(f"Status: {status['status']} - {status['progress']}")
    
    if status["status"] in ["completed", "failed", "error"]:
        break
    time.sleep(5)
```

## 🐛 Troubleshooting

### Common Issues

1. **API Server Not Starting**
   - Check if port 8000 is available
   - Verify all dependencies are installed
   - Check environment variables

2. **Calls Failing**
   - Verify VAPI credentials
   - Check phone number format
   - Ensure Smartsheet access token is valid

3. **Session Not Found**
   - Sessions are stored in memory and reset on server restart
   - Use proper session IDs returned from API calls

### Logs
The server logs all operations. Check console output for detailed error messages.

## 📄 License

This project follows the same license as the parent repository.

---

## 🔗 Related Files

- `app.py` - Main FastAPI server
- `api_client_example.py` - Python client example
- `auto_call_and_update.py` - Core workflow implementation
- `requirements.txt` - Python dependencies 