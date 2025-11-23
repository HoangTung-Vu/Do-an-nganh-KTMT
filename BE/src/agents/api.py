from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from .agent_manager import ChatAgentManager
from .agent_setup import create_agent
from ..utils.logger import setup_logger

router = APIRouter(prefix="/agent", tags=["Agent Interaction"])
logger = setup_logger('agent_api', 'agent_api.log')

# Global instance
_agent_manager: Optional[ChatAgentManager] = None

def get_agent_manager() -> ChatAgentManager:
    """Get or create agent manager singleton"""
    global _agent_manager
    if _agent_manager is None:
        agent = create_agent()
        _agent_manager = ChatAgentManager(
            app_name="control_theory_app",
            agent_flow=agent
        )
    return _agent_manager

class ChatRequest(BaseModel):
    user_id: str
    session_id: str
    query: str
    db_name: Optional[str] = None

class ChatResponse(BaseModel):
    response: Optional[str]
    artifacts: list

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the agent and get a response.
    """
    try:
        manager = get_agent_manager()
        
        result = await manager.run_workflow(
            user_id=request.user_id,
            session_id=request.session_id,
            query=request.query,
            db_name=request.db_name
        )
        
        return ChatResponse(
            response=result.get("response"),
            artifacts=result.get("artifacts", [])
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/session/{user_id}/{session_id}")
async def delete_session(user_id: str, session_id: str):
    """
    Delete a chat session.
    """
    try:
        manager = get_agent_manager()
        await manager.cleanup_session(user_id, session_id)
        return {"message": f"Session {session_id} deleted"}
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
