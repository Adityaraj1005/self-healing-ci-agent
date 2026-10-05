import os
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from graph_agent import app as repair_graph

server = FastAPI(
    title="Autonomous Self-Healing CI/CD Agent Webhook",
    description="Listens for test failure webhooks and triggers the LangGraph repair loop.",
    version="1.0.0"
)

# 1. Incoming webhook payload schema
class WebhookPayload(BaseModel):
    repo_name: str
    branch: str = "main"
    trigger_reason: str = "test_failure"

# 2. Background task running the state graph
def run_repair_workflow(repo_path: str):
    print(f"\n🔔 [Webhook Triggered] Launching StateGraph Repair Workflow on '{repo_path}'...")
    initial_state = {
        "repo_path": repo_path,
        "test_passed": False,
        "error_logs": "",
        "iteration": 0,
        "max_iterations": 3,
    }
    result = repair_graph.invoke(initial_state)
    print(f"\n✅ [Workflow Completed] Final Status: {'PASSED ✅' if result['test_passed'] else 'FAILED ❌'}")
    print(f"Total Iterations Used: {result['iteration']}")

# 3. Health check endpoint
@server.get("/")
def health_check():
    return {
        "status": "online",
        "service": "Self-Healing CI Webhook Engine",
        "supported_nodes": ["run_tests", "patch_code"]
    }

# 4. CI/CD Webhook receiver endpoint
@server.post("/webhook")
def handle_ci_webhook(payload: WebhookPayload, background_tasks: BackgroundTasks):
    target_repo = "sandbox_repo"
    
    if not os.path.exists(target_repo):
        raise HTTPException(status_code=404, detail=f"Target repository '{target_repo}' not found on host.")

    background_tasks.add_task(run_repair_workflow, target_repo)

    return {
        "status": "accepted",
        "message": f"Autonomous repair graph queued for repo '{payload.repo_name}' on branch '{payload.branch}'.",
        "trigger": payload.trigger_reason
    }

if __name__ == "__main__":
    import uvicorn
    # reload=False prevents uvicorn from restarting when the agent patches code on disk
    uvicorn.run(server, host="127.0.0.1", port=8000, reload=False)