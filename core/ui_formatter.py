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
        # Alias para retrocompatibilidad, aunque ahora preferimos render_home_state
        UIFormatter.render_home_state()

    @staticmethod
    def render_home_state():
        import os
        os.system('cls' if os.name == 'nt' else 'clear')
        # "Stars" in bright yellow, "RAGS" in bright red
        stars_rags = r"""
   [bright_yellow]_____ _                 [/bright_yellow][bright_red]_____            _____  _____[/bright_red]
  [bright_yellow]/ ____| |               [/bright_yellow][bright_red]|  __ \     /\   / ____|/ ____|[/bright_red]
 [bright_yellow]| (___ | |_ __ _ _ __ ___[/bright_yellow][bright_red]| |__) |   /  \ | |  __| (___  [/bright_red]
  [bright_yellow]\___ \| __/ _` | '__/ __[/bright_yellow][bright_red]|  _  /   / /\ \| | |_ |\___ \ [/bright_red]
  [bright_yellow]____) | || (_| | |  \__ \[/bright_yellow][bright_red]| | \ \  / ____ \ |__| |____) |[/bright_red]
 [bright_yellow]|_____/ \__\__,_|_|  |___/[/bright_yellow][bright_red]|_|  \_\/_/    \_\_____|_____/ [/bright_red]
        """
        console.print(Panel(Align.center(Text.from_markup(stars_rags)), title="[bold white]🚀 Welcome to[/bold white]", border_style="bright_blue"))
        console.print("\n")

    @staticmethod
    def render_agent_picker_state():
        import os
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print(Align.center("[bold white]Selecciona un agente[/bold white]"))
        stars_rags = r"""
   [bright_yellow]_____ _                 [/bright_yellow][bright_red]_____            _____  _____[/bright_red]
  [bright_yellow]/ ____| |               [/bright_yellow][bright_red]|  __ \     /\   / ____|/ ____|[/bright_red]
 [bright_yellow]| (___ | |_ __ _ _ __ ___[/bright_yellow][bright_red]| |__) |   /  \ | |  __| (___  [/bright_red]
  [bright_yellow]\___ \| __/ _` | '__/ __[/bright_yellow][bright_red]|  _  /   / /\ \| | |_ |\___ \ [/bright_red]
  [bright_yellow]____) | || (_| | |  \__ \[/bright_yellow][bright_red]| | \ \  / ____ \ |__| |____) |[/bright_red]
 [bright_yellow]|_____/ \__\__,_|_|  |___/[/bright_yellow][bright_red]|_|  \_\/_/    \_\_____|_____/ [/bright_red]
        """
        console.print(Align.center(Text.from_markup(stars_rags)))
        console.print("\n")

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
