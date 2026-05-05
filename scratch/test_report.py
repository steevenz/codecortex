import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.main import create_orchestrator

async def test_report():
    orchestrator = create_orchestrator()
    request_id = "report-test-uuid-999"
    repo_id = "326f2fcb-d3e4-481c-9bc6-dc564001c5b4"
    
    print(f"Generating report for Repo: {repo_id} with Trace: {request_id}")
    
    try:
        # We call the internal service directly to test logging in mixins
        report = await orchestrator.graph_service.build_comprehensive_report(repo_id, request_id=request_id)
        print("\nReport Generated Successfully!")
        print("-" * 20)
        summary = report.get("summary", "")
        print(summary[:500] + "...") # Print first 500 chars of summary
        print("-" * 20)
        
        # Check if temporal coupling section exists
        if "Temporal Coupling" in report:
            print("SUCCESS: Temporal Coupling section found in report.")
        else:
            print("INFO: No Temporal Coupling found (this is normal if no history exists).")
            
    except Exception as e:
        import traceback
        print(f"Report Generation Failed: {e}")
        traceback.print_exc()
    finally:
        orchestrator.db.close()

if __name__ == "__main__":
    asyncio.run(test_report())
