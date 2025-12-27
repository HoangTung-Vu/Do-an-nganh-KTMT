import os
import sys
import asyncio
import base64
import json
from typing import Literal, Optional, Any
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService, DatabaseSessionService
from google.adk.agents import BaseAgent
from google.genai import types
from src.utils.logger import setup_logger
from pathlib import Path
from google.adk.runners import InMemoryArtifactService
from google.adk.artifacts import GcsArtifactService
from google.adk.agents.run_config import RunConfig, StreamingMode


from ..utils.load_config import load_config

config = load_config()
logger = setup_logger(__name__, "agent_manager.log")


class ChatAgentManager:
    """Singleton manager for chat agent - should be created once at app startup"""

    def __init__(
        self,
        app_name: str,
        agent_flow: BaseAgent,
        session_service_name: Literal["database", "in_memory"] = "in_memory",
        artifact_service_name: Literal["gcs", "in_memory"] = "in_memory",
    ):
        """
        Initialize manager with shared services.

        Args:
            agent_flow: The agent to run
            session_service: Shared session service (DatabaseSessionService or InMemorySessionService)
            artifact_service: Shared artifact service (GcsArtifactService or InMemoryArtifactService)
            app_name: Application name
        """
        if session_service_name == "database":
            session_service = DatabaseSessionService(db_url=config["database"]["url"])
        else:
            session_service = InMemorySessionService()

        if artifact_service_name == "gcs":
            artifact_service = GcsArtifactService(
                bucket_name=config["gcs"]["bucket_name"]
            )
        else:
            artifact_service = InMemoryArtifactService()

        self._runner = Runner(
            agent=agent_flow,
            app_name=app_name,
            session_service=session_service,
            artifact_service=artifact_service,
        )
        self._app_name = app_name
        self._session_service = session_service
        self._artifact_service = artifact_service

    async def check_session(
        self,
        user_id: str,
        session_id: str,
        initial_state: Optional[dict[str, Any]] = None,
    ):
        """
        Prepare session by checking if it exists, create new one if not.

        Args:
            user_id: User identifier
            session_id: Session identifier
            initial_state: Optional initial state for new session

        Returns:
            Session object (existing or newly created)
        """
        # Try to get existing session
        session = await self._session_service.get_session(
            app_name=self._app_name, user_id=user_id, session_id=session_id
        )

        # Create new session if not exists
        if session is None:
            session = await self._session_service.create_session(
                app_name=self._app_name,
                user_id=user_id,
                state=initial_state or {},
                session_id=session_id,
            )
            logger.info(f"Created new session: {session_id} for user: {user_id}")
        else:
            logger.info(f"Using existing session: {session_id} for user: {user_id}")

    async def run_workflow(
        self, user_id: str, session_id: str, query: str, db_name: Optional[str] = None
    ) -> dict:
        """
        Run workflow for a specific user/session.

        Args:
            user_id: User identifier
            session_id: Session identifier
            query: User query
            db_name: Database name for retrieval (stored in session state)
        """
        try:
            # Prepare state delta if db_name provided
            state_delta = {}
            if db_name:
                state_delta["db_name"] = db_name
                state_delta["original_user_id"] = user_id

            content = types.Content(role="user", parts=[types.Part(text=query)])

            await self.check_session(
                user_id=user_id, session_id=session_id, initial_state=state_delta
            )

            final_response = "No final response captured."

            async for event in self._runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=content,
                state_delta=state_delta,
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    logger.info(f"Final response from [{event.author}]")
                    final_response = event.content.parts[0].text

            # Get artifacts
            artifacts = await self.get_artifacts(user_id, session_id)
            logger.info(f"Retrieved {len(artifacts)} artifacts")

            return {"response": final_response, "artifacts": artifacts}

        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            return {"response": None, "artifacts": []}

    async def get_artifacts(self, user_id: str, session_id: str) -> list:
        """Get all artifacts for a specific user/session."""
        artifacts = []
        if self._artifact_service:
            try:
                session_artifacts = await self._artifact_service.list_artifact_keys(
                    app_name=self._app_name, user_id=user_id, session_id=session_id
                )

                for artifact_name in session_artifacts:
                    artifact_data = await self._artifact_service.load_artifact(
                        app_name=self._app_name,
                        user_id=user_id,
                        session_id=session_id,
                        filename=artifact_name,
                    )

                    if artifact_data and hasattr(artifact_data, "inline_data"):
                        blob = artifact_data.inline_data
                        if hasattr(blob, "data") and hasattr(blob, "mime_type"):
                            base64_data = base64.b64encode(blob.data).decode("utf-8")
                            artifacts.append(
                                {
                                    "name": artifact_name,
                                    "type": (
                                        "image"
                                        if blob.mime_type.startswith("image/")
                                        else "other"
                                    ),
                                    "mime_type": blob.mime_type,
                                    "data": f"data:{blob.mime_type};base64,{base64_data}",
                                }
                            )

                    await self._artifact_service.delete_artifact(
                        app_name=self._app_name,
                        user_id=user_id,
                        session_id=session_id,
                        filename=artifact_name,
                    )

            except Exception as e:
                logger.error(f"Error retrieving artifacts: {e}", exc_info=True)

        return artifacts

    async def cleanup(self):
        """Cleanup runner resources."""
        try:
            if self._runner:
                await self._runner.close()
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")

    async def cleanup_session(self, user_id: str, session_id: str):
        """Delete session after use"""
        try:
            await self._session_service.delete_session(
                app_name=self._app_name, user_id=user_id, session_id=session_id
            )
            logger.info(f"Deleted session: {session_id} for user: {user_id}")
        except Exception as e:
            logger.warning(f"Error deleting session: {e}")
