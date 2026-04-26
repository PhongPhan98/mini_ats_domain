import json

import google.generativeai as genai
from openai import OpenAI

from app.config import settings
from app.prompts import CV_PARSING_PROMPT, MATCHING_PROMPT


class LLMService:
    @staticmethod
    def _openai_compatible_parse_cv(*, api_key: str, model: str, base_url: str | None, cv_text: str, provider_name: str) -> dict:
        if not api_key:
            raise RuntimeError(f"{provider_name} api key is empty.")
        client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
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
    def _openai_compatible_match_candidate(*, api_key: str, model: str, base_url: str | None, job_title: str, requirements: str, candidate: dict, provider_name: str) -> dict:
        if not api_key:
            raise RuntimeError(f"{provider_name} api key is empty.")
        client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
        prompt = f"Job Title: {job_title}\nRequirements:\n{requirements}\n\nCandidate:\n{json.dumps(candidate, ensure_ascii=False)}"
        response = client.chat.completions.create(
            model=model,
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
        return {"match_score": score, "explanation": data.get("explanation", "No explanation provided.")}

    @staticmethod
    def _openai_parse_cv(cv_text: str) -> dict:
        return LLMService._openai_compatible_parse_cv(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            base_url=None,
            cv_text=cv_text,
            provider_name="openai",
        )

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
    def _openrouter_parse_cv(cv_text: str) -> dict:
        return LLMService._openai_compatible_parse_cv(
            api_key=settings.openrouter_api_key,
            model=settings.openrouter_model,
            base_url="https://openrouter.ai/api/v1",
            cv_text=cv_text,
            provider_name="openrouter",
        )

    @staticmethod
    def _openrouter_match_candidate(job_title: str, requirements: str, candidate: dict) -> dict:
        return LLMService._openai_compatible_match_candidate(
            api_key=settings.openrouter_api_key,
            model=settings.openrouter_model,
            base_url="https://openrouter.ai/api/v1",
            job_title=job_title,
            requirements=requirements,
            candidate=candidate,
            provider_name="openrouter",
        )

    @staticmethod
    def _groq_parse_cv(cv_text: str) -> dict:
        return LLMService._openai_compatible_parse_cv(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            base_url="https://api.groq.com/openai/v1",
            cv_text=cv_text,
            provider_name="groq",
        )

    @staticmethod
    def _groq_match_candidate(job_title: str, requirements: str, candidate: dict) -> dict:
        return LLMService._openai_compatible_match_candidate(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            base_url="https://api.groq.com/openai/v1",
            job_title=job_title,
            requirements=requirements,
            candidate=candidate,
            provider_name="groq",
        )

    @staticmethod
    def _ollama_parse_cv(cv_text: str) -> dict:
        return LLMService._openai_compatible_parse_cv(
            api_key="ollama",
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            cv_text=cv_text,
            provider_name="ollama",
        )

    @staticmethod
    def _ollama_match_candidate(job_title: str, requirements: str, candidate: dict) -> dict:
        return LLMService._openai_compatible_match_candidate(
            api_key="ollama",
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            job_title=job_title,
            requirements=requirements,
            candidate=candidate,
            provider_name="ollama",
        )



    @staticmethod
    def _gemini_parse_cv_from_file(file_name: str, content: bytes, mime_type: str) -> dict:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is empty. Set it or switch LLM_PROVIDER.")
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.gemini_model)
        prompt = (
            CV_PARSING_PROMPT
            + "\n\nReturn ONLY valid JSON object. No markdown, no extra text."
            + "\nInput file may be scanned/image-based. Extract best-effort structured candidate info."
        )
        response = model.generate_content([
            {"text": prompt},
            {"inline_data": {"mime_type": mime_type, "data": content}},
        ])
        text = (response.text or "{}").strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()
        return json.loads(text)

    @staticmethod
    def parse_cv_from_file(file_name: str, content: bytes, mime_type: str) -> dict:
        provider = settings.llm_provider.strip().lower()
        return LLMService.parse_cv_file_for_provider(provider, file_name, content, mime_type)

    @staticmethod
    def parse_cv_for_provider(provider: str, cv_text: str) -> dict:
        p = (provider or "").strip().lower()
        if p == "gemini":
            return LLMService._gemini_parse_cv(cv_text)
        if p == "openrouter":
            return LLMService._openrouter_parse_cv(cv_text)
        if p == "groq":
            return LLMService._groq_parse_cv(cv_text)
        if p == "ollama":
            return LLMService._ollama_parse_cv(cv_text)
        return LLMService._openai_parse_cv(cv_text)

    @staticmethod
    def parse_cv_file_for_provider(provider: str, file_name: str, content: bytes, mime_type: str) -> dict:
        p = (provider or "").strip().lower()
        if p == "gemini":
            return LLMService._gemini_parse_cv_from_file(file_name, content, mime_type)
        raise RuntimeError(f"File-vision parse not supported for provider: {provider}")

    @staticmethod
    def parse_cv(cv_text: str) -> dict:
        provider = settings.llm_provider.strip().lower()
        return LLMService.parse_cv_for_provider(provider, cv_text)

    @staticmethod
    def match_candidate(job_title: str, requirements: str, candidate: dict) -> dict:
        provider = settings.llm_provider.strip().lower()
        if provider == "gemini":
            return LLMService._gemini_match_candidate(job_title, requirements, candidate)
        if provider == "openrouter":
            return LLMService._openrouter_match_candidate(job_title, requirements, candidate)
        if provider == "groq":
            return LLMService._groq_match_candidate(job_title, requirements, candidate)
        if provider == "ollama":
            return LLMService._ollama_match_candidate(job_title, requirements, candidate)
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
