"""
Provider-agnostic LLM factory. Pick a free-tier provider via LLM_PROVIDER in
.env — no vendor lock-in required for the prototype.

  groq   -> free, very fast inference (OpenAI-compatible endpoint)
  google -> Google AI Studio free tier (Gemini)
  openai -> paid, included for completeness if you already have a key
"""
import os


def get_llm():
    provider = os.getenv("LLM_PROVIDER", "groq").lower()

    if provider == "groq":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
            temperature=0.9,
        )

    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=os.getenv("GOOGLE_MODEL", "gemini-1.5-flash"),
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.9,
        )

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0.9,
        )

    raise ValueError(f"Unknown LLM_PROVIDER: {provider}")