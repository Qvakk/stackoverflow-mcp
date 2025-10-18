"""MCP server implementation for Stack Overflow."""

import re
from typing import Any, Literal, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .api import StackOverflowAPI
from .config import config
from .formatter import Formatter
from .utilities import input_validation as iv
from .utilities import output_filtering as of
from .utilities import logging as slog


class StackOverflowMCPServer:
    """MCP server for Stack Overflow search."""

    def __init__(self) -> None:
        """Initialize the MCP server."""
        self.server = Server("stackoverflow-mcp")
        self.api = StackOverflowAPI()
        self.formatter = Formatter()
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register MCP tool handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="search_by_query",
                    description=(
                        "Search Stack Overflow for questions matching a query. "
                        "Returns relevant questions with filters for tags, score, "
                        "and accepted answers."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query",
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional tags to filter by",
                            },
                            "excluded_tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional tags to exclude",
                            },
                            "min_score": {
                                "type": "integer",
                                "description": "Minimum score threshold",
                                "default": 0,
                            },
                            "has_accepted_answer": {
                                "type": "boolean",
                                "description": "Filter for questions with accepted answers",
                                "default": False,
                            },
                            "title": {
                                "type": "string",
                                "description": "Text that must appear in the title",
                            },
                            "body": {
                                "type": "string",
                                "description": "Text that must appear in the body",
                            },
                            "min_answers": {
                                "type": "integer",
                                "description": "Minimum number of answers",
                            },
                            "sort_by": {
                                "type": "string",
                                "enum": ["activity", "creation", "votes", "relevance"],
                                "description": "Sort field (activity, creation, votes, relevance)",
                                "default": "relevance",
                            },
                            "include_comments": {
                                "type": "boolean",
                                "description": "Include comments in results",
                                "default": False,
                            },
                            "response_format": {
                                "type": "string",
                                "enum": ["json", "markdown"],
                                "description": "Response format",
                                "default": "markdown",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "default": 10,
                            },
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="search_by_error",
                    description=(
                        "Search Stack Overflow for solutions to an error message. "
                        "Extracts key error patterns and searches for relevant solutions."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "error_message": {
                                "type": "string",
                                "description": "The error message to search for",
                            },
                            "language": {
                                "type": "string",
                                "description": "Programming language (e.g., python, javascript)",
                            },
                            "technologies": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Related technologies/frameworks",
                            },
                            "min_score": {
                                "type": "integer",
                                "description": "Minimum score threshold",
                                "default": 1,
                            },
                            "include_comments": {
                                "type": "boolean",
                                "description": "Include comments in results",
                                "default": False,
                            },
                            "response_format": {
                                "type": "string",
                                "enum": ["json", "markdown"],
                                "description": "Response format",
                                "default": "markdown",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "default": 5,
                            },
                        },
                        "required": ["error_message"],
                    },
                ),
                Tool(
                    name="get_question",
                    description=(
                        "Get a specific Stack Overflow question by ID with all its "
                        "answers and optionally comments."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "question_id": {
                                "type": "integer",
                                "description": "The Stack Overflow question ID",
                            },
                            "include_comments": {
                                "type": "boolean",
                                "description": "Include comments in results",
                                "default": False,
                            },
                            "response_format": {
                                "type": "string",
                                "enum": ["json", "markdown"],
                                "description": "Response format",
                                "default": "markdown",
                            },
                        },
                        "required": ["question_id"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            """Handle tool calls."""
            if name == "search_by_query":
                return await self._handle_search_by_query(arguments)
            elif name == "search_by_error":
                return await self._handle_search_by_error(arguments)
            elif name == "get_question":
                return await self._handle_get_question(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")

    async def _handle_search_by_query(
        self, args: dict[str, Any]
    ) -> list[TextContent]:
        """Handle search_by_query tool with automatic tag fallback."""
        # Validate and sanitize inputs
        try:
            query = iv.validate_query(args["query"])
        except iv.ValidationError:
            slog.log_event("input_validation_failed", slog.Severity.HIGH, "Invalid search query", {"query": str(args.get("query"))})
            raise

        tags = iv.validate_tags(args.get("tags"))
        excluded_tags = iv.validate_tags(args.get("excluded_tags"))
        invalid_tags: list[str] = []
        no_results_fallback = False
        
        # Try with all tags first
        try:
            questions = await self.api.search_questions(
                query=query,
                tags=tags,
                excluded_tags=excluded_tags,
                min_score=args.get("min_score", 0),
                has_accepted_answer=args.get("has_accepted_answer", False),
                title=args.get("title"),
                body=args.get("body"),
                min_answers=args.get("min_answers"),
                sort_by=args.get("sort_by", "relevance"),
                limit=iv.validate_limit(args.get("limit", 10)),
            )
        except ValueError as e:
            # If tags caused the error, find and remove invalid tags
            if "tags" in str(e).lower() and tags and len(tags) > 0:
                # Try to find which tags are invalid by testing them one by one
                valid_tags: list[str] = []
                for tag in tags:
                    try:
                        await self.api.search_questions(
                            query=query,
                            tags=[tag],
                            min_score=0,
                            limit=1,
                        )
                        valid_tags.append(tag)
                    except ValueError:
                        invalid_tags.append(tag)
                
                # Retry with only valid tags
                questions = await self.api.search_questions(
                    query=query,
                    tags=valid_tags if valid_tags else None,
                    excluded_tags=excluded_tags,
                    min_score=args.get("min_score", 0),
                    has_accepted_answer=args.get("has_accepted_answer", False),
                    title=args.get("title"),
                    body=args.get("body"),
                    min_answers=args.get("min_answers"),
                    sort_by=args.get("sort_by", "relevance"),
                    limit=iv.validate_limit(args.get("limit", 10)),
                )
            else:
                raise
        
        # If no results and tags were used, try again without tags
        if not questions and tags:
            no_results_fallback = True
            questions = await self.api.search_questions(
                query=query,
                tags=None,
                excluded_tags=None,
                min_score=args.get("min_score", 0),
                has_accepted_answer=args.get("has_accepted_answer", False),
                title=args.get("title"),
                body=args.get("body"),
                min_answers=args.get("min_answers"),
                sort_by=args.get("sort_by", "relevance"),
                limit=iv.validate_limit(args.get("limit", 10)),
            )

        response_format: Literal["json", "markdown"] = args.get(
            "response_format", "markdown"
        )
        include_comments: bool = args.get("include_comments", False)

        # If include_comments, fetch full details for top questions
        if include_comments and questions:
            results = []
            for q in questions[: min(3, len(questions))]:  # Limit to top 3
                result = await self.api.get_question(
                    q.question_id, include_comments=True
                )
                if response_format == "markdown":
                    results.append(self.formatter.format_markdown(result))
                else:
                    results.append(self.formatter.format_json(result))
            text = "\n\n---\n\n".join(results)
        else:
            if response_format == "markdown":
                text = self.formatter.format_questions_list_markdown(questions)
            else:
                text = self.formatter.format_questions_list_json(questions)

        # Prepend warning if invalid tags were found and removed
        if invalid_tags:
            warning = f"⚠️ **Note:** Invalid tags removed: `{'`, `'.join(invalid_tags)}`. Search performed with remaining valid tags.\n\n---\n\n"
            text = warning + text
        elif no_results_fallback:
            warning = "ℹ️ **Note:** No results found with the specified tags. Showing results without tag filtering.\n\n---\n\n"
            text = warning + text

        # Sanitize output for PII and injection tokens
        sanitized, pii_count, inj_count = of.sanitize_output(text)
        if pii_count:
            slog.log_event("pii_detected", slog.Severity.HIGH, "PII redacted in search_by_query output", {"redactions": pii_count})
        if inj_count:
            slog.log_event("output_injection", slog.Severity.CRITICAL, "Output contained injection tokens and was sanitized", {"count": inj_count})

        return [TextContent(type="text", text=sanitized)]

    async def _handle_search_by_error(
        self, args: dict[str, Any]
    ) -> list[TextContent]:
        """Handle search_by_error tool."""
        try:
            error_message = iv.validate_error_message(args["error_message"])
        except iv.ValidationError:
            slog.log_event("input_validation_failed", slog.Severity.HIGH, "Invalid error_message", {"error_message": str(args.get("error_message"))})
            raise

        # Extract key error pattern from message
        query = self._extract_error_query(error_message)

        # Build tags from language and technologies
        tags: list[str] = []
        if language := args.get("language"):
            tags.append(language)
        if technologies := args.get("technologies"):
            tags.extend(technologies)

        questions = await self.api.search_questions(
            query=query,
            tags=tags if tags else None,
            min_score=args.get("min_score", 1),
            has_accepted_answer=True,  # Prefer questions with solutions
            limit=iv.validate_limit(args.get("limit", 5)),
        )

        response_format: Literal["json", "markdown"] = args.get(
            "response_format", "markdown"
        )
        include_comments: bool = args.get("include_comments", False)

        # Fetch full details for top questions
        if questions:
            results = []
            for q in questions[: min(3, len(questions))]:
                result = await self.api.get_question(
                    q.question_id, include_comments=include_comments
                )
                if response_format == "markdown":
                    results.append(self.formatter.format_markdown(result))
                else:
                    results.append(self.formatter.format_json(result))
            text = "\n\n---\n\n".join(results)
        else:
            text = "No solutions found for this error."

        # Sanitize output
        sanitized, pii_count, inj_count = of.sanitize_output(text)
        if pii_count:
            slog.log_event("pii_detected", slog.Severity.HIGH, "PII redacted in search_by_error output", {"redactions": pii_count})
        if inj_count:
            slog.log_event("output_injection", slog.Severity.CRITICAL, "Output contained injection tokens and was sanitized", {"count": inj_count})

        return [TextContent(type="text", text=sanitized)]

    async def _handle_get_question(
        self, args: dict[str, Any]
    ) -> list[TextContent]:
        """Handle get_question tool."""
        try:
            qid = iv.validate_question_id(args["question_id"])
        except iv.ValidationError:
            slog.log_event("input_validation_failed", slog.Severity.HIGH, "Invalid question_id", {"question_id": str(args.get("question_id"))})
            raise

        result = await self.api.get_question(
            question_id=qid,
            include_comments=args.get("include_comments", False),
        )

        response_format: Literal["json", "markdown"] = args.get(
            "response_format", "markdown"
        )

        if response_format == "markdown":
            text = self.formatter.format_markdown(result)
        else:
            text = self.formatter.format_json(result)

        # Sanitize output
        sanitized, pii_count, inj_count = of.sanitize_output(text)
        if pii_count:
            slog.log_event("pii_detected", slog.Severity.HIGH, "PII redacted in get_question output", {"redactions": pii_count})
        if inj_count:
            slog.log_event("output_injection", slog.Severity.CRITICAL, "Output contained injection tokens and was sanitized", {"count": inj_count})

        return [TextContent(type="text", text=sanitized)]

    @staticmethod
    def _extract_error_query(error_message: str) -> str:
        """Extract searchable query from error message.

        Args:
            error_message: Full error message or stack trace

        Returns:
            Cleaned error query suitable for search
        """
        # Extract error type/message (first line often most relevant)
        lines = error_message.strip().split("\n")
        first_line = lines[0].strip()

        # Try to extract exception type and message
        # Pattern: ExceptionType: error message
        if ":" in first_line:
            parts = first_line.split(":", 1)
            if len(parts) == 2:
                error_type = parts[0].strip()
                error_msg = parts[1].strip()
                # Clean up file paths and line numbers
                error_msg = re.sub(r'["\'].*?["\']', "", error_msg)
                error_msg = re.sub(r"\s+", " ", error_msg)
                return f"{error_type} {error_msg}".strip()

        # Fallback: use first line, clean it up
        clean = re.sub(r'["\'].*?["\']', "", first_line)
        clean = re.sub(r"\s+", " ", clean)
        return clean.strip()

    async def run(self) -> None:
        """Run the MCP server.
        
        Configuration is validated automatically during module import via Pydantic.
        """
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream, write_stream, self.server.create_initialization_options()
            )

    async def cleanup(self) -> None:
        """Clean up resources."""
        await self.api.close()
