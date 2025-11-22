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

logger = setup_logger(__name__, 'base_image_tool.log')

class BaseImageTool(BaseTool):
    """Base class for image tools that handle image artifacts."""
    
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
        """Execute the search and return dict of {artifact_name: base64_image}."""
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
        images_base64 = await self._execute_search(args, tool_context)
        
        # Process and save artifacts
        artifact_names = await self._save_artifacts(images_base64, tool_context)
        
        return {
            "status": "success",
            "message": "Images added to tool context.",
            "artifact_name": artifact_names
        }
    
    async def _save_artifacts(
        self, 
        images_base64: Dict[str, str], 
        tool_context: ToolContext
    ) -> list[str]:
        """Save base64 images as artifacts and return their names."""
        artifact_names = []
        existing_artifacts = await tool_context.list_artifacts()
        
        for artifact_name, image in images_base64.items():
            if artifact_name in existing_artifacts:
                logger.info(f"Artifact {artifact_name} already exists. Skipping save.")
                artifact_names.append(artifact_name)
                continue
            
            # Decode base64 image
            base64_str = re.sub(r'^data:image/\w+;base64,', '', image)
            images_bytes = base64.b64decode(base64_str)
            
            # Create and save artifact
            report_artifact = types.Part.from_bytes(
                data=images_bytes, 
                mime_type="image/png"
            )
            await tool_context.save_artifact(artifact_name, report_artifact)
            logger.info(f"Saved artifact: {artifact_name}")
            artifact_names.append(artifact_name)
        
        return artifact_names
    
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
            
            llm_request.contents.append(
                types.Content(
                    role='user',
                    parts=[
                        types.Part.from_text(
                            text=f'Artifact {artifact_name} is:'
                        ),
                        artifact,
                    ],
                )
            )