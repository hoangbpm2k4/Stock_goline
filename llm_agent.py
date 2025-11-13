import os
from typing import Optional

# Gemini
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False


class LLMAgent:
    def __init__(
        self,
        provider: str = "gemini",
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.provider = provider.lower()
        self.api_key = api_key
        self.model_name = model
        self.client = None

        if self.provider == "gemini":
            self._init_gemini()
        elif self.provider == "openai":
            raise NotImplementedError("OpenAI provider chưa được implement. Có thể thêm sau.")
        elif self.provider == "claude":
            raise NotImplementedError("Claude provider chưa được implement. Có thể thêm sau.")
        else:
            raise ValueError(f"Provider '{provider}' không được support. Available: gemini")

    def _init_gemini(self):
        """Initialize Gemini client"""
        if not HAS_GEMINI:
            raise ImportError("Cần cài đặt: pip install google-generativeai")

        self.api_key = self.api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = self.model_name or os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY không tồn tại. Set env hoặc pass qua api_key param.")

        genai.configure(api_key=self.api_key)
        self.client = genai.GenerativeModel(self.model_name)

    def generate(self, prompt: str) -> str:
        if not self.is_ready():
            raise RuntimeError(f"LLM Agent ({self.provider}) chưa sẵn sàng")

        if self.provider == "gemini":
            return self._generate_gemini(prompt)
        else:
            raise NotImplementedError(f"Provider {self.provider} chưa implement generate()")

    def _generate_gemini(self, prompt: str) -> str:
        """Generate từ Gemini"""
        try:
            response = self.client.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            raise RuntimeError(f"Lỗi Gemini API: {str(e)}")

    def is_ready(self) -> bool:
        return self.client is not None

    def info(self) -> dict:
        """Thông tin về agent"""
        return {
            "provider": self.provider,
            "model": self.model_name,
            "ready": self.is_ready()
        }
