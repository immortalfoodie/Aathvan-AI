"""Voice check-in service using Gemini API to parse transcripts into task updates."""

from typing import List, Any
from pydantic import BaseModel, Field

from google import genai
from google.genai import types

from app.config import settings

class ProposedChange(BaseModel):
    step_id: int = Field(description="The unique integer ID of the active step")
    step_title: str = Field(description="The title of the step being updated")
    proposed_status: str = Field(description="'done' or 'in_progress'")
    reasoning: str = Field(description="Short reasoning explaining why the transcript maps to this step")

class VoiceCheckinResult(BaseModel):
    understood_transcript: str = Field(description="The original transcript provided")
    proposed_changes: list[ProposedChange] = Field(description="List of proposed status updates")

VOICE_PROMPT = """You are a helpful assistant interpreting a user's voice check-in about their tasks.
You will be provided with a transcript of what the user said, and a list of their current active task steps.

Your job is to match what they said to the specific steps and propose status updates.
1. Only propose changes for steps you are highly confident they mentioned.
2. Determine if the step is 'done' (completed) or 'in_progress' (they worked on it but aren't finished).
3. Return a short reasoning string explaining why you mapped their words to that step.
"""

async def process_voice_checkin(transcript: str, active_steps: List[Any]) -> VoiceCheckinResult:
    """Uses Gemini to map a transcript to proposed step status updates."""
    if not settings.GEMINI_API_KEY:
        # Mock response for local development without API key
        if not active_steps:
            return VoiceCheckinResult(understood_transcript=transcript, proposed_changes=[])
        
        # Propose making the first step done just as a mock
        return VoiceCheckinResult(
            understood_transcript=transcript,
            proposed_changes=[
                ProposedChange(
                    step_id=active_steps[0].id,
                    step_title=active_steps[0].title,
                    proposed_status="done",
                    reasoning="Mock fallback reason based on voice."
                )
            ]
        )

    # Format the context
    steps_context = "\n".join([f"- ID: {s.id} | Task: {s.task.title if s.task else 'Unknown'} | Title: {s.title} | Current Status: {s.status.value}" for s in active_steps])
    
    user_message = f"""Transcript: "{transcript}"

Active Steps:
{steps_context}

Please propose status updates based on the transcript."""

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=VOICE_PROMPT,
                response_mime_type="application/json",
                response_schema=VoiceCheckinResult,
                temperature=0.1,
            ),
        )

        if not response.parsed:
            return VoiceCheckinResult(understood_transcript=transcript, proposed_changes=[])

        return response.parsed

    except Exception as e:
        # Log error or handle gracefully
        print(f"Voice check-in error: {e}")
        return VoiceCheckinResult(understood_transcript=transcript, proposed_changes=[])
