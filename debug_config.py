import sys, os
sys.path.insert(0, '.')

from src.config import get_settings
s = get_settings()

print("=== CONFIG ===")
print(f"model_name: {s.model_name}")
print(f"openai_api_key set: {bool(s.openai_api_key)}")
print(f"openai_api_key prefix: {s.openai_api_key[:15] if s.openai_api_key else 'None'}")
print(f"gemini_api_key set: {bool(s.gemini_api_key)}")
print(f"google_api_key set: {bool(s.google_api_key)}")
print(f"chroma_host: {repr(s.chroma_host)}")
print(f"chroma_port: {s.chroma_port}")
print(f"llm_temperature: {s.llm_temperature}")
print(f"get_api_base: {repr(s.get_api_base)}")

openai_key = s.openai_api_key
gemini_key = s.gemini_api_key or s.google_api_key

print()
print("=== RAG LLM BRANCH ===")
if openai_key:
    effective_model = s.model_name if s.model_name.startswith("gpt-") else "gpt-4o-mini"
    print(f"Branch: OpenAI")
    print(f"Effective model: {effective_model}")
    print(f"base_url: {repr(s.get_api_base)}")
elif gemini_key:
    effective_model = s.model_name if s.model_name.startswith("gemini-") else "gemini-1.5-flash"
    print(f"Branch: Gemini")
    print(f"Effective model: {effective_model}")
else:
    print("Branch: NO KEY -> will raise RuntimeError")

print()
print("=== CHROMA MODE ===")
from src.services.vector_store_config import build_chroma_connection_kwargs
kwargs = build_chroma_connection_kwargs(s)
print(f"Chroma kwargs: {kwargs}")
