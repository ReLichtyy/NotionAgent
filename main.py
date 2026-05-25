import sys
from core.config import get_settings
from core.logger import get_logger
from clients.notion_client import NotionAppClient
from clients.openai_client import OpenAIAppClient
from crawler.notion_crawler import NotionCrawler
from parser.notion_parser import NotionParser
from generator.markdown_generator import MarkdownGenerator
from generator.json_generator import JsonFragmentGenerator
from assistant.agent import NotionMentorAgent
from core.ui_formatter import UIFormatter

logger = get_logger("Main")

def print_parsed_tree_summary(node, depth=0):
    """Helper to print a summary of the parsed tree."""
    if not node:
        return
    
    indent = "  " * depth
    icon = "📄"
    if node.metadata.source_type == "database": icon = "🗄️"
from core.registry import AgentRegistry
from agents.notion_agent import NotionWorkspaceAgent
from agents.local_file_agent import LocalFileManagerAgent

logger = get_logger("MainLauncher")

def render_agent_menu(agent):
    """
    Renders the Tier 2 menu for a specific agent.
    """
    while True:
        options = agent.get_menu_options()
        
        status_info = agent.get_status_info()
        theme_color = agent.get_theme_color()
        UIFormatter.print_menu_header(agent.get_name(), status_info, theme_color)
        
        for i, (opt_name, _) in enumerate(options, 1):
            print(f"{i}. {opt_name}")
            
        exit_index = len(options) + 1
        print(f"{exit_index}. Volver al menú principal")
        
        choice_str = input(f"\nElige una opción [1-{exit_index}]: ").strip()
        
        if not choice_str.isdigit():
            print("Entrada inválida.")
            continue
            
        choice = int(choice_str)
        
        if choice == exit_index:
            return
            
        if 1 <= choice <= len(options):
            # Execute the callable associated with the option
            _, opt_callable = options[choice - 1]
            try:
                opt_callable()
            except Exception as e:
                print(f"\n❌ Ocurrió un error al ejecutar la opción: {e}")
        else:
            print("Opción fuera de rango.")

def main():
    UIFormatter.print_banner()
    
    # Initialize Registry and Register Agents
    registry = AgentRegistry()
    registry.register(NotionWorkspaceAgent())
    registry.register(LocalFileManagerAgent())
    
    while True:
        agents = registry.get_all_agents()
        
        print("\n" + "=" * 50)
        print(" SELECCIÓN DE AGENTE")
        print("=" * 50)
        UIFormatter.print_stars_rags()
        print()
        
        for idx, agent in enumerate(agents, 1):
            print(f"{idx}. {agent.get_name()} - {agent.get_description()}")
            
        exit_idx = len(agents) + 1
        print(f"{exit_idx}. Salir del Sistema")
        
        choice_str = input(f"\nElige un agente [1-{exit_idx}]: ").strip()
        
        if not choice_str.isdigit():
            print("Entrada inválida. Ingresa un número.")
            continue
            
        choice = int(choice_str)
        
        if choice == exit_idx:
            print("Saliendo de Lab Sync. ¡Hasta pronto!")
            sys.exit(0)
            
        if 1 <= choice <= len(agents):
            selected_agent = agents[choice - 1]
            render_agent_menu(selected_agent)
        else:
            print("Opción fuera de rango.")

if __name__ == "__main__":
    main()
