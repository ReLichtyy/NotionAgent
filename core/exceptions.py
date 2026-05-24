class LabSyncError(Exception):
    """Base exception for Lab Sync."""
    pass

class ConfigurationError(LabSyncError):
    """Raised when there is an issue with the environment configuration."""
    pass

class NotionConnectionError(LabSyncError):
    """Raised when the connection to Notion API fails."""
    pass

class OpenAIConnectionError(LabSyncError):
    """Raised when the connection to OpenAI API fails."""
    pass
