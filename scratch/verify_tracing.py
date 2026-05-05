import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.main import create_orchestrator

async def test_analyze():
    # Use current directory as test target
    target_path = str(Path(__file__).parent.parent.parent.resolve())
    print(f"Analyzing: {target_path}")
    
    orchestrator = create_orchestrator()
    request_id = "test-tracing-uuid-12345"
    
    try:
        result = await orchestrator.analyze(target_path, request_id=request_id)
        print("Analysis Successful!")
        print(f"Repository ID: {result['repository_id']}")
        
        # Check logs (this is manual, but we'll see if the script finishes without error)
        print("\nChecking log correlation...")
        log_file = Path("logs/CodeCortex.Domain.CodeIndex.log")
        if log_file.exists():
            with open(log_file, "r") as f:
                last_lines = f.readlines()[-10:]
                found = any(request_id in line for line in last_lines)
                print(f"Request ID '{request_id}' found in Index logs: {found}")
    except Exception as e:
        print(f"Analysis Failed: {e}")
    finally:
        orchestrator.db.close()

if __name__ == "__main__":
    asyncio.run(test_analyze())
