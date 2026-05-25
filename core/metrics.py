import time
from rich.console import Console
from rich.table import Table

console = Console()

class MetricsTracker:
    def __init__(self):
        self.timers = {}
        self.phases = []
        
    def start_phase(self, phase_name: str):
        self.timers[phase_name] = time.time()
        if phase_name not in self.phases:
            self.phases.append(phase_name)
            
    def end_phase(self, phase_name: str):
        if phase_name in self.timers:
            elapsed = time.time() - self.timers[phase_name]
            self.timers[phase_name] = elapsed
            
    def print_summary(self):
        table = Table(show_header=True, header_style="bold magenta", border_style="bright_black")
        table.add_column("Fase", style="dim", width=25)
        table.add_column("Latencia (s)", justify="right")
        
        total = 0.0
        for phase in self.phases:
            elapsed = self.timers.get(phase, 0.0)
            total += elapsed
            table.add_row(phase, f"{elapsed:.2f}s")
            
        table.add_row("[bold]Total[/bold]", f"[bold]{total:.2f}s[/bold]")
        console.print("\n")
        console.print(table)
        console.print("\n")

    def log_operation(self, operation: str, target: str):
        """Silently logs an operation to a file for background analytics."""
        try:
            with open("operations_log.txt", "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - OP: {operation} - TARGET: {target}\n")
        except:
            pass
