from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import asyncio
import uuid
from datetime import datetime
import logging
# Import functions dynamically to avoid immediate execution of module-level code
from . import auto_call_and_update
from .read_cancellation_dev import find_phone_by_client_policy

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Auto Call and Update API",
    description="API for automated VAPI calls with Smartsheet integration",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for call tracking (use Redis/DB in production)
call_sessions = {}

# Request/Response Models
class CallRequest(BaseModel):
    client_id: str = Field(..., description="Client ID from Smartsheet")
    policy_number: str = Field(..., description="Policy Number from Smartsheet")
    phone_number: Optional[str] = Field(None, description="Optional phone number (will lookup if not provided)")

class CallResponse(BaseModel):
    session_id: str = Field(..., description="Unique session ID for tracking")
    status: str = Field(..., description="Call status")
    message: str = Field(..., description="Status message")
    call_id: Optional[str] = Field(None, description="VAPI call ID")

class CallStatusResponse(BaseModel):
    session_id: str
    status: str
    call_id: Optional[str] = None
    call_data: Optional[Dict[Any, Any]] = None
    progress: str
    timestamp: datetime

class QuickCallRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number to call directly")

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Auto Call and Update API",
        "version": "1.0.0",
        "endpoints": {
            "POST /call/auto": "Start auto call workflow",
            "POST /call/quick": "Make quick call with phone number",
            "GET /call/status/{session_id}": "Get call status",
            "GET /call/{call_id}/status": "Get VAPI call status"
        }
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now()}

@app.post("/call/auto", response_model=CallResponse)
async def start_auto_call(request: CallRequest, background_tasks: BackgroundTasks):
    """
    Start the complete auto call workflow:
    1. Lookup phone number from Smartsheet (if not provided)
    2. Make VAPI call
    3. Monitor call status
    4. Update Smartsheet when call ends
    """
    try:
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Initialize session tracking
        call_sessions[session_id] = {
            "status": "initializing",
            "client_id": request.client_id,
            "policy_number": request.policy_number,
            "phone_number": request.phone_number,
            "call_id": None,
            "call_data": None,
            "progress": "Starting auto call workflow",
            "timestamp": datetime.now(),
            "error": None
        }
        
        # Start background task for the auto call workflow
        background_tasks.add_task(
            run_auto_call_workflow,
            session_id,
            request.client_id,
            request.policy_number,
            request.phone_number
        )
        
        logger.info(f"Started auto call workflow - Session: {session_id}, Client: {request.client_id}, Policy: {request.policy_number}")
        
        return CallResponse(
            session_id=session_id,
            status="initiated",
            message="Auto call workflow started successfully",
            call_id=None
        )
        
    except Exception as e:
        logger.error(f"Error starting auto call workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start auto call workflow: {str(e)}")

@app.post("/call/quick", response_model=CallResponse)
async def make_quick_call(request: QuickCallRequest, background_tasks: BackgroundTasks):
    """
    Make a quick VAPI call with just a phone number
    """
    try:
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Initialize session tracking
        call_sessions[session_id] = {
            "status": "calling",
            "phone_number": request.phone_number,
            "call_id": None,
            "call_data": None,
            "progress": "Making VAPI call",
            "timestamp": datetime.now(),
            "error": None
        }
        
        # Start background task for quick call
        background_tasks.add_task(
            run_quick_call,
            session_id,
            request.phone_number
        )
        
        logger.info(f"Started quick call - Session: {session_id}, Phone: {request.phone_number}")
        
        return CallResponse(
            session_id=session_id,
            status="calling",
            message="Quick call initiated successfully",
            call_id=None
        )
        
    except Exception as e:
        logger.error(f"Error making quick call: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to make quick call: {str(e)}")

@app.get("/call/status/{session_id}", response_model=CallStatusResponse)
async def get_call_status(session_id: str):
    """
    Get the current status of a call session
    """
    if session_id not in call_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = call_sessions[session_id]
    
    return CallStatusResponse(
        session_id=session_id,
        status=session["status"],
        call_id=session.get("call_id"),
        call_data=session.get("call_data"),
        progress=session["progress"],
        timestamp=session["timestamp"]
    )

@app.get("/call/{call_id}/status")
async def get_vapi_call_status(call_id: str):
    """
    Get current status directly from VAPI API
    """
    try:
        call_data = auto_call_and_update.check_call_status(call_id)
        if not call_data:
            raise HTTPException(status_code=404, detail="Call not found or API error")
        
        return {
            "call_id": call_id,
            "status": call_data.get("status", "unknown"),
            "data": call_data
        }
        
    except Exception as e:
        logger.error(f"Error getting VAPI call status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get call status: {str(e)}")

# Background task functions
async def run_auto_call_workflow(session_id: str, client_id: str, policy_number: str, phone_number: Optional[str] = None):
    """
    Background task to run the complete auto call workflow
    """
    try:
        # Update status
        call_sessions[session_id]["status"] = "processing"
        call_sessions[session_id]["progress"] = "Running auto call workflow"
        call_sessions[session_id]["timestamp"] = datetime.now()
        
        # Run the auto call workflow in a thread to avoid blocking
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(
            None,
            auto_call_and_update.auto_call_and_update,
            client_id,
            policy_number,
            phone_number
        )
        
        # Update final status
        if success:
            call_sessions[session_id]["status"] = "completed"
            call_sessions[session_id]["progress"] = "Workflow completed successfully"
        else:
            call_sessions[session_id]["status"] = "failed"
            call_sessions[session_id]["progress"] = "Workflow failed"
            
        call_sessions[session_id]["timestamp"] = datetime.now()
        
        logger.info(f"Auto call workflow completed - Session: {session_id}, Success: {success}")
        
    except Exception as e:
        call_sessions[session_id]["status"] = "error"
        call_sessions[session_id]["progress"] = f"Error: {str(e)}"
        call_sessions[session_id]["error"] = str(e)
        call_sessions[session_id]["timestamp"] = datetime.now()
        
        logger.error(f"Error in auto call workflow - Session: {session_id}, Error: {e}")

async def run_quick_call(session_id: str, phone_number: str):
    """
    Background task to make a quick VAPI call
    """
    try:
        # Update status
        call_sessions[session_id]["status"] = "calling"
        call_sessions[session_id]["progress"] = "Making VAPI call"
        call_sessions[session_id]["timestamp"] = datetime.now()
        
        # Make the call in a thread
        loop = asyncio.get_event_loop()
        call_id = await loop.run_in_executor(
            None,
            auto_call_and_update.make_vapi_call,
            phone_number
        )
        
        if call_id:
            call_sessions[session_id]["call_id"] = call_id
            call_sessions[session_id]["status"] = "active"
            call_sessions[session_id]["progress"] = f"Call initiated with ID: {call_id}"
            
            # Wait for call completion
            call_data = await loop.run_in_executor(
                None,
                auto_call_and_update.wait_for_call_completion,
                call_id
            )
            
            if call_data:
                call_sessions[session_id]["call_data"] = call_data
                call_sessions[session_id]["status"] = "completed"
                call_sessions[session_id]["progress"] = "Call completed"
            else:
                call_sessions[session_id]["status"] = "timeout"
                call_sessions[session_id]["progress"] = "Call monitoring timed out"
        else:
            call_sessions[session_id]["status"] = "failed"
            call_sessions[session_id]["progress"] = "Failed to initiate call"
            
        call_sessions[session_id]["timestamp"] = datetime.now()
        
        logger.info(f"Quick call completed - Session: {session_id}, Call ID: {call_id}")
        
    except Exception as e:
        call_sessions[session_id]["status"] = "error"
        call_sessions[session_id]["progress"] = f"Error: {str(e)}"
        call_sessions[session_id]["error"] = str(e)
        call_sessions[session_id]["timestamp"] = datetime.now()
        
        logger.error(f"Error in quick call - Session: {session_id}, Error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 