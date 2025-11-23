from .agent.agent_factory import make_subagent
from .tools.search_tool import SearchTool
from ..utils.logger import setup_logger

logger = setup_logger('agent_setup', 'agent_setup.log')

def create_agent():
    """
    Create and configure the main agent for the API.
    """
    logger.info("Creating main agent...")
    
    # Initialize tools
    search_tool = SearchTool()
    
    # Define system prompt
    system_prompt = """
    You are a helpful AI assistant for the Control Theory textbook application.
    You have access to a search tool to find information from the textbook.
    
    When a user asks a question:
    1. Use the search tool to find relevant information if needed.
    2. Answer the question based on the retrieved information.
    3. If you cannot find the answer, state that clearly.
    """
    
    # Create agent
    agent = make_subagent(
        agent_name="GeneralAssistant",
        system_prompt=system_prompt,
        description="A general assistant for answering questions about Control Theory.",
        tools=[search_tool],
        model_name="gemini-2.0-flash" 
    )
    
    logger.info("Main agent created successfully.")
    return agent
