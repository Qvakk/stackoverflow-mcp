# Stack Overflow MCP Server - Development Guide

A production-ready Python 3.12 MCP server for searching Stack Overflow with comprehensive security hardening. Works with stdio transport for local Docker integration in VS Code.

## Project Overview

**3 Tools Available:**
- `search_by_query` - Search questions with advanced filters (tags, score, answers, title, body)
- `search_by_error` - Find solutions by pasting error messages
- `get_question` - Retrieve specific question with answers and optional comments

**Transport:** stdio (stdin/stdout) - connects locally via Docker
**Security:** OWASP Top 10 MCP hardened (96/100 security score)
**Search Filters:** Tags, score, answers, accepted, title, body, sort order
**Rate Limiting:** 30 requests/minute (configurable)
**Input Limits:** Query (2000 chars), tags (10×50 chars), results (max 100)

Use https://modelcontextprotocol-security.io/top10/server/ for vulnerability guidelines.