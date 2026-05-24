from typing import Dict, List
from core.agent_base import BaseAgent
from core.logger import get_logger

logger = get_logger("AgentRegistry")

class AgentRegistry:
    """
    Central registry for managing multiple Lab Sync agents.
    """
    
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        
    def register(self, agent: BaseAgent):
        """Registers an agent into the system."""
        agent_id = agent.get_id()
        if agent_id in self._agents:
            logger.warning(f"Agent with ID {agent_id} is already registered. Overwriting.")
        self._agents[agent_id] = agent
        logger.info(f"Registered agent: {agent.get_name()} ({agent_id})")
        
    def get_agent(self, agent_id: str) -> BaseAgent:
        """Retrieves a specific agent by ID."""
        return self._agents.get(agent_id)
        
    def get_all_agents(self) -> List[BaseAgent]:
        """Returns a list of all registered agents."""
        return list(self._agents.values())
