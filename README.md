# Stack Overflow MCP Server

A modular Model Context Protocol (MCP) server that enables AI assistants to search and access Stack Overflow content for technical solutions, error handling, and programming knowledge.

## Features

- 🔍 **Multiple Search Methods**: Search by query, error message, or specific question ID
- 📊 **Advanced Filtering**: Filter results by tags, score, and accepted answers
- 🧩 **Error Analysis**: Parse error messages and find relevant solutions
- 📝 **Flexible Formatting**: Get results in Markdown or JSON format
- 💬 **Comments Support**: Optionally include question and answer comments
- ⚡ **Rate Limiting**: Built-in protection to respect Stack Exchange API quotas
- 🏗️ **Modular Architecture**: Clean separation of concerns for easy maintenance

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (recommended) or pip
- Stack Exchange API key (see below)

### Getting a Stack Exchange API Key

1. Go to [Stack Apps OAuth Registration](https://stackapps.com/apps/oauth/register)
2. Fill out the form:
   - Name: "Stack Overflow MCP" (or your preferred name)
   - Description: "MCP server for accessing Stack Overflow"
   - OAuth Domain: "localhost" (for local usage)
3. Submit and copy your API Key

## Installation

### Using uv (recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd stackoverflow-mcp

# Install dependencies
uv pip install -e .

# For development
uv pip install -e ".[dev]"
```

### Using pip

```bash
pip install -e .

# For development
pip install -e ".[dev]"
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Required
STACK_EXCHANGE_API_KEY=your_api_key_here

# Optional: Rate limiting (defaults shown)
MAX_REQUEST_PER_WINDOW=30
RATE_LIMIT_WINDOW_MS=60000
RETRY_AFTER_MS=2000
```

## Usage

### Running the Server Locally

```bash
# Using uv
uv run main.py

# Using python
python main.py
```

### Running with Docker

```bash
# Build the Docker image
docker-compose build

# Run the server
docker-compose run --rm stackoverflow-mcp
```

### Adding to VS Code MCP

Add to your User `mcp.json` file (File > Preferences > Settings > search for "mcp" > Edit in settings.json):

**Using Docker (recommended):**

```json
"stackoverflow-mcp": {
  "type": "stdio",
  "command": "docker",
  "args": [
    "compose",
    "-f",
    "C:/Users/YourUser/path/to/stackoverflow-mcp/docker-compose.yml",
    "run",
    "--rm",
    "-T",
    "stackoverflow-mcp"
  ],
  "env": {
    "STACK_EXCHANGE_API_KEY": "your_api_key_here"
  }
}
```

**Without Docker:**

```json
"stackoverflow-mcp": {
  "type": "stdio",
  "command": "python",
  "args": ["C:/Users/YourUser/path/to/stackoverflow-mcp/main.py"],
  "env": {
    "STACK_EXCHANGE_API_KEY": "your_api_key_here"
  }
}
```

## Available Tools

### 1. `search_by_query`

Advanced search with comprehensive filtering options.

**Parameters:**
- `query` (required): Search query string
- `tags`: Filter by tags (e.g., `["python", "pandas"]`)
  - ⚠️ **Note**: Invalid tags are automatically detected and removed. The search continues with only valid tags and displays which tags were removed.
  - ℹ️ **Note**: If no results are found with tags, the search automatically retries without tag filtering to find relevant content.
- `excluded_tags`: Exclude specific tags
- `min_score`: Minimum score threshold (default: 0)
- `has_accepted_answer`: Require accepted answer (default: false)
- `title`: Text that must appear in title
- `body`: Text that must appear in body
- `min_answers`: Minimum number of answers
- `sort_by`: Sort by `activity`, `creation`, `votes`, or `relevance` (default: "relevance")
- `include_comments`: Include comments (default: false)
- `response_format`: `"json"` or `"markdown"` (default: "markdown")
- `limit`: Max results (default: 10)

### 2. `search_by_error`

Parse error messages and find solutions.

**Parameters:**
- `error_message` (required): Error message or stack trace
- `language`: Programming language (e.g., "python", "javascript")
- `technologies`: Related technologies (e.g., `["react", "django"]`)
- `min_score`: Minimum score threshold (default: 1)
- `include_comments`: Include comments (default: false)
- `response_format`: `"json"` or `"markdown"` (default: "markdown")
- `limit`: Max results (default: 5)

### 3. `get_question`

Fetch specific question with all answers by ID.

**Parameters:**
- `question_id` (required): Stack Overflow question ID
- `include_comments`: Include comments (default: false)
- `response_format`: `"json"` or `"markdown"` (default: "markdown")
