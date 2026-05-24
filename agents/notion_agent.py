import os
from core.agent_base import BaseAgent
from core.logger import get_logger

from agents.notion_pipeline import NotionExtractionPipeline
from agents.notion_policy import NotionStartupPolicy
from assistant.agent import NotionMentorAgent

logger = get_logger("NotionAgentFacade")

class NotionWorkspaceAgent(BaseAgent):
    """
    Agent implementation for the Notion Workspace context.
    Encapsulates crawling, parsing, generation, and the interactive chat loop.
    """
    
    def __init__(self):
        self.mentor_agent = None
        self.policy = NotionStartupPolicy()

    def get_id(self) -> str:
        return "notion_workspace"

    def get_name(self) -> str:
        return "Notion Workspace Agent"

    def get_description(self) -> str:
        return "Mentor Estratégico Bidireccional conectado a tu base de conocimiento de Notion."

    def is_ready(self) -> bool:
        """Checks if the context files exist and have content using the StartupPolicy."""
        return self.policy.evaluate().is_ready

    def refresh_knowledge(self) -> bool:
        """Runs the extraction phases to export the Markdown context and JSON fragments."""
        pipeline = NotionExtractionPipeline()
        return pipeline.run()

    def start_chat(self) -> None:
        """Instantiates the mentor agent and starts the CLI loop."""
        result = self.policy.evaluate()
        if not result.is_ready:
            print(f"\n❌ Error: {result.message}")
            return
            
        self.mentor_agent = NotionMentorAgent()
        self.mentor_agent.start_chat_loop()
