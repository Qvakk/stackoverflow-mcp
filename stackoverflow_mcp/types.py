"""Type definitions for Stack Overflow MCP server."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Question:
    """Immutable representation of a Stack Overflow question.
    
    Attributes:
        question_id: Unique identifier for the question
        title: Question title text
        link: Direct URL to the question
        score: Net upvotes (upvotes - downvotes)
        answer_count: Number of answers posted
        is_answered: Whether an answer is accepted
        view_count: Number of times question was viewed
        tags: Tuple of topic tags
        owner_display_name: Question author's display name
        creation_date: Unix timestamp of creation
        last_activity_date: Unix timestamp of last activity
        body: Optional HTML body content
        accepted_answer_id: ID of accepted answer if exists
    """

    question_id: int
    title: str
    link: str
    score: int
    answer_count: int
    is_answered: bool
    view_count: int
    tags: tuple[str, ...]
    owner_display_name: str
    creation_date: int
    last_activity_date: int
    body: str | None = None
    accepted_answer_id: int | None = None

    @property
    def created_at(self) -> datetime:
        """Get creation date as datetime object."""
        return datetime.fromtimestamp(self.creation_date)

    @property
    def last_activity_at(self) -> datetime:
        """Get last activity date as datetime object."""
        return datetime.fromtimestamp(self.last_activity_date)


@dataclass(frozen=True, slots=True)
class Answer:
    """Immutable representation of a Stack Overflow answer.
    
    Attributes:
        answer_id: Unique identifier for the answer
        question_id: ID of parent question
        score: Net upvotes (upvotes - downvotes)
        is_accepted: Whether this is the accepted answer
        owner_display_name: Answer author's display name
        creation_date: Unix timestamp of creation
        last_activity_date: Unix timestamp of last edit/activity
        body: HTML body content
    """

    answer_id: int
    question_id: int
    score: int
    is_accepted: bool
    owner_display_name: str
    creation_date: int
    last_activity_date: int
    body: str

    @property
    def created_at(self) -> datetime:
        """Get creation date as datetime object."""
        return datetime.fromtimestamp(self.creation_date)


@dataclass(frozen=True, slots=True)
class Comment:
    """Immutable representation of a comment on a question or answer.
    
    Attributes:
        comment_id: Unique identifier for the comment
        post_id: ID of parent post (question or answer)
        score: Number of upvotes
        owner_display_name: Comment author's display name
        creation_date: Unix timestamp of creation
        body: Plain text or HTML body content
    """

    comment_id: int
    post_id: int
    score: int
    owner_display_name: str
    creation_date: int
    body: str


@dataclass(frozen=True, slots=True)
class SearchResult:
    """Immutable collection of a question with its answers and comments.
    
    Attributes:
        question: The main question
        answers: Tuple of answers, typically sorted by score
        question_comments: Comments on the question
        answer_comments: Mapping of answer_id to tuple of comments
    """

    question: Question
    answers: tuple[Answer, ...] = field(default_factory=tuple)
    question_comments: tuple[Comment, ...] = field(default_factory=tuple)
    answer_comments: dict[int, tuple[Comment, ...]] = field(default_factory=dict)

    @property
    def total_comments(self) -> int:
        """Get total count of all comments."""
        return len(self.question_comments) + sum(
            len(comments) for comments in self.answer_comments.values()
        )
