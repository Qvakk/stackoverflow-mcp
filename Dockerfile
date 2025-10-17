FROM python:3.12-slim

WORKDIR /app

# Install uv for faster dependency management
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml ./
COPY stackoverflow_mcp ./stackoverflow_mcp
COPY main.py ./

# Install dependencies
RUN uv pip install --system -e .

# Run the MCP server
CMD ["python", "main.py"]
