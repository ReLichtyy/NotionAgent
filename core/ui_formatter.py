import time
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.text import Text
from rich.panel import Panel
from rich.align import Align

console = Console()

class UIFormatter:
    @staticmethod
    def print_banner():
        banner_text = r"""
  _       _       ____    _____ __  __ _   _  ____ 
 | |     / \     |  _ \  / ____|  \/  | \ | |/ ___|
 | |    / _ \    | |_) | \___ \| \  / |  \| | |    
 | |___/ ___ \   |  _ <   ___) | |\/| | |\  | |___ 
 |____/_/   \_\  |_| \_\ |____/|_|  |_|_| \_|\____|
        """
        console.print(Panel(Align.center(Text(banner_text, style="bold cyan")), title="[bold white]🚀 Welcome to[/bold white]", border_style="cyan"))

    @staticmethod
    def print_menu_header(title: str, status_info: dict, theme_color: str):
        text = Text()
        for key, value in status_info.items():
            text.append(f"• {key}: ", style="bold white")
            text.append(f"{value}\n", style=theme_color)
        
        # Remove trailing newline
        if len(text) > 0:
            text.right_crop(1)
            
        console.print(Panel(text, title=f"[bold {theme_color}]--- {title} ---[/bold {theme_color}]", border_style=theme_color))

    @staticmethod
    def print_agent_avatar(theme_color: str):
        console.print(f"\n[{theme_color} bold]🤖 Lab Sync:[/]")

    @staticmethod
    def print_typewriter_markdown(content: str, speed: float = 0.005):
        """
        Renders markdown progressively to simulate a typewriter effect.
        """
        # Increase speed if content is too large to avoid annoying waits
        if len(content) > 1000:
            speed = 0.001
            
        with Live(Markdown(""), refresh_per_second=30, console=console, transient=False) as live:
            # Step size determines how many characters are revealed per tick
            step = max(1, int(len(content) / 300)) if len(content) > 500 else 1
            for i in range(1, len(content) + 1, step):
                live.update(Markdown(content[:i]))
                time.sleep(speed)
            # Ensure final render is complete
            live.update(Markdown(content))
        console.print()
