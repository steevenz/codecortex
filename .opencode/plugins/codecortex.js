// CodeCortex OpenCode Plugin
// This file is the entry point for OpenCode's plugin system.
// It registers skills from the .skills/ directory.

import { readdirSync, readFileSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SKILLS_DIR = join(__dirname, '..', '.skills');

/**
 * Load all CodeCortex skills for OpenCode.
 * Each skill directory contains SKILL.md with frontmatter + instructions.
 */
export function loadSkills() {
  if (!existsSync(SKILL_DIR)) return [];

  const skills = [];
  const entries = readdirSync(SKILL_DIR, { withFileTypes: true });

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;

    const skillPath = join(SKILL_DIR, entry.name, 'SKILL.md');
    if (!existsSync(skillPath)) continue;

    const content = readFileSync(skillPath, 'utf-8');
    // Parse YAML frontmatter
    const match = content.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
    if (!match) continue;

    const frontmatter = {};
    for (const line of match[1].split('\n')) {
      const sep = line.indexOf(':');
      if (sep > 0) {
        frontmatter[line.slice(0, sep).trim()] = line.slice(sep + 1).trim().replace(/^"(.*)"$/, '$1');
      }
    }

    skills.push({
      name: frontmatter.name || entry.name,
      description: frontmatter.description || '',
      content: match[2].trim(),
      directory: entry.name,
    });
  }

  return skills;
}

/**
 * Get plugin metadata for OpenCode marketplace.
 */
export function getPluginInfo() {
  return {
    name: 'codecortex',
    version: '1.2.0',
    description: 'Code intelligence via MCP — codebase analysis, graph queries, refactoring, architecture audit, cross-IDE memory',
    skills: loadSkills(),
  };
}

export default { loadSkills, getPluginInfo };
