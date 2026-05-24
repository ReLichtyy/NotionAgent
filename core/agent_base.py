from abc import ABC, abstractmethod

class BaseAgent(ABC):
    """
    Abstract Base Class defining the standard contract for all Lab Sync agents.
    Every new agent (Notion, Local Files, Github, etc.) must implement these methods.
    """
    
    @abstractmethod
    def get_id(self) -> str:
        """Returns a unique identifier for the agent (e.g. 'notion_workspace')."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Returns the human-readable name of the agent."""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Returns a brief description of what the agent does."""
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        """
        Checks if the agent's knowledge context is built and ready for chat.
        Returns True if ready, False if it needs extraction/refresh.
        """
        pass

    @abstractmethod
    def refresh_knowledge(self) -> bool:
        """
        Executes the logic to crawl, parse, and generate the agent's context.
        Returns True if successful, False otherwise.
        """
        pass

    @abstractmethod
    def start_chat(self) -> None:
        """
        Starts the interactive CLI chat session for this specific agent.
        """
        pass

    def get_menu_options(self) -> list[tuple[str, callable]]:
        """
        Returns a list of tuples containing (Option Name, Callable Method).
        These populate the tier-2 menu for this specific agent.
        """
        return [
            ("Usar contexto actual (Entrar al chat)", self.start_chat),
            ("Refrescar conocimiento (Full Crawl)", self.refresh_knowledge)
        ]

    @abstractmethod
    def get_status_info(self) -> dict:
        """
        Returns a dictionary with status information to be displayed in the menu.
        Example: {"Fuente": "Notion Workspace", "Conocimiento actual": "Disponible"}
        """
        pass
