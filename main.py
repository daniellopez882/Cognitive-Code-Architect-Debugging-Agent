import os
import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.theme import Theme
from rich.layout import Layout
from graph import app
from utils.config import load_config
from state import CodeReviewState

# Custom Theme for Premium Look
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "brand": "bold magenta",
})

console = Console(theme=custom_theme)

def create_header():
    """Create a premium header for the application."""
    grid = Table.grid(expand=True)
    grid.add_column(justify="center", ratio=1)
    grid.add_row(
        Panel(
            "[brand]TITAN AI[/brand]\n[italic]The Cognitive Code Architect[/italic]",
            style="brand",
            border_style="magenta",
            padding=(1, 2),
        )
    )
    return grid

def main():
    """Main entry point for TitanAI Code Review."""
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(create_header())
    
    local_path = "."
    config = load_config(local_path)
    
    initial_state = {
        "repository_url": "local",
        "local_path": local_path,
        "review_scope": "full",
        "config": config,
        "auto_fix_enabled": config.get("auto_fix", {}).get("enabled", False),
        "messages": [],
        "errors": [],
        "static_analysis_findings": [],
        "pattern_analysis_findings": [],
        "security_findings": [],
        "performance_findings": [],
        "testing_findings": [],
        "logic_findings": [],
        "files_analyzed": 0,
        "total_files": 0,
        "analysis_start_time": time.time()
    }

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        format_remaining=True,
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Architecting Code Review...", total=100)
        
        try:
            # Update progress as we run (Simulated for UI smoothness)
            progress.update(task, advance=10, description="[cyan]Initializing Repository...")
            time.sleep(0.5)
            
            thread_config = {"configurable": {"thread_id": f"titan-run-{int(time.time())}"}}
            results = app.invoke(initial_state, thread_config)
            
            progress.update(task, advance=90, description="[success]Analysis Complete!")
            
            # Show Results Table
            console.print("\n")
            
            grade = results.get("titan_score", "N/A")
            grade_color = "green" if "A" in grade else "yellow" if "B" in grade else "red"
            
            console.print(Panel(f"FINAL CODE GRADE: [{grade_color} bold]{grade}[/{grade_color} bold]", border_style=grade_color, expand=False))
            
            table = Table(title="[brand]Review Intelligence Summary[/brand]", border_style="magenta")
            table.add_column("Category", style="cyan")
            table.add_column("Findings", justify="right", style="magenta")
            table.add_column("Severity Score", justify="center")

            findings = results.get('all_findings', [])
            categories = {
                "Static": len(results.get('static_analysis_findings', [])),
                "Pattern": len(results.get('pattern_analysis_findings', [])),
                "Security": len(results.get('security_findings', [])),
                "Performance": len(results.get('performance_findings', [])),
                "Logic": len(results.get('logic_findings', [])),
            }

            for cat, count in categories.items():
                score = "🟢 LOW" if count < 5 else "🟡 MED" if count < 15 else "🔴 HIGH"
                table.add_row(cat, str(count), score)

            console.print(table)
            console.print(Panel(f"[success]✅ Success:[/success] Generated [info]{results.get('current_step')}[/info]", border_style="green"))
            
        except Exception as e:
            console.print(Panel(f"[error]❌ TitanAI encountered a bottleneck:[/error]\n{str(e)}", border_style="red"))

if __name__ == "__main__":
    main()
