"""AI service for task decomposition using the Google Gemini API."""

from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field

from google import genai
from google.genai import types

from app.config import settings

# ── Structured output types ───────────────────────────────────────────

class AIDecomposedStep(BaseModel):
    title: str = Field(description="Short, active-verb title of the step (e.g., 'Draft thesis statement').")
    description: str = Field(description="Specific, actionable detail explaining exactly what to do.")
    estimated_hours: float = Field(description="Realistic hours required (can be decimals, e.g. 1.5).")
    suggested_order: int = Field(description="The 0-based sequential order of this step.")


class AIDecompositionResult(BaseModel):
    task_summary: str = Field(description="A 1-2 sentence empathetic summary of what the task requires.")
    steps: list[AIDecomposedStep] = Field(description="The sequential list of concrete steps needed to complete the task.")
    total_estimated_hours: float = Field(description="The sum of all steps' estimated hours.")
    confidence_note: str = Field(description="Mentorship advice, context alerts, or confidence caveats if description is sparse.")


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

class AIServiceException(Exception):
    """Custom exception raised when plan generation fails."""
    pass


async def generate_task_plan(
    title: str,
    raw_description: Optional[str],
    task_type: str,
    due_date: Optional[datetime],
    adjustment_factor: float = 1.0,
) -> AIDecompositionResult:
    """Call the Gemini API to decompose a task.

    Raises AIServiceException on API errors, rate limits, timeouts, or parsing errors.
    """
    if not settings.GEMINI_API_KEY:
        if not settings.ALLOW_MOCK_FALLBACK:
            raise AIServiceException("Gemini API key is not configured.")
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
            confidence_note="Note: This is a fallback mock plan generated locally because GEMINI_API_KEY is not configured.",
        )

    # Format context
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
        # Initialize Gemini Client
        # The SDK automatically uses synchronous requests under the hood, but can be awaited if wrapped or run async.
        # Since the Google GenAI SDK's `client.models.generate_content_async` is available, we use that.
        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=AIDecompositionResult,
                temperature=0.2,
            ),
        )

        if not response.parsed:
            raise AIServiceException("Model failed to return structured data.")

        result = response.parsed

        # Apply the user's learned estimation adjustment factor
        if adjustment_factor != 1.0:
            for step in result.steps:
                # Multiply the estimate by the user's learned factor and round to nearest 0.25 for neatness
                adjusted = step.estimated_hours * adjustment_factor
                step.estimated_hours = round(adjusted * 4) / 4
            
            # Recalculate total
            result.total_estimated_hours = sum(s.estimated_hours for s in result.steps)
            
            # Append a note that the estimates were personalized
            result.confidence_note += f"\n\n[Personalized]: Estimates have been adjusted by a factor of {adjustment_factor:.2f}x based on your past completion times for {task_type} tasks."

        return result

    except Exception as e:
        raise AIServiceException(f"An unexpected error occurred during AI plan generation: {str(e)}")
