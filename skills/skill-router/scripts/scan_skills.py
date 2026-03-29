#!/usr/bin/env python3
"""Scan installed skill directories across multiple AI coding tools.

The scanner groups some shared directories for inventory purposes, so it is not a
1:1 mirror of upstream `agents.ts`. See `references/supported-agents.md` for the
upstream-aligned agent matrix and local/global path rules.
Cross-platform: macOS, Linux, Windows.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# Validation thresholds (shared with validate_skill.py)
MAX_BODY_LINES = 500
MAX_SKILL_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
MAX_COMPATIBILITY_LENGTH = 500

# Allowed top-level frontmatter fields per Agent Skills Spec
# Plus widely-used extensions (args, user-invokable, version) from Claude Code ecosystem
ALLOWED_FRONTMATTER_FIELDS = {
    "name", "description", "license", "allowed-tools", "metadata", "compatibility",
    # Extensions used by Claude Code and other agents
    "args", "user-invokable", "version", "disable-model-invocation",
}


# --- Tool path registry ---
# Scanner-oriented registry of known skill directories.
# Source material: https://github.com/vercel-labs/skills/blob/main/src/agents.ts
#
# Paths are resolved at import time using environment variables and platform defaults.
# The scanner checks each path and skips those that don't exist.

_HOME = str(Path.home())
_XDG_CONFIG = (os.environ.get("XDG_CONFIG_HOME") or "").strip() or os.path.join(_HOME, ".config")
_CODEX_HOME = (os.environ.get("CODEX_HOME") or "").strip() or os.path.join(_HOME, ".codex")
_CLAUDE_HOME = (os.environ.get("CLAUDE_CONFIG_DIR") or "").strip() or os.path.join(_HOME, ".claude")

# Simple-pattern agents: global skills at ~/<subdir>/skills
# Format: (tool_id, display_name, home_subdir)
_SIMPLE_AGENTS = [
    ("adal", "AdaL", ".adal"),
    ("antigravity", "Antigravity", ".gemini/antigravity"),
    ("augment", "Augment", ".augment"),
    ("cline", "Cline", ".cline"),
    ("codebuddy", "CodeBuddy", ".codebuddy"),
    ("command-code", "Command Code", ".commandcode"),
    ("continue", "Continue", ".continue"),
    ("cortex", "Cortex Code", ".snowflake/cortex"),
    ("cursor", "Cursor", ".cursor"),
    ("droid", "Droid", ".factory"),
    ("gemini-cli", "Gemini CLI", ".gemini"),
    ("github-copilot", "GitHub Copilot", ".copilot"),
    ("iflow-cli", "iFlow CLI", ".iflow"),
    ("junie", "Junie", ".junie"),
    ("kilo", "Kilo Code", ".kilocode"),
    ("kiro-cli", "Kiro CLI", ".kiro"),
    ("kode", "Kode", ".kode"),
    ("mcpjam", "MCPJam", ".mcpjam"),
    ("mistral-vibe", "Mistral Vibe", ".vibe"),
    ("mux", "Mux", ".mux"),
    ("neovate", "Neovate", ".neovate"),
    ("openhands", "OpenHands", ".openhands"),
    ("pi", "Pi", ".pi/agent"),
    ("pochi", "Pochi", ".pochi"),
    ("qoder", "Qoder", ".qoder"),
    ("qwen-code", "Qwen Code", ".qwen"),
    ("roo", "Roo Code", ".roo"),
    ("trae", "Trae", ".trae"),
    ("trae-cn", "Trae CN", ".trae-cn"),
    ("windsurf", "Windsurf", ".codeium/windsurf"),
    ("zencoder", "Zencoder", ".zencoder"),
]


def _build_tool_registry():
    """Build the complete tool registry from agent definitions."""
    registry = [
        # Shared directory used by universal agents (Amp, Codex, Cursor, Gemini CLI, etc.)
        {
            "tool": "agents-shared",
            "display_name": "Shared Agents",
            "paths": [
                {"path": os.path.join(_HOME, ".agents", "skills"), "source_type": "user"},
                {"path": os.path.join(_XDG_CONFIG, "agents", "skills"), "source_type": "user"},
            ],
        },
        # Claude Code (respects CLAUDE_CONFIG_DIR env var)
        {
            "tool": "claude-code",
            "display_name": "Claude Code",
            "paths": [
                {"path": os.path.join(_CLAUDE_HOME, "skills"), "source_type": "user"},
            ],
        },
        # Codex (respects CODEX_HOME env var, has vendor-imported curated skills)
        {
            "tool": "codex",
            "display_name": "Codex",
            "paths": [
                {"path": os.path.join(_CODEX_HOME, "skills"), "source_type": "system"},
                {
                    "path": os.path.join(
                        _CODEX_HOME, "vendor_imports", "skills", "skills", ".curated"
                    ),
                    "source_type": "curated",
                },
                {
                    "path": os.path.join(
                        _CODEX_HOME, "vendor_imports", "skills", "skills", ".experimental"
                    ),
                    "source_type": "experimental",
                },
            ],
        },
        # OpenClaw (with legacy directory names: .clawdbot, .moltbot)
        {
            "tool": "openclaw",
            "display_name": "OpenClaw",
            "paths": [
                {"path": os.path.join(_HOME, ".openclaw", "skills"), "source_type": "user"},
                {"path": os.path.join(_HOME, ".clawdbot", "skills"), "source_type": "user"},
                {"path": os.path.join(_HOME, ".moltbot", "skills"), "source_type": "user"},
            ],
        },
        # XDG-based agents (use $XDG_CONFIG_HOME/<name>/skills)
        {
            "tool": "crush",
            "display_name": "Crush",
            "paths": [
                {"path": os.path.join(_XDG_CONFIG, "crush", "skills"), "source_type": "user"},
            ],
        },
        {
            "tool": "goose",
            "display_name": "Goose",
            "paths": [
                {"path": os.path.join(_XDG_CONFIG, "goose", "skills"), "source_type": "user"},
            ],
        },
        {
            "tool": "opencode",
            "display_name": "OpenCode",
            "paths": [
                {"path": os.path.join(_XDG_CONFIG, "opencode", "skills"), "source_type": "user"},
            ],
        },
    ]

    # Add simple-pattern agents: ~/<subdir>/skills
    for tool_id, display_name, subdir in _SIMPLE_AGENTS:
        registry.append({
            "tool": tool_id,
            "display_name": display_name,
            "paths": [
                {"path": os.path.join(_HOME, subdir, "skills"), "source_type": "user"},
            ],
        })

    return registry


TOOL_REGISTRY = _build_tool_registry()


def expand_path(p: str) -> Path:
    """Expand ~ and environment variables in a path string."""
    return Path(os.path.expandvars(os.path.expanduser(p)))


def discover_tools(include_vendor: bool = False) -> list[dict]:
    """Discover which tools are installed by checking for their skill directories.

    Iterates over TOOL_REGISTRY (41 agents). Each path is already absolute
    (resolved at import time with env vars and XDG defaults), so we just check
    whether the directory exists.

    Args:
        include_vendor: If True, include vendor-managed skills (curated/experimental).
                        Defaults to False since these are not user-installed skills.
    """
    found = []

    for tool_info in TOOL_REGISTRY:
        tool_paths = []
        for path_entry in tool_info["paths"]:
            # Skip vendor-managed paths unless explicitly requested
            if path_entry.get("source_type") in ("curated", "experimental") and not include_vendor:
                continue

            expanded = Path(path_entry["path"])

            if expanded.is_dir():
                tool_paths.append({
                    "path": str(expanded),
                    "source_type": path_entry["source_type"],
                    "exists": True,
                })

        if tool_paths:
            found.append({
                "tool": tool_info["tool"],
                "display_name": tool_info["display_name"],
                "skill_paths": tool_paths,
            })

    return found


def _split_inline_list(value: str) -> list[str]:
    items: list[str] = []
    current: list[str] = []
    quote: str | None = None

    for char in value:
        if quote:
            if char == quote:
                quote = None
            else:
                current.append(char)
            continue
        if char in ("'", '"'):
            quote = char
            continue
        if char == ",":
            items.append("".join(current).strip())
            current = []
            continue
        current.append(char)

    items.append("".join(current).strip())
    return [item for item in items if item]


def _parse_scalar(value: str):
    value = value.strip()
    if not value:
        return ""
    if value.startswith("[") and value.endswith("]"):
        return [_parse_scalar(item) for item in _split_inline_list(value[1:-1])]
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]

    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "~"}:
        return None

    if re.fullmatch(r"-?\d+", value):
        try:
            return int(value)
        except ValueError:
            return value
    if re.fullmatch(r"-?\d+\.\d+", value):
        try:
            return float(value)
        except ValueError:
            return value
    return value


def _fold_block_lines(lines: list[str]) -> str:
    paragraphs: list[str] = []
    current: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        current.append(stripped)

    if current:
        paragraphs.append(" ".join(current))
    return "\n\n".join(paragraphs).strip()


def _parse_block_scalar(lines: list[str], index: int, indent: int, folded: bool):
    collected: list[str] = []

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        current_indent = len(line) - len(line.lstrip(" "))

        if stripped and current_indent < indent:
            break

        if not stripped:
            collected.append("")
            index += 1
            continue

        collected.append(line[indent:] if len(line) >= indent else "")
        index += 1

    if folded:
        return _fold_block_lines(collected), index
    return "\n".join(collected).strip(), index


def _skip_blank_lines(lines: list[str], index: int) -> int:
    while index < len(lines) and not lines[index].strip():
        index += 1
    return index


def _parse_mapping_entry(lines: list[str], index: int, indent: int, stripped: str):
    key, sep, remainder = stripped.partition(":")
    if not sep:
        return None, None, index + 1

    key = key.strip()
    value = remainder.lstrip()

    if value in {">", "|"}:
        parsed_value, next_index = _parse_block_scalar(
            lines, index + 1, indent + 2, folded=value == ">"
        )
        return key, parsed_value, next_index

    if value:
        return key, _parse_scalar(value), index + 1

    child_index = _skip_blank_lines(lines, index + 1)
    if child_index >= len(lines):
        return key, {}, child_index

    child_line = lines[child_index]
    child_indent = len(child_line) - len(child_line.lstrip(" "))
    if child_indent <= indent:
        return key, {}, child_index
    if child_line[child_indent:].startswith("- "):
        parsed_value, next_index = _parse_list(lines, child_index, child_indent)
        return key, parsed_value, next_index

    parsed_value, next_index = _parse_mapping(lines, child_index, child_indent)
    return key, parsed_value, next_index


def _parse_list(lines: list[str], index: int, indent: int):
    items: list[object] = []

    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue

        current_indent = len(line) - len(line.lstrip(" "))
        if current_indent < indent:
            break
        if current_indent != indent or not line[current_indent:].startswith("- "):
            break

        item_text = line[current_indent + 2:].lstrip()
        if not item_text:
            child_index = _skip_blank_lines(lines, index + 1)
            if child_index >= len(lines):
                items.append({})
                index = child_index
                continue
            child_indent = len(lines[child_index]) - len(lines[child_index].lstrip(" "))
            if child_indent <= current_indent:
                items.append({})
                index = child_index
                continue
            if lines[child_index][child_indent:].startswith("- "):
                item_value, index = _parse_list(lines, child_index, child_indent)
            else:
                item_value, index = _parse_mapping(lines, child_index, child_indent)
            items.append(item_value)
            continue

        if re.match(r"^\w[\w-]*:\s*", item_text):
            item: dict = {}
            key, value, next_index = _parse_mapping_entry(lines, index, current_indent + 2, item_text)
            if key is not None:
                item[key] = value

            while next_index < len(lines):
                continuation = lines[next_index]
                if not continuation.strip():
                    next_index += 1
                    continue

                continuation_indent = len(continuation) - len(continuation.lstrip(" "))
                if continuation_indent < current_indent + 2:
                    break
                if continuation_indent == current_indent and continuation[continuation_indent:].startswith("- "):
                    break
                if continuation_indent != current_indent + 2:
                    break

                cont_key, cont_value, next_index = _parse_mapping_entry(
                    lines, next_index, continuation_indent, continuation[continuation_indent:]
                )
                if cont_key is not None:
                    item[cont_key] = cont_value

            items.append(item)
            index = next_index
            continue

        items.append(_parse_scalar(item_text))
        index += 1

    return items, index


def _parse_mapping(lines: list[str], index: int, indent: int):
    mapping: dict = {}

    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue

        current_indent = len(line) - len(line.lstrip(" "))
        if current_indent < indent:
            break
        if current_indent != indent:
            break

        key, value, index = _parse_mapping_entry(lines, index, indent, line[indent:])
        if key is not None:
            mapping[key] = value

    return mapping, index


def parse_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from a SKILL.md file.

    This parser intentionally supports the subset of YAML used by skills:
    mappings, lists, nested mappings/lists, booleans, numbers, quoted strings,
    inline arrays, and folded/literal blocks.
    """
    match = re.match(r"^---\s*\n(.*?)\n---(?:\s*\n|$)", content, re.DOTALL)
    if not match:
        return {}

    raw = match.group(1)
    parsed, _ = _parse_mapping(raw.splitlines(), 0, 0)
    return parsed


def get_body_line_count(content: str) -> int:
    """Count lines in the body (after frontmatter)."""
    match = re.match(r"^---\s*\n.*?\n---\s*\n", content, re.DOTALL)
    if match:
        body = content[match.end():]
    else:
        body = content
    return len(body.strip().split("\n")) if body.strip() else 0


def find_skill_md(skill_path: Path) -> Path | None:
    """Find SKILL.md in a skill directory, accepting lowercase fallback.

    Prefers SKILL.md (uppercase) but accepts skill.md (lowercase),
    matching the official skills-ref reference implementation.
    Uses os.listdir to get real on-disk filenames, avoiding false matches
    on case-insensitive filesystems (macOS HFS+/APFS).
    """
    if not skill_path.is_dir():
        return None
    actual_files = set(os.listdir(skill_path))
    for name in ("SKILL.md", "skill.md"):
        if name in actual_files:
            return skill_path / name
    return None


def scan_skill(skill_path: Path, tool: str, source_type: str) -> dict:
    """Scan a single skill directory and return its metadata."""
    skill_md = find_skill_md(skill_path)

    result = {
        "name": skill_path.name,
        "path": str(skill_path),
        "tool": tool,
        "source_type": source_type,
        "is_symlink": skill_path.is_symlink(),
        "resolved_path": str(skill_path.resolve()) if skill_path.is_symlink() else None,
        "has_skill_md": skill_md is not None,
        "has_scripts": (skill_path / "scripts").is_dir(),
        "has_references": (skill_path / "references").is_dir(),
        "has_assets": (skill_path / "assets").is_dir(),
        "has_openai_yaml": (skill_path / "agents" / "openai.yaml").is_file(),
        "frontmatter": {},
        "body_lines": 0,
        "issues": [],
    }

    if skill_md is None:
        result["issues"].append("Missing SKILL.md")
        return result

    if skill_md.name != "SKILL.md":
        result["issues"].append("Using lowercase 'skill.md' — recommend renaming to 'SKILL.md'")

    try:
        content = skill_md.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        result["issues"].append(f"Cannot read SKILL.md ({type(e).__name__}): {e}")
        return result

    frontmatter = parse_frontmatter(content)
    result["frontmatter"] = frontmatter
    result["body_lines"] = get_body_line_count(content)

    # Validate name field
    if "name" not in frontmatter:
        result["issues"].append("Missing 'name' in frontmatter")
    else:
        name = frontmatter["name"]
        if not isinstance(name, str):
            result["issues"].append(f"Name must be a string, got {type(name).__name__}")
        else:
            if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name):
                result["issues"].append(f"Name '{name}' is not valid kebab-case")
            if len(name) > MAX_SKILL_NAME_LENGTH:
                result["issues"].append(
                    f"Name '{name}' exceeds {MAX_SKILL_NAME_LENGTH} char limit ({len(name)} chars)"
                )
            effective_dir = skill_path.resolve().name if skill_path.is_symlink() else skill_path.name
            if name != effective_dir:
                result["issues"].append(
                    f"Name '{name}' does not match directory name '{effective_dir}'"
                )

    # Validate description field
    if "description" not in frontmatter:
        result["issues"].append("Missing 'description' in frontmatter")
    else:
        desc = frontmatter["description"]
        if not isinstance(desc, str):
            result["issues"].append(f"Description must be a string, got {type(desc).__name__}")
        else:
            if len(desc) < 20:
                result["issues"].append("Description is too short (< 20 chars)")
            if len(desc) > MAX_DESCRIPTION_LENGTH:
                result["issues"].append(
                    f"Description exceeds {MAX_DESCRIPTION_LENGTH} char limit ({len(desc)} chars)"
                )

    # Validate compatibility field if present
    if "compatibility" in frontmatter:
        compat = frontmatter["compatibility"]
        if not isinstance(compat, str):
            result["issues"].append(f"Compatibility must be a string, got {type(compat).__name__}")
        elif len(compat) > MAX_COMPATIBILITY_LENGTH:
            result["issues"].append(
                f"Compatibility exceeds {MAX_COMPATIBILITY_LENGTH} char limit ({len(compat)} chars)"
            )

    # Check for unknown top-level frontmatter fields
    unknown = set(frontmatter.keys()) - ALLOWED_FRONTMATTER_FIELDS
    if unknown:
        result["issues"].append(
            f"Unknown frontmatter fields: {', '.join(sorted(unknown))}"
        )

    if result["body_lines"] > MAX_BODY_LINES:
        result["issues"].append(
            f"SKILL.md body is {result['body_lines']} lines (recommended: < {MAX_BODY_LINES})"
        )

    return result


def scan_tool_path(skills_dir: Path, tool: str, source_type: str) -> list[dict]:
    """Scan all skills in a given directory."""
    skills = []

    try:
        entries = sorted(skills_dir.iterdir())
    except FileNotFoundError:
        return skills
    except OSError as e:
        print(f"Warning: cannot read {skills_dir}: {e}", file=sys.stderr)
        return skills

    for entry in entries:
        if entry.name.startswith("."):
            continue

        # Detect broken symlinks (target no longer exists)
        if entry.is_symlink():
            try:
                target = entry.resolve()
                if not target.exists():
                    skills.append({
                        "name": entry.name,
                        "path": str(entry),
                        "tool": tool,
                        "source_type": source_type,
                        "is_symlink": True,
                        "resolved_path": str(entry.readlink()),
                        "has_skill_md": False,
                        "has_scripts": False,
                        "has_references": False,
                        "has_assets": False,
                        "has_openai_yaml": False,
                        "frontmatter": {},
                        "body_lines": 0,
                        "issues": ["Broken symlink — target no longer exists"],
                    })
                    continue
            except (OSError, ValueError):
                continue  # skip unresolvable symlinks entirely

        # Resolve symlinks and check if it's a directory
        target = entry.resolve() if entry.is_symlink() else entry
        if not target.is_dir():
            continue

        # Skip if no SKILL.md/skill.md and no obvious skill structure
        has_skill_file = (target / "SKILL.md").exists() or (target / "skill.md").exists()
        if not has_skill_file and not any(
            (target / d).is_dir() for d in ["scripts", "references", "assets"]
        ):
            continue

        skills.append(scan_skill(entry, tool, source_type))

    return skills


def scan_all(
    custom_paths: list[str] | None = None,
    tools_filter: list[str] | None = None,
    include_vendor: bool = False,
) -> dict:
    """Scan all installed skills and return the inventory dict.

    This is the programmatic API — returns a dict instead of printing JSON.
    Called by diagnose.py and other tools that need scan results directly.
    """
    custom_paths = custom_paths or []

    # Discover tools
    detected_tools = discover_tools(include_vendor=include_vendor)

    # Apply tool filter if specified
    if tools_filter:
        detected_tools = [t for t in detected_tools if t["tool"] in tools_filter]

    # Scan all detected tool paths
    all_skills = []
    tool_summaries = []

    for tool_info in detected_tools:
        tool_skill_count = 0
        for path_info in tool_info["skill_paths"]:
            skills = scan_tool_path(
                Path(path_info["path"]),
                tool_info["tool"],
                path_info["source_type"],
            )
            all_skills.extend(skills)
            tool_skill_count += len(skills)

        tool_summaries.append({
            "tool": tool_info["tool"],
            "display_name": tool_info["display_name"],
            "skill_count": tool_skill_count,
            "paths": [p["path"] for p in tool_info["skill_paths"]],
        })

    # Scan custom paths
    for cp in custom_paths:
        expanded = expand_path(cp)
        if expanded.is_dir():
            skills = scan_tool_path(expanded, "custom", "custom")
            all_skills.extend(skills)
            tool_summaries.append({
                "tool": "custom",
                "display_name": f"Custom ({cp})",
                "skill_count": len(skills),
                "paths": [str(expanded)],
            })

    return {
        "detected_tools": tool_summaries,
        "total_skills": len(all_skills),
        "skills_with_issues": sum(1 for s in all_skills if s["issues"]),
        "skills": all_skills,
    }


def main():
    # Custom path override via argument
    custom_paths = []
    tools_filter = None
    include_vendor = False

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--tool" and i + 1 < len(sys.argv):
            tools_filter = sys.argv[i + 1].split(",")
            i += 2
        elif sys.argv[i] == "--path" and i + 1 < len(sys.argv):
            custom_paths.append(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--include-vendor":
            include_vendor = True
            i += 1
        else:
            # Positional arg treated as custom path
            custom_paths.append(sys.argv[i])
            i += 1

    summary = scan_all(
        custom_paths=custom_paths,
        tools_filter=tools_filter,
        include_vendor=include_vendor,
    )

    json.dump(summary, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
