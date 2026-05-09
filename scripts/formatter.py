"""
/**
 * @project   CodeCortex
 * @package   CLI
 * @standard  Aegis-CrossStack-v1.0
 * * CLI Table Formatter — Laravel Artisan-style terminal output.
 *   Bold headers, bordered tables, consistent padding.
 */
"""

import sys
from typing import List, Dict, Optional
from datetime import datetime


def green(text: str) -> str:
    return f"\033[92m{text}\033[0m"

def yellow(text: str) -> str:
    return f"\033[93m{text}\033[0m"

def cyan(text: str) -> str:
    return f"\033[96m{text}\033[0m"

def red(text: str) -> str:
    return f"\033[91m{text}\033[0m"

def bold(text: str) -> str:
    return f"\033[1m{text}\033[0m"

def dim(text: str) -> str:
    return f"\033[2m{text}\033[0m"


def print_header(title: str):
    """Print a styled section header (ASCII-safe for Windows)."""
    line = "#" * 58
    print(f"\n{green(line)}")
    print(f"{green('  ' + title)}")
    print(f"{green(line)}")


def print_table(headers: List[str], rows: List[List[str]], colors: Optional[List[str]] = None):
    """Print a formatted table using ASCII borders (safe for all terminals)."""
    if not rows:
        print(f"  {dim('No entries found.')}")
        return
    
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))
    
    col_widths = [w + 2 for w in col_widths]
    
    sep = "+" + "+".join("-" * w for w in col_widths) + "+"
    
    print(f"\n{sep}")
    header_cells = []
    for i, h in enumerate(headers):
        header_cells.append(f" {h.ljust(col_widths[i] - 2)} ")
    print("|" + "|".join(header_cells) + "|")
    hsep = "+" + "+".join("=" * w for w in col_widths) + "+"
    print(hsep)
    
    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            cell_str = str(cell).ljust(col_widths[i] - 2)
            if colors and i < len(colors):
                cm = {'g': green, 'y': yellow, 'c': cyan, 'r': red, 'b': bold}
                cell_str = cm.get(colors[i], str)(cell_str)
            cells.append(f" {cell_str} ")
        print("|" + "|".join(cells) + "|")
        print(sep)
    
    print(f"{dim(f'  {len(rows)} row(s)')}\n")


def print_project_list(projects: List[Dict]):
    """Print repositories in a formatted table."""
    print_header("REGISTERED REPOSITORIES")
    
    if not projects:
        print(f"  {yellow('No projects registered.')}")
        print(f"  {dim('Run: codecortex --init /path/to/project')}")
        return
    
    headers = ["NAME", "PATH", "REPO ID", "LAST COMMIT", "STATS"]
    rows = []
    colors = ['g', 'c', 'y', 'b', '']
    
    for p in projects:
        name = p.get("name", p.get("repo_name", "?"))[:20]
        path = p.get("path", p.get("root_path", "?"))[:40]
        repo_id = p.get("repo_id", p.get("id", "?"))[:12]
        commit = (p.get("last_commit") or "")[:10] if p.get("last_commit") else "-"
        
        stats = p.get("stats", {})
        stat_str = f"f:{stats.get('files','?')} n:{stats.get('nodes','?')}" if stats else "-"
        
        rows.append([name, path, repo_id, commit, stat_str])
    
    print_table(headers, rows, colors)


def print_workspace_list(workspaces: List[Dict]):
    """Print workspaces in a formatted table."""
    print_header("WORKSPACES")
    
    if not workspaces:
        print(f"  {yellow('No workspaces configured.')}")
        return
    
    headers = ["NAME", "PATH", "PROJECTS", "STATUS"]
    rows = []
    colors = ['g', 'c', 'y', '']
    
    for w in workspaces:
        name = w.get("name", "?")[:20]
        path = w.get("path", "?")[:40]
        projects = str(w.get("project_count", w.get("repos", 0)))
        status = w.get("status", "active")
        
        rows.append([name, path, projects, status])
    
    print_table(headers, rows, colors)
