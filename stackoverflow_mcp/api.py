"""Stack Exchange API client module."""

import asyncio
import time
from typing import Any, Optional
from urllib.parse import urlencode

import httpx

from .config import config
from .types import Answer, Comment, Question, SearchResult


class RateLimiter:
    """Rate limiter for API requests."""

    def __init__(
        self, max_requests: int, window_ms: int, retry_after_ms: int
    ) -> None:
        """Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed per window
            window_ms: Time window in milliseconds
            retry_after_ms: Delay after hitting rate limit
        """
        self.max_requests = max_requests
        self.window_ms = window_ms
        self.retry_after_ms = retry_after_ms
        self.requests: list[float] = []

    async def acquire(self) -> None:
        """Acquire permission to make a request, waiting if necessary."""
        now = time.time() * 1000  # Convert to milliseconds
        # Remove old requests outside the window
        self.requests = [
            req for req in self.requests if now - req < self.window_ms
        ]

        if len(self.requests) >= self.max_requests:
            # Wait until we can make another request
            wait_time = self.retry_after_ms / 1000  # Convert to seconds
            await asyncio.sleep(wait_time)
            await self.acquire()  # Retry
        else:
            self.requests.append(now)


class StackOverflowAPI:
    """Client for Stack Exchange API."""

    BASE_URL = "https://api.stackexchange.com/2.3"

    def __init__(self) -> None:
        """Initialize API client with rate limiting."""
        self.rate_limiter = RateLimiter(
            config.max_requests_per_window,
            config.rate_limit_window_ms,
            config.retry_after_ms,
        )
        # Do not automatically follow redirects to prevent SSRF via redirect chains
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=False,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )

    def _validate_request_url(self, url: str) -> None:
        # Basic validation: only allow requests under the configured BASE_URL
        from urllib.parse import urlparse

        parsed = urlparse(url)
        base_parsed = urlparse(self.BASE_URL)
        if parsed.scheme not in ("https",):
            raise ValueError("Only HTTPS requests are allowed")
        # Ensure hostname ends with StackExchange host
        if not parsed.hostname or not parsed.hostname.endswith(base_parsed.hostname):
            raise ValueError("Request to unexpected host blocked")

    async def _make_request(
        self, endpoint: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Make a rate-limited API request.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            JSON response from API
            
        Raises:
            ValueError: For all errors without exposing API key or URL
        """
        await self.rate_limiter.acquire()

        params["key"] = config.stack_exchange_api_key
        params["site"] = "stackoverflow"
        params["filter"] = "withbody"  # Include question/answer bodies

        url = f"{self.BASE_URL}/{endpoint}"
        # Validate that the URL stays under allowed BASE_URL
        self._validate_request_url(url)

        try:
            response = await self.client.get(url, params=params)
        except httpx.TimeoutException:
            raise ValueError("Stack Exchange API request timed out. Please try again.")
        except httpx.NetworkError:
            raise ValueError("Network error connecting to Stack Exchange API. Please check your connection.")
        except httpx.HTTPError as e:
            # Catch any other httpx errors without exposing details
            raise ValueError(f"Error communicating with Stack Exchange API: {type(e).__name__}")
        
        # If a redirect is returned, block it (prevent SSRF via redirect)
        if 300 <= response.status_code < 400:
            raise ValueError("Unexpected redirect from Stack Exchange API blocked for security reasons")
        
        # Handle errors without exposing API key in error messages
        if response.status_code == 400:
            # Parse the API's error response to get the actual error message
            try:
                error_data = response.json()
                api_error_msg = error_data.get("error_message", "Unknown error")
                error_msg = f"Bad request to Stack Exchange API: {api_error_msg}"
            except Exception:
                # If we can't parse the error response, use a generic message
                error_msg = "Bad request to Stack Exchange API. "
                if "tagged" in params or "nottagged" in params:
                    error_msg += "Check that all tags are valid Stack Overflow tags."
            raise ValueError(error_msg)
        
        if response.status_code == 429:
            # Try to get backoff time from API response
            try:
                error_data = response.json()
                backoff = error_data.get("backoff", 0)
                if backoff > 0:
                    raise ValueError(f"Stack Exchange API rate limit exceeded. Please wait {backoff} seconds and try again.")
            except Exception:
                pass
            raise ValueError("Stack Exchange API rate limit exceeded. Please wait a moment and try again.")
        
        if not response.is_success:
            # Try to get error message from API, fallback to generic message
            try:
                error_data = response.json()
                api_error_msg = error_data.get("error_message", "Unknown error")
                raise ValueError(f"Stack Exchange API error ({response.status_code}): {api_error_msg}")
            except Exception:
                # Fallback to generic error without exposing URL/key
                raise ValueError(f"Stack Exchange API error: {response.status_code} {response.reason_phrase}")
        
        try:
            return response.json()
        except Exception:
            raise ValueError("Failed to parse Stack Exchange API response.")

    async def search_questions(
        self,
        query: str,
        tags: Optional[list[str]] = None,
        excluded_tags: Optional[list[str]] = None,
        min_score: int = 0,
        has_accepted_answer: bool = False,
        title: Optional[str] = None,
        body: Optional[str] = None,
        min_answers: Optional[int] = None,
        sort_by: str = "relevance",
        limit: int = 10,
    ) -> list[Question]:
        """Search for questions by query with advanced filters.

        Args:
            query: Search query string
            tags: Tags to filter by
            excluded_tags: Tags to exclude
            min_score: Minimum score threshold
            has_accepted_answer: Filter for questions with accepted answers
            title: Text that must appear in the title
            body: Text that must appear in the body
            min_answers: Minimum number of answers
            sort_by: Sort field (activity, creation, votes, relevance)
            limit: Maximum number of results

        Returns:
            List of matching questions
        """
        valid_sorts = {"activity", "creation", "votes", "relevance"}
        sort = sort_by if sort_by in valid_sorts else "relevance"
        
        # If min_score is specified and sort is "relevance", change to "votes"
        # because "relevance" sort doesn't accept min/max parameters
        if min_score > 0 and sort == "relevance":
            sort = "votes"
        
        params: dict[str, Any] = {
            "q": query,
            "sort": sort,
            "order": "desc",
            "pagesize": min(limit, 100),
        }

        if tags:
            params["tagged"] = ";".join(tags)
        if excluded_tags:
            params["nottagged"] = ";".join(excluded_tags)
        if min_score > 0:
            params["min"] = min_score
        if has_accepted_answer:
            params["accepted"] = "True"
        if title:
            params["title"] = title
        if body:
            params["body"] = body
        if min_answers is not None and min_answers > 0:
            params["answers"] = min_answers

        data = await self._make_request("search/advanced", params)
        return [self._parse_question(item) for item in data.get("items", [])]

    async def get_question(
        self, question_id: int, include_comments: bool = False
    ) -> SearchResult:
        """Get a specific question with its answers.

        Args:
            question_id: Stack Overflow question ID
            include_comments: Whether to include comments

        Returns:
            SearchResult with question, answers, and optionally comments
        """
        # Get question details
        q_data = await self._make_request(
            f"questions/{question_id}", {"filter": "withbody"}
        )
        
        # Check if question exists
        if not q_data.get("items"):
            raise ValueError(f"Question with ID {question_id} not found or is not accessible.")
        
        question = self._parse_question(q_data["items"][0])

        # Get answers
        a_data = await self._make_request(
            f"questions/{question_id}/answers",
            {"filter": "withbody", "sort": "votes", "order": "desc"},
        )
        answers = [self._parse_answer(item) for item in a_data.get("items", [])]

        # Get comments if requested
        question_comments: tuple[Comment, ...] = ()
        answer_comments: dict[int, tuple[Comment, ...]] = {}

        if include_comments:
            # Get question comments
            qc_data = await self._make_request(
                f"questions/{question_id}/comments", {}
            )
            question_comments = tuple(
                self._parse_comment(item) for item in qc_data.get("items", [])
            )

            # Get answer comments
            for answer in answers:
                ac_data = await self._make_request(
                    f"answers/{answer.answer_id}/comments", {}
                )
                answer_comments[answer.answer_id] = tuple(
                    self._parse_comment(item) for item in ac_data.get("items", [])
                )

        return SearchResult(
            question=question,
            answers=tuple(answers),
            question_comments=question_comments,
            answer_comments=answer_comments,
        )

    def _parse_question(self, data: dict[str, Any]) -> Question:
        """Parse question data from API response."""
        return Question(
            question_id=data["question_id"],
            title=data["title"],
            link=data["link"],
            score=data["score"],
            answer_count=data["answer_count"],
            is_answered=data.get("is_answered", False),
            view_count=data["view_count"],
            tags=tuple(data["tags"]),
            owner_display_name=data["owner"].get("display_name", "Unknown"),
            creation_date=data["creation_date"],
            last_activity_date=data["last_activity_date"],
            body=data.get("body"),
            accepted_answer_id=data.get("accepted_answer_id"),
        )

    def _parse_answer(self, data: dict[str, Any]) -> Answer:
        """Parse answer data from API response."""
        return Answer(
            answer_id=data["answer_id"],
            question_id=data["question_id"],
            score=data["score"],
            is_accepted=data.get("is_accepted", False),
            owner_display_name=data["owner"].get("display_name", "Unknown"),
            creation_date=data["creation_date"],
            last_activity_date=data["last_activity_date"],
            body=data.get("body", ""),
        )

    def _parse_comment(self, data: dict[str, Any]) -> Comment:
        """Parse comment data from API response."""
        return Comment(
            comment_id=data["comment_id"],
            post_id=data["post_id"],
            score=data["score"],
            owner_display_name=data["owner"].get("display_name", "Unknown"),
            creation_date=data["creation_date"],
            body=data["body"],
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
