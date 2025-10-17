"""Response formatting utilities for Stack Overflow data."""

import json
from typing import Any

from .types import Answer, Comment, Question, SearchResult


class Formatter:
    """Format Stack Overflow data for different output formats."""

    @staticmethod
    def format_markdown(result: SearchResult) -> str:
        """Format search result as Markdown.

        Args:
            result: SearchResult to format

        Returns:
            Markdown-formatted string
        """
        lines = []

        # Question section
        q = result.question
        lines.append(f"# [{q.title}]({q.link})")
        lines.append("")
        lines.append(
            f"**Score:** {q.score} | **Answers:** {q.answer_count} | "
            f"**Views:** {q.view_count}"
        )
        lines.append(f"**Tags:** {', '.join(f'`{tag}`' for tag in q.tags)}")
        lines.append(f"**Asked by:** {q.owner_display_name}")
        lines.append("")

        if q.body:
            lines.append("## Question")
            lines.append("")
            lines.append(q.body)
            lines.append("")

        # Question comments
        if result.question_comments:
            lines.append("### Comments")
            lines.append("")
            for comment in result.question_comments:
                lines.append(
                    f"- **{comment.owner_display_name}** "
                    f"(+{comment.score}): {comment.body}"
                )
            lines.append("")

        # Answers section
        if result.answers:
            lines.append("---")
            lines.append("")
            lines.append(f"## Answers ({len(result.answers)})")
            lines.append("")

            for idx, answer in enumerate(result.answers, 1):
                accepted = " ✓ ACCEPTED" if answer.is_accepted else ""
                lines.append(
                    f"### Answer {idx}{accepted} "
                    f"(Score: {answer.score})"
                )
                lines.append(f"**By:** {answer.owner_display_name}")
                lines.append("")
                lines.append(answer.body)
                lines.append("")

                # Answer comments
                if answer.answer_id in result.answer_comments:
                    comments = result.answer_comments[answer.answer_id]
                    if comments:
                        lines.append("**Comments:**")
                        lines.append("")
                        for comment in comments:
                            lines.append(
                                f"- **{comment.owner_display_name}** "
                                f"(+{comment.score}): {comment.body}"
                            )
                        lines.append("")

        return "\n".join(lines)

    @staticmethod
    def format_json(result: SearchResult) -> str:
        """Format search result as JSON.

        Args:
            result: SearchResult to format

        Returns:
            JSON-formatted string
        """
        data: dict[str, Any] = {
            "question": Formatter._question_to_dict(result.question),
            "answers": [
                Formatter._answer_to_dict(ans) for ans in result.answers
            ],
        }

        if result.question_comments:
            data["question_comments"] = [
                Formatter._comment_to_dict(c) for c in result.question_comments
            ]

        if result.answer_comments:
            data["answer_comments"] = {
                str(aid): [Formatter._comment_to_dict(c) for c in comments]
                for aid, comments in result.answer_comments.items()
            }

        return json.dumps(data, indent=2)

    @staticmethod
    def format_questions_list_markdown(questions: list[Question]) -> str:
        """Format a list of questions as Markdown.

        Args:
            questions: List of questions to format

        Returns:
            Markdown-formatted string
        """
        if not questions:
            return "No questions found."

        lines = [f"# Found {len(questions)} Questions", ""]

        for idx, q in enumerate(questions, 1):
            lines.append(f"## {idx}. [{q.title}]({q.link})")
            lines.append(
                f"**Score:** {q.score} | **Answers:** {q.answer_count} | "
                f"**Views:** {q.view_count}"
            )
            lines.append(f"**Tags:** {', '.join(f'`{tag}`' for tag in q.tags)}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def format_questions_list_json(questions: list[Question]) -> str:
        """Format a list of questions as JSON.

        Args:
            questions: List of questions to format

        Returns:
            JSON-formatted string
        """
        data = {
            "count": len(questions),
            "questions": [
                Formatter._question_to_dict(q) for q in questions
            ],
        }
        return json.dumps(data, indent=2)

    @staticmethod
    def _question_to_dict(question: Question) -> dict[str, Any]:
        """Convert Question to dictionary."""
        return {
            "question_id": question.question_id,
            "title": question.title,
            "link": question.link,
            "score": question.score,
            "answer_count": question.answer_count,
            "is_answered": question.is_answered,
            "view_count": question.view_count,
            "tags": question.tags,
            "owner": question.owner_display_name,
            "creation_date": question.creation_date,
            "body": question.body,
            "accepted_answer_id": question.accepted_answer_id,
        }

    @staticmethod
    def _answer_to_dict(answer: Answer) -> dict[str, Any]:
        """Convert Answer to dictionary."""
        return {
            "answer_id": answer.answer_id,
            "question_id": answer.question_id,
            "score": answer.score,
            "is_accepted": answer.is_accepted,
            "owner": answer.owner_display_name,
            "creation_date": answer.creation_date,
            "body": answer.body,
        }

    @staticmethod
    def _comment_to_dict(comment: Comment) -> dict[str, Any]:
        """Convert Comment to dictionary."""
        return {
            "comment_id": comment.comment_id,
            "post_id": comment.post_id,
            "score": comment.score,
            "owner": comment.owner_display_name,
            "creation_date": comment.creation_date,
            "body": comment.body,
        }
