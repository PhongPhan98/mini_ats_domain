import json

import google.generativeai as genai
from openai import OpenAI

from app.config import settings
from app.prompts import CV_PARSING_PROMPT, MATCHING_PROMPT


class LLMService:
    @staticmethod
    def _openai_parse_cv(cv_text: str) -> dict:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is empty. Set it or switch LLM_PROVIDER=gemini.")
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": CV_PARSING_PROMPT},
                {"role": "user", "content": cv_text[:12000]},
            ],
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)

    @staticmethod
    def _openai_match_candidate(job_title: str, requirements: str, candidate: dict) -> dict:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is empty. Set it or switch LLM_PROVIDER=gemini.")
        client = OpenAI(api_key=settings.openai_api_key)
        prompt = f"Job Title: {job_title}\nRequirements:\n{requirements}\n\nCandidate:\n{json.dumps(candidate, ensure_ascii=False)}"
        response = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": MATCHING_PROMPT},
                {"role": "user", "content": prompt[:12000]},
            ],
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        score = int(max(0, min(100, data.get("match_score", 0))))
        return {
            "match_score": score,
            "explanation": data.get("explanation", "No explanation provided."),
        }

    @staticmethod
    def _gemini_json(prompt: str, payload: str) -> dict:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is empty. Set it or switch LLM_PROVIDER=openai.")
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.gemini_model)

        full_prompt = (
            f"{prompt}\n\n"
            "Return ONLY valid JSON object. No markdown, no extra text.\n\n"
            f"INPUT:\n{payload[:12000]}"
        )
        response = model.generate_content(full_prompt)
        text = (response.text or "{}").strip()

        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()

        return json.loads(text)

    @staticmethod
    def _gemini_parse_cv(cv_text: str) -> dict:
        return LLMService._gemini_json(CV_PARSING_PROMPT, cv_text)

    @staticmethod
    def _gemini_match_candidate(job_title: str, requirements: str, candidate: dict) -> dict:
        payload = f"Job Title: {job_title}\nRequirements:\n{requirements}\n\nCandidate:\n{json.dumps(candidate, ensure_ascii=False)}"
        data = LLMService._gemini_json(MATCHING_PROMPT, payload)
        score = int(max(0, min(100, data.get("match_score", 0))))
        return {
            "match_score": score,
            "explanation": data.get("explanation", "No explanation provided."),
        }

    @staticmethod
    def parse_cv(cv_text: str) -> dict:
        provider = settings.llm_provider.strip().lower()
        if provider == "gemini":
            return LLMService._gemini_parse_cv(cv_text)
        return LLMService._openai_parse_cv(cv_text)

    @staticmethod
    def match_candidate(job_title: str, requirements: str, candidate: dict) -> dict:
        provider = settings.llm_provider.strip().lower()
        if provider == "gemini":
            return LLMService._gemini_match_candidate(job_title, requirements, candidate)
        return LLMService._openai_match_candidate(job_title, requirements, candidate)


def llm_match_candidates(job, candidates: list) -> list[dict]:
    """Compatibility helper for jobs router."""
    results: list[dict] = []
    for c in candidates:
        candidate_payload = {
            "name": getattr(c, "name", None),
            "email": getattr(c, "email", None),
            "phone": getattr(c, "phone", None),
            "skills": getattr(c, "skills", []) or [],
            "years_of_experience": getattr(c, "years_of_experience", None),
            "education": getattr(c, "education", []) or [],
            "previous_companies": getattr(c, "previous_companies", []) or [],
            "summary": getattr(c, "summary", None),
        }
        match = LLMService.match_candidate(job.title, job.requirements, candidate_payload)
        results.append(
            {
                "candidate_id": c.id,
                "candidate_name": getattr(c, "name", None),
                "match_score": match["match_score"],
                "explanation": match["explanation"],
            }
        )

    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results
