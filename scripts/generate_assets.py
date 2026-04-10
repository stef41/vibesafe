"""Generate SVG assets for vibesafe README."""

from rich.console import Console
from rich.table import Table


def generate_scan_report():
    console = Console(record=True, width=90)

    table = Table(title="vibesafe scan report", show_header=True, header_style="bold red")
    table.add_column("File", style="cyan")
    table.add_column("Line", justify="right")
    table.add_column("Code", style="yellow")
    table.add_column("Severity", style="bold")
    table.add_column("Issue", style="white")

    table.add_row("api/auth.py", "12", "VS100", "[red]error[/]", "Use of eval() - code injection")
    table.add_row("api/auth.py", "18", "VS200", "[red]error[/]", "Possible OpenAI API key")
    table.add_row("api/auth.py", "25", "VS110", "[red]error[/]", "SQL query with f-string")
    table.add_row("core/utils.py", "3", "VS300", "[yellow]warning[/]", "Import 'magic_ai_lib' not found")
    table.add_row("core/utils.py", "45", "VS400", "[yellow]warning[/]", "Unused import: 'json'")
    table.add_row("core/utils.py", "67", "VS507", "[yellow]warning[/]", "Mutable default in 'process()'")
    table.add_row("models/user.py", "8", "VS501", "[yellow]warning[/]", "Function 'validate' - placeholder")
    table.add_row("models/user.py", "15", "VS402", "[yellow]warning[/]", "Empty except block")
    table.add_row("main.py", "5", "VS500", "[blue]info[/]", "TODO comment left by AI")
    table.add_row("main.py", "22", "VS504", "[blue]info[/]", "Hardcoded localhost URL")

    console.print(table)
    console.print("\n[bold]4 files scanned:[/] [red]3 errors[/], [yellow]5 warnings[/], [blue]2 info[/]")
    return console.export_svg(title="vibesafe scan")


def generate_checks_overview():
    console = Console(record=True, width=85)

    table = Table(title="vibesafe check categories", show_header=True, header_style="bold cyan")
    table.add_column("Category", style="bold")
    table.add_column("Codes", style="yellow")
    table.add_column("Checks", justify="right")
    table.add_column("What It Catches")

    table.add_row("[red]Security[/]", "VS100-VS110", "11", "eval, exec, shell injection, SQL injection")
    table.add_row("[red]Secrets[/]", "VS200-VS210", "12", "API keys, tokens, private keys, credentials")
    table.add_row("[yellow]Imports[/]", "VS300", "1", "Hallucinated packages (AI's #1 mistake)")
    table.add_row("[yellow]Dead Code[/]", "VS400-VS403", "4", "Unused imports, unreachable code, bare except")
    table.add_row("[blue]AI Patterns[/]", "VS500-VS507", "8", "TODOs, stubs, mutable defaults, star imports")

    console.print(table)
    console.print("\n[bold green]36 built-in checks[/] • Zero dependencies • <100ms per file")
    return console.export_svg(title="vibesafe checks")


if __name__ == "__main__":
    import os
    os.makedirs("assets", exist_ok=True)

    svg = generate_scan_report()
    with open("assets/scan_report.svg", "w") as f:
        f.write(svg)
    print(f"  scan_report.svg: {len(svg):,} bytes")

    svg = generate_checks_overview()
    with open("assets/checks_overview.svg", "w") as f:
        f.write(svg)
    print(f"  checks_overview.svg: {len(svg):,} bytes")
