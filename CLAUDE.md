## 0. Critical Requirements
- Think in English, but generate responses in Japanese
- **Sequential thinking**: Automatically use for: architectural decisions, complex multi-step implementations, debugging unclear issues, design pattern selection, refactoring strategies, security considerations. Skip for simple operations (file reads, commits, straightforward tool execution).
- **Read README.md first**: Always read the project's README.md file before starting any task to understand the project structure, setup instructions, and key information
- **Clean up temporary files**: If temporary new files, scripts, or helper files are created for iteration purposes, delete these files at the end of the task to clean up
- **Parallel tool execution**: For maximum efficiency, when multiple independent operations need to be performed, call all relevant tools simultaneously rather than sequentially
- **Context window efficiency**: When creating or modifying documents that Claude Code may read (slash commands, documentation, configuration files), prioritize context window efficiency:
  - Remove redundant explanations and duplicate information
  - Eliminate user-facing content (examples, troubleshooting guides, verbose explanations)
  - Keep only essential execution instructions and core information
  - Use concise, structured format (bullet points over paragraphs)
  - Aggressively reduce verbosity while preserving all execution-critical information (typically results in 50-70% reduction, but information completeness takes priority over size targets)

## 1. Basic Configuration
- **Task tool**: Large-scale file search, impact scope identification
- **Web search**: Execute `gemini -p "$ARGUMENTS"` (always use gemini tool instead of WebSearch)
- **Code understanding and editing**: Always use mcp-serena for semantic code operations (symbol search, code editing, pattern search, and symbol overview)
- **Code context management**: Use mcp-context7 for managing coding context and related operations
- **GitHub operations**: Always use mcp-github for GitHub API operations (PR creation, merging, status checks, etc.)
- **Python environment**: Always use `.venv/bin/activate` for Python environment (managed with uv)
- **Browser operations**: Always use mcp-playwright for browser automation and web interactions
