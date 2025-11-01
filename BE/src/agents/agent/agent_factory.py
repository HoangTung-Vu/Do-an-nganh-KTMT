from google.adk.models.lite_llm import LiteLlm
from google.adk.agents import LlmAgent
from google.genai.types import GenerateContentConfig
from typing import Literal

import os
from dotenv import load_dotenv
from ...utils.load_config import load_config 
from src.utils.logger import setup_logger
from pathlib import Path



logger = setup_logger(__name__, 'agent.log')

load_dotenv()
config = load_config()

def before_callback(callback_context): 
    logger.info(f"Before callback: {callback_context}")
    logger.info("Agent initiated")

def after_callback(callback_context):
    logger.info(f"After callback: {callback_context}")
    logger.info("Agent finished")


def make_subagent(agent_name : str,
    system_prompt : str,
    description : str,
    llm_choice : Literal["gemini", "openai"] = "gemini",
    model_name : str = "gemini-2.0-flash",
    temperature : float = 0.7,
    tools : list = None,
    **additional_llm_config
) : 
    if llm_choice == "openai": 
        model = LiteLlm(
            model = config["custom_llm"]["model_name"],
            api_base=config["custom_llm"]["base_url"],
            api_key=config["custom_llm"]["api_key"],
        )

    else : 
        model = model_name
    
    return LlmAgent(
        name=agent_name,
        model=model,
        description=description,
        instruction=system_prompt,
        generate_content_config=GenerateContentConfig(
            temperature=temperature,
            **additional_llm_config
        ),
        disallow_transfer_to_parent=True,  
        disallow_transfer_to_peers=True,  
        tools=tools,
    )

