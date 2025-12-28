# base_search_tool.py
from typing import Any, Dict
from abc import abstractmethod
from google.genai import types
import re
import base64
import binascii

from google.adk.tools.base_tool import BaseTool
from google.adk.models.llm_request import LlmRequest
from google.adk.tools.tool_context import ToolContext
from ...utils.logger import setup_logger

logger = setup_logger(__name__, "base_artifact_tool.log")


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
    async def _execute_search(
        self, args: dict[str, Any], tool_context: ToolContext
    ) -> Dict[str, str]:
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

    async def run_async(
        self, *, args: dict[str, Any], tool_context: ToolContext
    ) -> Any:
        """Common implementation for running search and saving artifacts."""
        logger.info(f"EXECUTING {self.name} with args: {args}")

        # Execute search (implemented by subclass)

        raw_artifacts = await self._execute_search(args, tool_context)

        # Process and save artifacts
        text_content = raw_artifacts.pop("text", None)

        saved_artifact_names = await self._save_artifacts(raw_artifacts, tool_context)

        response = {
            "status": "success",
            "message": "Artifacts added to tool context.",
            "artifact_name": saved_artifact_names,
        }

        if text_content:
            response["text"] = text_content

        return response

    async def _save_artifacts(
        self, artifacts_data: Dict[str, str], tool_context: ToolContext
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
            is_image = False
            image_data = None
            mime_type = "image/png"  # Default

            # Check for data
            if re.match(r"^data:image/\w+;base64,", data_string):
                try:
                    base64_str = re.sub(r"^data:image/\w+;base64,", "", data_string)
                    image_data = base64.b64decode(base64_str)
                    mime_match = re.match(r"^data:(image/\w+);base64,", data_string)
                    if mime_match:
                        mime_type = mime_match.group(1)
                    is_image = True
                except Exception as e:
                    logger.warning(
                        f"Failed to decode data URI for {artifact_name}: {e}"
                    )

            # Check for raw base64 (if not already identified)
            if not is_image:
                if len(data_string) > 100 and " " not in data_string[:100]:
                    try:
                        decoded = base64.b64decode(data_string, validate=True)
                        if decoded.startswith(b"\x89PNG\r\n\x1a\n"):
                            mime_type = "image/png"
                            is_image = True
                            image_data = decoded
                        elif decoded.startswith(b"\xff\xd8"):
                            mime_type = "image/jpeg"
                            is_image = True
                            image_data = decoded
                        elif decoded.startswith(b"GIF87a") or decoded.startswith(
                            b"GIF89a"
                        ):
                            mime_type = "image/gif"
                            is_image = True
                            image_data = decoded
                        elif decoded.startswith(b"RIFF") and decoded[8:12] == b"WEBP":
                            mime_type = "image/webp"
                            is_image = True
                            image_data = decoded
                    except Exception:
                        pass

            if is_image and image_data:
                try:
                    artifact_part = types.Part.from_bytes(
                        data=image_data, mime_type=mime_type
                    )
                    logger.info(
                        f"Created image part for {artifact_name} with mime_type {mime_type}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Could not create image part for {artifact_name}: {e}. Treating as text."
                    )
                    artifact_part = types.Part.from_text(text=data_string)
            else:
                # Assume it's plain text
                artifact_part = types.Part.from_text(text=data_string)

            if artifact_part:
                await tool_context.save_artifact(artifact_name, artifact_part)
                logger.info(f"Saved artifact: {artifact_name}")
                saved_artifact_names.append(artifact_name)
            else:
                logger.error(f"Failed to create artifact part for {artifact_name}.")

        return saved_artifact_names

    async def process_llm_request(
        self, *, tool_context: ToolContext, llm_request: LlmRequest
    ) -> None:
        """Load and attach artifacts to LLM request after tool execution."""
        await super().process_llm_request(
            tool_context=tool_context, llm_request=llm_request
        )

        if not (llm_request.contents and llm_request.contents[-1].parts):
            return

        function_response = llm_request.contents[-1].parts[0].function_response
        if not function_response or function_response.name != self.name:
            return

        artifact_names = function_response.response.get("artifact_name", [])
        for artifact_name in artifact_names:
            artifact = await tool_context.load_artifact(artifact_name)
            if artifact is None:
                logger.warning(f'Artifact "{artifact_name}" not found')
                continue

            logger.info(f"Loaded artifact {artifact_name}: type={type(artifact)}")
            if hasattr(artifact, "text") and artifact.text:
                logger.info(
                    f"Artifact {artifact_name} has text content (length {len(artifact.text)})"
                )
            if hasattr(artifact, "inline_data"):
                logger.info(
                    f"Artifact {artifact_name} has inline_data (mime_type={getattr(artifact.inline_data, 'mime_type', 'unknown')})"
                )

            parts_to_add = []
            parts_to_add.append(
                types.Part.from_text(text=f'Artifact "{artifact_name}" is:')
            )

            if artifact.text:
                text_content = artifact.text.strip()
                is_image_text = False
                image_part_from_text = None

                # Check data URI in text
                if (
                    text_content.startswith("data:image/")
                    and ";base64," in text_content[:50]
                ):
                    try:
                        base64_str = text_content.split(";base64,")[1]
                        image_bytes = base64.b64decode(base64_str)
                        mime_type = text_content.split(";base64,")[0].replace(
                            "data:", ""
                        )
                        image_part_from_text = types.Part.from_bytes(
                            data=image_bytes, mime_type=mime_type
                        )
                        is_image_text = True
                        logger.info(
                            f"Converted text artifact {artifact_name} to image part (Data URI)"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to convert text artifact {artifact_name} to image: {e}"
                        )

                # Check raw base64 in text (heuristic)
                elif len(text_content) > 100 and " " not in text_content[:100]:
                    try:
                        decoded = base64.b64decode(text_content, validate=True)
                        detected_mime = None
                        if decoded.startswith(b"\x89PNG\r\n\x1a\n"):
                            detected_mime = "image/png"
                        elif decoded.startswith(b"\xff\xd8"):
                            detected_mime = "image/jpeg"
                        elif decoded.startswith(b"GIF87a") or decoded.startswith(
                            b"GIF89a"
                        ):
                            detected_mime = "image/gif"
                        elif decoded.startswith(b"RIFF") and decoded[8:12] == b"WEBP":
                            detected_mime = "image/webp"

                        if detected_mime:
                            image_part_from_text = types.Part.from_bytes(
                                data=decoded, mime_type=detected_mime
                            )
                            is_image_text = True
                            logger.info(
                                f"Converted text artifact {artifact_name} to image part (Raw Base64, mime={detected_mime})"
                            )
                    except Exception:
                        pass

                if is_image_text and image_part_from_text:
                    parts_to_add.append(image_part_from_text)
                else:
                    parts_to_add.append(types.Part.from_text(text=artifact.text))
            else:
                parts_to_add.append(artifact)

            llm_request.contents.append(
                types.Content(
                    role="user",
                    parts=parts_to_add,
                )
            )
