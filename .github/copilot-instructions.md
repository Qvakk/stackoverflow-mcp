# Stack Overflow MCP Server

Hey! This is a Python 3.12 MCP server that lets you search Stack Overflow. It has three tools: search by query (with tons of filters), search by error message, and get a specific question.

## How it's organized

The code is split into modules - don't mix them up:
- `config.py` handles environment stuff with Pydantic
- `types.py` has frozen dataclasses (use tuples, not lists!)
- `api.py` talks to Stack Exchange API with rate limiting built in
- `formatter.py` converts data to Markdown or JSON
- `server.py` is the MCP server with tool handlers
- `main.py` just runs everything

Use modern Python: `str | None`, lowercase `tuple`/`dict`.

## Things to remember

Always do `await self.rate_limiter.acquire()` before hitting the API.
The `_extract_error_query()` function cleans up error messages with regex - don't break that pattern, it's important for search quality.
Everything's async, so use `async def` and remember to `await self.api.close()` when cleaning up.

## Quick setup

Copy `.env.example` to `.env` and add your `STACK_EXCHANGE_API_KEY` (grab one from https://stackapps.com/apps/oauth/register - gives you 10k requests/day instead of 300).
Run it: `uv run main.py` or `python main.py` or Docker.
Check your code: `ruff format . && ruff check . && mypy stackoverflow_mcp`

## Stack Exchange API stuff

Base URL is `https://api.stackexchange.com/2.3`
The search_by_query tool supports a bunch of filters: `title`, `body`, `answers` (minimum), `tagged`/`nottagged`, `min` score, `accepted` answer, and `sort` by relevance/votes/creation/activity.
Max 100 results per request.
**Important:** If invalid tags cause a 400 error, the server automatically identifies which tags are invalid by testing them one-by-one, removes only the invalid ones, and retries with the remaining valid tags. It then shows a warning listing the specific invalid tags. This is in `_handle_search_by_query()` with a try/except block.

## Common mistakes

Don't forget to `await` your coroutines - mypy will catch this if you run it.
All the dataclasses are frozen with slots, so return tuples not lists.
Pydantic validates config on import, so if your .env is wrong, it'll blow up immediately with a ValidationError.
Keep an eye on `quota_remaining` in API responses so you don't hit limits.
