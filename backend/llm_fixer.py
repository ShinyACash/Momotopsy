from __future__ import annotations

import logging
from typing import Any

from groq import AsyncGroq
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_LLM_MODEL: str = "llama-3.3-70b-versatile"

_SYSTEM_PROMPT: str = (
    "You are a senior legal contract analyst. The user will provide a single "
    "predatory contract clause. Analyze it and respond with ONLY a JSON object "
    "matching this exact schema — no markdown, no explanation outside the JSON:\n\n"
    "{\n"
    '  "reason_flagged": "One sentence explaining why this clause is predatory.",\n'
    '  "key_issues": ["Issue 1", "Issue 2"],\n'
    '  "improved_clause": "A rewritten, legally fair version of the clause."\n'
    "}\n\n"
    "Rules:\n"
    "- reason_flagged: exactly 1 sentence.\n"
    "- key_issues: 2-5 concise bullet points.\n"
    "- improved_clause: a complete, standalone clause — not a diff or fragment.\n"
    "- Output valid JSON only. No trailing commas. No comments."
)


class ClauseAnalysis(BaseModel):
    reason_flagged: str = Field(
        description="One sentence explaining why the clause is predatory",
    )
    key_issues: list[str] = Field(
        description="List of key legal issues",
    )
    improved_clause: str = Field(
        description="Rewritten safe version of the clause",
    )


_EMPTY_RESULT: dict[str, Any] = {
    "reason_flagged": "",
    "key_issues": [],
    "improved_clause": "",
}


class ClauseFixer:
    def __init__(self, model: str = _LLM_MODEL) -> None:
        self.client: AsyncGroq = AsyncGroq()  # reads GROQ_API_KEY from env
        self.model: str = model

    async def analyze_clause(self, text: str) -> dict[str, Any]:
        """Send a predatory clause to the LLM and return structured analysis.

        Returns a dict with keys: reason_flagged, key_issues, improved_clause.
        On any failure, returns empty/default fields instead of raising.
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=512,
            )
            raw: str = response.choices[0].message.content or ""
            analysis = ClauseAnalysis.model_validate_json(raw)
            return analysis.model_dump()

        except Exception as exc:
            logger.warning(
                "LLM analysis failed for clause: %.80s — %s", text, exc,
            )
            return dict(_EMPTY_RESULT)

    async def generate_negotiation_doc(self, original_clause: str, improved_clause: str, doc_type: str) -> dict[str, str]:
        """Generate a polite but firm legal negotiation email to demand the improved clause."""
        prompt = (
            f"You are a highly professional, polite, but extremely firm legal advocate. "
            f"The user is preparing to negotiate a predatory clause found in their {doc_type}.\n\n"
            f"Predatory Clause:\n{original_clause}\n\n"
            f"Improved, Fair Clause:\n{improved_clause}\n\n"
            "Task: Generate an assertive email template to send to the opposing party (e.g. landlord, employer, company) "
            "requesting the removal of the toxic clause and the implementation of the fair clause. "
            "Explicitly cite why the original clause is unreasonable and present the improved clause as the standard industry alternative. "
            "Leave [bracketed] placeholders for names.\n\n"
            "Output ONLY a JSON object matching this exact schema:\n"
            '{"email_subject": "...", "email_body": "..."}'
        )
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=800,
            )
            import json
            raw: str = response.choices[0].message.content or "{}"
            result = json.loads(raw)
            return {
                "email_subject": result.get("email_subject", "Contract Negotiation Request"),
                "email_body": result.get("email_body", "Error parsing LLM output.")
            }
        except Exception as exc:
            logger.warning("Generation failed for negotiation doc: %s", exc)
            return {
                "email_subject": "Contract Clarification Requested",
                "email_body": "System timed out communicating with AI services. Please manually request the clause change."
            }

    async def extract_lifecycle_events(self, document_text: str) -> list[dict]:
        """Extract explicit deadlines and contractual milestone dates."""
        prompt = (
            "You are a contract analysis AI. Review the following complete document text and extract all explicit or implicit deadlines, lifecycle events, and critical dates (e.g., Expiration, Auto-Renewal, Term Start, Payment Due, Contract Termination, Intern End Date, KYC Request).\n\n"
            "Output ONLY a JSON object containing a 'deadlines' list array matching this schema exactly:\n"
            '{"deadlines": [{"event_type": "Auto-Renewal", "date_str": "YYYY-MM-DD", "description": "The contract will automatically renew if not cancelled."}]}\n\n'
            "If no clear dates exist or cannot be parsed into YYYY-MM-DD format based on context, return {'deadlines': []}. "
            "Never make up a date. Use your best contextual guess if a year is implicit.\n\n"
            f"Document Text:\n{document_text[:20000]}"
        )
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=800,
            )
            import json
            raw: str = response.choices[0].message.content or "{}"
            result = json.loads(raw)
            return result.get("deadlines", [])
        except Exception as exc:
            logger.warning("Failed to extract lifecycle events: %s", exc)
            return []
