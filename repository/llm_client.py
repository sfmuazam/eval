from __future__ import annotations
import os, json, re, logging, time
from dataclasses import dataclass
from typing import Optional

from settings import GROQ_API_KEY, LLM_FAILOPEN, LLM_MODEL, LLM_PROVIDER, LLM_RETRIES, LLM_TIMEOUT_SEC

try:
    import httpx
except Exception:
    httpx = None

log = logging.getLogger("llm")

@dataclass
class LLMResponse:
    content: str

class MockLLM:
    def __init__(self):
        self.last_raw = {"backend": "mock"}

    @staticmethod
    def _contains_any(s: str, keys: list[str]) -> bool:
        s = (s or "").lower()
        return any(k.lower() in s for k in keys)

    def generate_json(self, prompt: str, **kwargs):
        p = (prompt or "")

        if self._contains_any(p, ['overall_summary', 'return json only with this exact schema']):
            return {
                "overall_summary": "Mock summary without a live LLM.",
                "recommendation": "hold",
                "strengths": ["stable mock path"],
                "gaps": ["no model reasoning"],
                "next_steps": ["enable LLM or review manually"]
            }
        if self._contains_any(p, ["project scorer", "project score", "[project_text]", "project rubric"]):
            return {"corr":3, "code":3, "res":3, "docs":3, "bonus":3, "feedback":"Mock project feedback."}
        if self._contains_any(p, ["cv scorer", "cv scores", "score the candidate's cv", "[extracted_cv_json]"]):
            return {"skills":3, "exp":3, "ach":3, "culture":3, "feedback":"Mock CV feedback."}
        if self._contains_any(p, ["information extractor", "fields (all required)", "return a strict json object"]):
            return {
                "skills_backend": [],
                "skills_db": [],
                "skills_api": [],
                "skills_cloud": [],
                "skills_ai": [],
                "experience_years": 0.0,
                "projects": []
            }
        return {}

    def generate(self, prompt: str, **kwargs):
        class R:
            content = "ok"
        self.last_raw = {"backend": "mock", "prompt": prompt}
        return R()

class GroqLLM:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, base_url: Optional[str] = None):
        if httpx is None:
            raise RuntimeError("httpx is not installed.")
        self.api_key = api_key or GROQ_API_KEY
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY is not set.")
        self.model = model or LLM_MODEL
        self.base_url = (base_url or os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")).rstrip("/")
        self.timeout = float(LLM_TIMEOUT_SEC)
        self.retries = int(LLM_RETRIES)
        self.failopen = bool(LLM_FAILOPEN)

        self._timeout = httpx.Timeout(connect=self.timeout, read=self.timeout, write=self.timeout, pool=self.timeout)
        self._client = httpx.Client(timeout=self._timeout, trust_env=True)

        self.last_error: str | None = None
        self.last_raw: str | None = None

        log.info(f"[LLM] Groq init model={self.model} base={self.base_url} timeout={self.timeout}s retries={self.retries} failopen={self.failopen}")

    def _chat_once(self, messages, temperature: float, max_tokens: int, force_json: bool) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": self.model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
        if force_json:
            payload["response_format"] = {"type": "json_object"}

        r = self._client.post(url, headers=headers, json=payload)

        if r.status_code == 400 and force_json:
            log.warning("[LLM] 400 with response_format=json_object; retrying without response_format")
            payload.pop("response_format", None)
            r = self._client.post(url, headers=headers, json=payload)

        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            body = e.response.text
            msg = f"HTTP {e.response.status_code}: {body[:1000]}"
            self.last_error = msg
            log.error(f"[LLM] {msg}")
            raise

        data = r.json()
        return data["choices"][0]["message"]["content"]

    def _chat(self, messages, temperature: float, max_tokens: int, force_json: bool) -> str:
        last_err = None
        for attempt in range(self.retries + 1):
            t0 = time.time()
            try:
                log.info(f"[LLM] groq call (force_json={force_json}) attempt={attempt+1}")
                out = self._chat_once(messages, temperature, max_tokens, force_json)
                dt = (time.time() - t0) * 1000
                log.info(f"[LLM] groq ok in {dt:.0f} ms")
                return out
            except Exception as e:
                last_err = e
                log.warning(f"[LLM] groq error attempt={attempt+1}: {e}")
        if self.failopen:
            self.last_error = f"fail-open after retries: {last_err}"
            log.error(f"[LLM] groq failed after retries; fail-open.")
            return "{}"
        raise last_err

    def generate(self, prompt: str, temperature: float = 0.1, max_tokens: int = 1024) -> LLMResponse:
        content = self._chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            force_json=False,
        )
        self.last_raw = content
        return LLMResponse(content=content)

    def generate_json(self, prompt: str, temperature: float = 0.1, max_tokens: int = 1024) -> dict:
        raw = self._chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            force_json=True,
        )
        text = raw.strip()
        self.last_raw = text
        text = re.sub(r"^```(json)?\s*|\s*```$", "", text, flags=re.I)
        try:
            return json.loads(text)
        except Exception:
            m = re.search(r"\{.*\}", text, flags=re.S)
            if m:
                try:
                    return json.loads(m.group(0))
                except Exception:
                    pass
            return {}

def get_llm():
    backend = (LLM_PROVIDER or "").lower()
    if backend == "groq":
        try:
            return GroqLLM()
        except Exception as e:
            if LLM_FAILOPEN:
                log.error(f"[LLM] Groq init failed: {e}. Fallback to MockLLM.")
                return MockLLM()
            raise
    return MockLLM()
