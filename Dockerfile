# Minimal image so MCP directories (e.g. Glama) can start the stdio MCP server
# and run introspection. CheckYourself's CLI is stdlib-only; no extra deps.
FROM python:3.14-slim
WORKDIR /app
COPY tools/ tools/
COPY schemas/ schemas/
COPY checkyourself.manifest.json LICENSE NOTICE.md ./
RUN useradd --create-home --uid 10001 checkyourself \
    && chown -R checkyourself /app
USER checkyourself
ENTRYPOINT ["python3", "tools/checkyourself.py", "mcp"]
