#!/usr/bin/env python3
"""
API Server Startup Script
Run this script to start the Auto Call and Update API server
"""

import sys
import os
import subprocess

# Add the parent directory to Python path so we can import from api package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def start_server(host="0.0.0.0", port=8000, reload=True):
    """Start the FastAPI server using uvicorn"""
    
    print("🚀 Starting Auto Call and Update API Server")
    print("="*50)
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Reload: {reload}")
    print(f"API Documentation: http://{host}:{port}/docs")
    print("="*50)
    
    # Build uvicorn command
    cmd = [
        "python3", "-m", "uvicorn", 
        "api.app:app",
        "--host", host,
        "--port", str(port)
    ]
    
    if reload:
        cmd.append("--reload")
    
    try:
        # Start the server
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start server: {e}")
        print("\n💡 Make sure you have installed all dependencies:")
        print("   pip install -r requirements.txt")
    except FileNotFoundError:
        print("❌ uvicorn not found. Please install dependencies:")
        print("   pip install -r requirements.txt")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Start the Auto Call and Update API server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to (default: 8000)")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")
    
    args = parser.parse_args()
    
    start_server(
        host=args.host,
        port=args.port,
        reload=not args.no_reload
    ) 