# Architecture

This client is physically separate from the MCP lab project.

It contains only:

- OpenAI API chat loop
- MCP client bridge
- terminal UI
- logs

It does not contain:

- `mcp_server.py`
- fake tool implementations
- case registry
- lab state seeder
- GUI launcher

## Runtime dependency direction

```text
API chat client -> external MCP endpoint
API chat client -> external MCP lab_env/current_case.json
```

The API client reads the starting prompt from the prepared case file and fetches tool schemas from the MCP endpoint.

## Why this is different from the previous standalone API runner

The previous approach copied tool schemas and routed directly to local fake Python functions. This project does not do that. It uses the existing MCP server as the tool source of truth.


## .env defaults

The client loads `.env` from its own project root before prompting. Values from `.env` become defaults for MCP endpoint, MCP project root, model index, max steps, temperature, and `OPENAI_API_KEY`. Pressing Enter at a prompt keeps the loaded default.
