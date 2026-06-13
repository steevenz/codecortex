"""
Mixin for generating high-craft architectural reports.

:project: CodeCortex
:package: Modules.Codegraph.Services.Mixins.Reporter
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeGraph-v1.0
"""

import datetime
from typing import Any, Dict


class ArchitecturalReporterMixin:
    """Mixin for generating high-craft architectural reports."""

    def generate_markdown_report(self, data: Dict[str, Any]) -> str:
        """Ported logic for generating the comprehensive markdown report."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            f"# CodeCortex Architectural Insight · {data.get('repo_name', 'System')}",
            f"> Generated: {timestamp}",
            "",
            "## 1. System Vitality",
            "| Metric | Value |",
            "| :--- | :--- |",
            f"| Total Files | {data.get('total_files', 0)} |",
            f"| God Nodes | {len(data.get('god_nodes', []))} |",
            f"| Communities | {len(data.get('communities', {}))} |",
            f"| Cohesion Score | {data.get('avg_cohesion', 'N/A')} |",
            "",
            "## 2. Central Hubs (God Nodes)",
            "High-impact files with massive influence over the system architecture.",
            "",
            "| Node | Impact | In/Out | centraliy |",
            "| :--- | :--- | :--- | :--- |"
        ]

        for node in data.get('god_nodes', [])[:5]:
            node_id = node['id']
            impact = "🔴 Critical" if node['pagerank'] > 0.05 else "🟡 Significant"
            in_out = f"{node['in_degree']}/{node['out_degree']}"
            lines.append(f"| `{node_id}` | {impact} | {in_out} | {node['pagerank']} |")

        lines.extend([
            "",
            "## 3. Temporal Hotspots (Git History)",
            "Files with the highest churn rate. Often indicate technical debt or high-complexity areas.",
            "",
            "| File Path | Commit Count | Impact |",
            "| :--- | :--- | :--- |"
        ])

        for spot in data.get('hotspots', [])[:5]:
            impact = "🔥 High Churn" if spot['commit_count'] > 20 else "⚡ Moderate"
            lines.append(f"| `{spot['file_path']}` | {spot['commit_count']} | {impact} |")

        temporal_coupling = data.get('temporal_coupling', [])
        if temporal_coupling:
            lines.extend([
                "",
                "## 3.5. Temporal Coupling",
                "Files frequently committed together, indicating hidden dependencies or tight logical coupling.",
                "",
                "| File A | File B | Co-Commits |",
                "| :--- | :--- | :--- |"
            ])
            for couple in temporal_coupling[:5]:
                lines.append(f"| `{couple['file_a']}` | `{couple['file_b']}` | {couple['co_commits']} |")

        lines.extend([
            "",
            "## 4. Module Interactions",
            "High-level dependencies between system modules/folders.",
            "",
            "| Source Module | Target Module | Weight |",
            "| :--- | :--- | :--- |"
        ])

        module_data = data.get('module_analysis', {})
        for edge in module_data.get('dependencies', [])[:10]:
            lines.append(f"| `{edge['source_module']}` | `{edge['target_module']}` | {edge['total_weight']} |")

        lines.extend([
            "",
            "## 5. Structural Risks & Observations",
        ])

        for obs in data.get('observations', []):
            lines.append(f"- {obs}")

        if not data.get('observations'):
            lines.append("- No immediate structural risks detected. System appears balanced.")

        lines.extend([
            "",
            "## 6. Architectural Inquiry",
            "Questions suggested by the graph topology for deep exploration:",
            ""
        ])

        for q in data.get('questions', []):
            lines.append(f"- **{q}**")

        return "\n".join(lines)
