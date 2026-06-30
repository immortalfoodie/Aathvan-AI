"""AI service for task decomposition using the Anthropic API."""

import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

import anthropic
from app.config import settings

# ── Structured output types ───────────────────────────────────────────

class AIDecomposedStep(BaseModel):
    title: str
    description: str
    estimated_hours: float
    suggested_order: int


class AIDecompositionResult(BaseModel):
    task_summary: str
    steps: List[AIDecomposedStep]
    total_estimated_hours: float
    confidence_note: str


# ── System prompt for experienced mentor/TA behavior ───────────────────

SYSTEM_PROMPT = """You are an experienced academic mentor and personal productivity assistant.
Your job is to analyze a task and decompose it into a set of realistic, concrete, and actionable daily steps.

You must follow these rules strictly:
1. Estimate effort realistically, even conservatively. Do not be overly optimistic. Assume the user will encounter minor obstacles.
2. Consider the task_type (e.g. assignment, project, bill, application, personal_goal, other) to tailor the steps.
   - For 'assignment' or 'project': Include research, outlining, drafting, testing, and reviewing.
   - For 'bill': Include logging into the portal, verifying payment details, and executing/scheduling.
   - For 'application': Include resume tailoring, drafting cover letters, review, and submission.
3. Be highly specific and descriptive. Do not write vague steps like "work on project" or "write essay".
   Instead, write "set up local development repository and configure initial database models" or "draft introductory paragraph and main outline".
4. When the user provides a very short, sparse, or vague task description:
   - Provide a sensible, standard best-effort roadmap for that kind of task.
   - Explicitly flag your lack of information and state any assumptions in the 'confidence_note' field rather than fabricating false specific facts.
5. Provide a clear, empathetic 1-2 sentence 'task_summary' summarizing what the task requires.
6. Provide a 'confidence_note' with warnings, caveats, or suggestions (e.g., "This estimate assumes you are familiar with SQL; if not, add 2 hours for basic tutorials.").
"""

# Tool definition forcing structured output
DECOMPOSE_TOOL = {
    "name": "create_task_decomposition",
    "description": "Output the structured decomposition of the user's task.",
    "input_schema": {
        "type": "object",
        "properties": {
            "task_summary": {
                "type": "string",
                "description": "A 1-2 sentence empathetic summary of what the task requires."
            },
            "steps": {
                "type": "array",
                "description": "The sequential list of concrete steps needed to complete the task.",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Short, active-verb title of the step (e.g., 'Draft thesis statement')."
                        },
                        "description": {
                            "type": "string",
                            "description": "Specific, actionable detail explaining exactly what to do."
                        },
                        "estimated_hours": {
                            "type": "number",
                            "description": "Realistic hours required (can be decimals, e.g. 1.5)."
                        },
                        "suggested_order": {
                            "type": "integer",
                            "description": "The 0-based sequential order of this step."
                        }
                    },
                    "required": ["title", "description", "estimated_hours", "suggested_order"]
                }
            },
            "total_estimated_hours": {
                "type": "number",
                "description": "The sum of all steps' estimated hours."
            },
            "confidence_note": {
                "type": "string",
                "description": "Mentorship advice, context alerts, or confidence caveats if description is sparse."
            }
        },
        "required": ["task_summary", "steps", "total_estimated_hours", "confidence_note"]
    }
}


class AIServiceException(Exception):
    """Custom exception raised when plan generation fails."""
    pass


async def generate_task_plan(
    title: str,
    raw_description: Optional[str],
    task_type: str,
    due_date: Optional[datetime],
) -> AIDecompositionResult:
    """Call the Anthropic API to decompose a task.

    Raises AIServiceException on API errors, rate limits, timeouts, or parsing errors.
    """
    if not settings.ANTHROPIC_API_KEY:
        if not settings.ALLOW_MOCK_FALLBACK:
            raise AIServiceException("Anthropic API key is not configured.")
        # Fallback mock decomposition for local development/testing without API key
        return AIDecompositionResult(
            task_summary=f"Decomposed plan for: '{title}'.",
            steps=[
                AIDecomposedStep(
                    title="Phase 1: Initial research & outline requirements",
                    description=f"Gather resources for '{title}' and draft a preliminary plan.",
                    estimated_hours=2.0,
                    suggested_order=0,
                ),
                AIDecomposedStep(
                    title="Phase 2: Execution & implementation",
                    description=f"Core execution phase for '{title}'. Develop main parts.",
                    estimated_hours=4.0,
                    suggested_order=1,
                ),
                AIDecomposedStep(
                    title="Phase 3: Review, testing & validation",
                    description="Perform quality checks, refine work, and finalize deliverable.",
                    estimated_hours=2.0,
                    suggested_order=2,
                ),
            ],
            total_estimated_hours=8.0,
            confidence_note="Note: This is a fallback mock plan generated locally because ANTHROPIC_API_KEY is not configured.",
        )

    # Format context for Claude
    due_date_str = due_date.strftime("%Y-%m-%d %H:%M:%S") if due_date else "Not specified"
    current_time_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    user_message = f"""Here is the task information:
Title: {title}
Type: {task_type}
Due Date: {due_date_str}
Current Time (UTC): {current_time_str}
Description: {raw_description or "(No description provided)"}

Please decompose this task into a sequential plan of actionable steps."""

    try:
        # Create async client
        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        # Call Claude with tool choice forced
        response = await client.messages.create(
            model="claude-opus-4-6",
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
            tools=[DECOMPOSE_TOOL],
            tool_choice={"type": "tool", "name": "create_task_decomposition"},
            timeout=30.0,
        )

        # Extract tool use block
        tool_use = None
        for block in response.content:
            if block.type == "tool_use" and block.name == "create_task_decomposition":
                tool_use = block
                break

        if not tool_use:
            raise AIServiceException("Model failed to invoke the task decomposition tool.")

        input_data = tool_use.input
        return AIDecompositionResult(**input_data)

    except anthropic.APITimeoutError:
        raise AIServiceException("Request to Anthropic API timed out. Please try again.")
    except anthropic.RateLimitError:
        raise AIServiceException("Anthropic API rate limit exceeded. Please try again in a few moments.")
    except anthropic.APIStatusError as e:
        raise AIServiceException(f"Anthropic API returned status code {e.status_code}: {e.message}")
    except Exception as e:
        raise AIServiceException(f"An unexpected error occurred during AI plan generation: {str(e)}")
