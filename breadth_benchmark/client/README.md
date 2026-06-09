# Standalone MCP API Chat Client

This is a separate client project. It does **not** contain the MCP server, fake tools, GUI launcher, or case registry.

It connects to an already-running MCP lab server, reads the already-prepared case from the separate MCP lab project folder, fetches the tool list from the MCP endpoint, and runs an OpenAI API tool-calling chat loop.

## Folder separation

Use two separate folders:

```text
C:\Users\eunsu\Desktop\agentdojo_mcp_official_ui_lab
C:\Users\eunsu\Desktop\agentdojo_mcp_api_chat_client
```

The first folder runs the target MCP lab server and prepares cases.  
The second folder is this API chat client.

## Before running this client

In the MCP lab project:

1. Start the MCP server.
2. Prepare a case, for example `case_1065` or `case_0393`.
3. Keep the MCP server running.

The client will read:

```text
<MCP lab project>\lab_env\current_case.json
```

and connect to:

```text
http://127.0.0.1:58473/mcp
```

## Run without terminal commands

Double-click:

```text
START_CHAT_CLIENT.bat
```

The window stays open after the run so logs are not lost.

The first run asks for:

- MCP endpoint
- MCP lab project root
- model index
- OpenAI API key, if `OPENAI_API_KEY` is not already set

You can avoid retyping these by copying `.env.example` to `.env` and filling the values. When the client asks, just press Enter to use the `.env` or saved default value.

Example `.env`:

```text
OPENAI_API_KEY=sk-your-key-here
MCP_ENDPOINT=http://127.0.0.1:58473/mcp
MCP_PROJECT_ROOT=C:\Users\eunsu\Desktop\agentdojo_mcp_official_ui_lab
MODEL_INDEX=0
MAX_STEPS=20
TEMPERATURE=0.0
```

It saves endpoint/path/model index to `.chat_client_config.json` for next time. It does not save the API key unless you put it in `.env` yourself. At startup it checks whether the selected model is available to your API key; if not, it falls back to the first configured available model.

## Model index

The model list is in:

```text
agentdojo_mcp_api_chat_client/models.py
```

Current list:

```text
0: gpt-4.1-mini
1: gpt-4.1
2: gpt-4o-mini
3: gpt-4o
4: gpt-5-mini
5: gpt-5
6: gpt-5.1
7: gpt-5.2
```

## Interactive follow-up chat

After the prepared case finishes, the chat remains open. You can ask follow-ups such as:

```text
Didn't you see the Eve instruction?
```

Commands:

```text
/help   show commands
/eval   run the MCP lab project's evaluate_case.py
/trace  run the MCP lab project's show_trace.py
/task   show the prepared task
/tools  show MCP tools, descriptions, parameters, and required fields
/status show MCP endpoint, project root, case, run log, and trace file
/exit   quit
```

## Important implementation detail

This client does not define fake tools locally. It asks the MCP server for its current tools and calls those MCP tools remotely.

```text
OpenAI API model
  -> tool call
  -> this client
  -> external MCP tools/call
  -> MCP fake tool result
  -> tool message back to OpenAI API model
```

The user task is not bundled with fake data. Tool results are returned as tool messages after the model calls the MCP tool.


## Trace mirroring

Each MCP tool call made by this client is also mirrored into the selected MCP lab project's `lab_env/traces/tool_calls.jsonl`. This keeps `/eval` and `/trace` useful even when the MCP transport or folder selection would otherwise make server-side traces hard to see.


## Tool contract audit

Use `/tools` inside the chat to inspect live MCP tools and `/toolcheck` to verify every loaded tool has API-visible parameter descriptions. You can also run `uv run python scripts\audit_mcp_tools.py --mcp-url http://127.0.0.1:58473/mcp`.
