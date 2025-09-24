# Auto Call and Update System

A comprehensive system for automated VAPI calls with Smartsheet integration. This project provides a complete workflow for making AI-powered phone calls and updating results in Smartsheet automatically.

## 🚀 Features

- **🤖 Auto Call Workflow**: Complete end-to-end automated calling process
- **📊 Smartsheet Integration**: Seamless data reading and result updating
- **🌐 REST API**: FastAPI-powered web service with real-time monitoring
- **📞 VAPI Integration**: AI-powered voice calls with monitoring
- **⚡ Asynchronous Processing**: Non-blocking operations with background tasks
- **📋 Session Management**: Track multiple concurrent calls
- **🧪 Comprehensive Testing**: Test suites and client examples

## 📁 Project Structure

```
python-read-write-sheet/
├── api/                          # Core API modules
│   ├── __init__.py
│   ├── app.py                    # FastAPI server
│   ├── auto_call_and_update.py   # Main workflow logic
│   └── read_cancellation_dev.py  # Smartsheet data operations
├── tests/                        # Testing and examples
│   ├── __init__.py
│   ├── api_client_example.py     # Interactive API client
│   ├── test_auto_call.py         # Auto call workflow tests
│   └── test_vapi_integration.py  # VAPI integration tests
├── docs/                         # Documentation
│   ├── API_README.md             # Detailed API documentation
│   └── LICENSE                   # License file
├── scripts/                      # Utility scripts
│   └── start_server.py           # Server startup script
├── requirements.txt              # Python dependencies
├── .env                          # Environment variables (create this)
└── README.md                     # This file
```

## 🛠️ Installation

### 1. Clone and Setup

```bash
git clone <repository-url>
cd python-read-write-sheet
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file in the project root:

```env
SMARTSHEET_ACCESS_TOKEN=your_smartsheet_token_here
```

**Get your Smartsheet token:**
1. Log into Smartsheet
2. Go to Account → Personal Settings → API Access
3. Generate a new access token

## 🚀 Quick Start

### Method 1: Using the Startup Script (Recommended)

```bash
python3 scripts/start_server.py
```

### Method 2: Direct uvicorn Command

```bash
python3 -m uvicorn api.app:app --reload --host 0.0.0.0 --port 8000
```

### Method 3: Using the Interactive Client

```bash
# Test the API with interactive client
python3 tests/api_client_example.py
```

## 📖 Usage

### 1. Web API Interface

Once the server is running, access:

- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### 2. Auto Call Workflow

Start a complete automated call workflow:

```bash
curl -X POST "http://localhost:8000/call/auto" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "24765",
    "policy_number": "BSNDP-2025-012160-01"
  }'
```

The system will automatically:
1. 🔍 Look up the phone number from Smartsheet
2. 📞 Make a VAPI call
3. 📊 Monitor call status in real-time
4. 📝 Update results back to Smartsheet when complete

### 3. Quick Call

Make a direct call with a phone number:

```bash
curl -X POST "http://localhost:8000/call/quick" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "3239435582"
  }'
```

### 4. Monitor Call Status

```bash
curl "http://localhost:8000/call/status/{session_id}"
```

## 🧪 Testing

### Run Individual Tests

```bash
# Test auto call workflow
python3 tests/test_auto_call.py

# Test VAPI integration (safe, no actual calls)
python3 tests/test_vapi_integration.py

# Interactive API testing
python3 tests/api_client_example.py
```

### Run Smartsheet Data Exploration

```bash
# Explore and search Smartsheet data
python3 api/read_cancellation_dev.py
```

## 📋 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API information and available endpoints |
| `GET` | `/health` | Health check endpoint |
| `POST` | `/call/auto` | Start auto call workflow |
| `POST` | `/call/quick` | Make quick call with phone number |
| `GET` | `/call/status/{session_id}` | Get call session status |
| `GET` | `/call/{call_id}/status` | Get VAPI call status directly |

## 🔧 Configuration

### Environment Variables

- `SMARTSHEET_ACCESS_TOKEN`: Your Smartsheet API access token

### API Configuration

The following are configured in `api/auto_call_and_update.py`:
- `VAPI_API_KEY`: VAPI API key
- `ASSISTANT_ID`: VAPI assistant ID  
- `PHONE_NUMBER_ID`: VAPI phone number ID

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Client    │    │   FastAPI       │    │   Smartsheet    │
│                 │◄──►│   Server        │◄──►│   API           │
│  (Browser/API)  │    │  (api/app.py)   │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   VAPI Service  │
                       │                 │
                       │ (Voice Calls)   │
                       └─────────────────┘
```

## 🔄 Workflow Process

1. **Input**: Client ID and Policy Number
2. **Lookup**: Find phone number in Smartsheet
3. **Call**: Initiate VAPI voice call
4. **Monitor**: Track call status and progress
5. **Update**: Write call results back to Smartsheet
6. **Response**: Return session status to client

## 📚 Documentation

- **Detailed API Docs**: See `docs/API_README.md`
- **Interactive Docs**: http://localhost:8000/docs (when server is running)
- **Code Documentation**: Inline comments and docstrings

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

See `docs/LICENSE` for license information.

## 🆘 Troubleshooting

### Common Issues

1. **Import Errors**: Make sure you're running commands from the project root
2. **Server Won't Start**: Check if port 8000 is available
3. **API Calls Fail**: Verify your Smartsheet access token is valid
4. **VAPI Errors**: Check VAPI credentials in the configuration

### Getting Help

- Check the logs in the terminal output
- Review `docs/API_README.md` for detailed troubleshooting
- Test individual components using the test files

---

**Made with ❤️ for automated customer communication**
