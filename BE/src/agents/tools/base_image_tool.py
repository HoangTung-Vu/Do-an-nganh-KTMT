# base_search_tool.py
from typing import Any, Dict
from abc import abstractmethod
from google.genai import types
import re
import base64

from google.adk.tools.base_tool import BaseTool
from google.adk.models.llm_request import LlmRequest
from google.adk.tools.tool_context import ToolContext
from ...utils.logger import setup_logger

logger = setup_logger(__name__, 'base_artifact_tool.log')

class BaseArtifactTool(BaseTool):
    """Base class for tools that handle various types of artifacts (images, text)."""
    
    def __init__(self, name: str, description: str, search_instance):
        super().__init__(name=name, description=description)
        self.search_instance = search_instance
    
    @abstractmethod
    def _get_search_params_schema(self) -> Dict[str, types.Schema]:
        """Define the parameters schema for the search operation."""
        pass
    
    @abstractmethod
    def _get_required_params(self) -> list[str]:
        """Define required parameters for the search operation."""
        pass
    
    @abstractmethod
    async def _execute_search(self, args: dict[str, Any], tool_context: ToolContext) -> Dict[str, str]:
        """
        Execute the search and return a dict of {artifact_name: data_string}.
        Data strings can be base64-encoded images or plain text.
        """
        pass
    
    def _get_declaration(self) -> types.FunctionDeclaration | None:
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties=self._get_search_params_schema(),
                required=self._get_required_params(),
            ),
        )
    
    async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
        """Common implementation for running search and saving artifacts."""
        logger.info(f"EXECUTING {self.name} with args: {args}")
        
        # Execute search (implemented by subclass)
        # _execute_search now returns a dict that can contain both base64 images and plain text
        raw_artifacts = await self._execute_search(args, tool_context)
        
        # Process and save artifacts
        saved_artifact_names = await self._save_artifacts(raw_artifacts, tool_context)
        
        return {
            "status": "success",
            "message": "Artifacts added to tool context.",
            "artifact_name": saved_artifact_names # Renamed for clarity
        }
    
    async def _save_artifacts(
        self, 
        artifacts_data: Dict[str, str], 
        tool_context: ToolContext
    ) -> list[str]:
        """Save various types of data as artifacts and return their names."""
        saved_artifact_names = []
        existing_artifacts = await tool_context.list_artifacts()
        
        for artifact_name, data_string in artifacts_data.items():
            if artifact_name in existing_artifacts:
                logger.info(f"Artifact {artifact_name} already exists. Skipping save.")
                saved_artifact_names.append(artifact_name)
                continue
            
            artifact_part = None
            # Heuristic to determine if it's a base64 image or plain text
            if re.match(r'^data:image/\w+;base64,', data_string):
                try:
                    base64_str = re.sub(r'^data:image/\w+;base64,', '', data_string)
                    images_bytes = base64.b64decode(base64_str)
                    # Attempt to guess MIME type, default to png if not specified in data URI
                    mime_match = re.match(r'^data:(image/\w+);base64,', data_string)
                    mime_type = mime_match.group(1) if mime_match else "image/png"
                    artifact_part = types.Part.from_bytes(data=images_bytes, mime_type=mime_type)
                except Exception as e:
                    logger.warning(f"Could not decode base64 for artifact {artifact_name}: {e}. Treating as text.")
                    artifact_part = types.Part.from_text(text=data_string)
            else:
                # Assume it's plain text if not a base64 image URI
                artifact_part = types.Part.from_text(text=data_string)
            
            if artifact_part:
                await tool_context.save_artifact(artifact_name, artifact_part)
                logger.info(f"Saved artifact: {artifact_name} (Type: {artifact_part.mime_type or 'text/plain'})")
                saved_artifact_names.append(artifact_name)
            else:
                logger.error(f"Failed to create artifact part for {artifact_name}.")
        
        return saved_artifact_names
    
    async def process_llm_request(
        self, 
        *, 
        tool_context: ToolContext, 
        llm_request: LlmRequest
    ) -> None:
        """Load and attach artifacts to LLM request after tool execution."""
        # Call parent implementation
        await super().process_llm_request(
            tool_context=tool_context,
            llm_request=llm_request
        )
        
        # Check if this tool was just called
        if not (llm_request.contents and llm_request.contents[-1].parts):
            return
        
        function_response = llm_request.contents[-1].parts[0].function_response
        if not function_response or function_response.name != self.name:
            return
        
        # Load and attach artifacts
        artifact_names = function_response.response.get('artifact_name', [])
        for artifact_name in artifact_names:
            artifact = await tool_context.load_artifact(artifact_name)
            if artifact is None:
                logger.warning(f'Artifact "{artifact_name}" not found')
                continue
            
            # Attach artifact based on its type
            parts_to_add = []
            parts_to_add.append(types.Part.from_text(text=f'Artifact "{artifact_name}" is:'))
            
            # If the artifact is text, append the text content directly
            # Otherwise, append the artifact object itself (for images, etc.)
            if artifact.text:
                parts_to_add.append(types.Part.from_text(text=artifact.text))
            else:
                parts_to_add.append(artifact)
            
            llm_request.contents.append(
                types.Content(
                    role='user',
                    parts=parts_to_add,
                )
            )


