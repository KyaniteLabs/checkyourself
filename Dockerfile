# Minimal image so MCP directories (e.g. Glama) can start the stdio MCP server
# and run introspection. CheckYourself's CLI is stdlib-only; no extra deps.
FROM python:3.14-slim
WORKDIR /app
COPY . .
ENTRYPOINT ["python3", "tools/checkyourself.py", "mcp"]
