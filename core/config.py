import os
from zoneinfo import ZoneInfo

from langchain.chat_models import BaseChatModel
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_list_separator=",",
    )

    APP_PATH: str = Field(
        default=os.getcwd(),
        description="The base path of the application.",
    )
    MOUNT_FOLDER: str = Field(
        ...,
        description="The folder to mount for file operations. Should be an absolute path.",
    )

    LLM_MODEL: str = Field(
        ...,
        description="Default language model. Format: provider:model_name",
    )
    AVAILABLE_MODELS: list[str] = Field(
        default_factory=lambda: [
            "openai:gpt-5.6-terra",
            "openai:gpt-5.6-luna",
            "google_genai:gemini-3.5-flash",
            "google_genai:gemini-3.1-flash-lite-preview",
            "anthropic:claude-haiku-4-5",
            "anthropic:claude-sonnet-5",
            "lmstudio:qwen/qwen3.8-27b",
            "lmstudio:qwen/qwen3.6-35b-a3b",
            "lmstudio:google/gemma-4-12b-qat",
            "qwen:qwen3.8-max",
            "qwen:deepseek-v4-flash",
            "qwen:qwen3.7-plus",
            "qwen:qwen3.7-flash",
        ],
        description="Models shown in the UI selector (comma-separated). Defaults to LLM_MODEL only.",
    )
    LM_STUDIO_API_KEY: SecretStr | None = Field(
        default=None,
        description="API key for LM Studio when the lmstudio provider is selected.",
    )
    LM_STUDIO_BASE_URL: str | None = Field(
        default=None,
        description="Base URL for LM Studio when the lmstudio provider is selected.",
    )
    OPENAI_API_KEY: SecretStr | None = Field(
        default=None,
        description="API key for OpenAI when the openai provider is selected.",
    )
    ANTHROPIC_API_KEY: SecretStr | None = Field(
        default=None,
        description="API key for Anthropic when the anthropic provider is selected.",
    )
    GEMINI_API_KEY: SecretStr | None = Field(
        default=None,
        description="API key for Google GenAI when the google_genai provider is selected.",
    )
    QWEN_API_KEY: SecretStr | None = Field(
        default=None,
        description="API key for Qwen when the qwen provider is selected.",
    )
    QWEN_BASE_URL: str | None = Field(
        default=None,
        description="Base URL for Qwen when the qwen provider is selected.",
    )
    DEFAULT_TEMPERATURE: float = Field(
        0.7,
        description="Default temperature for LLM responses.",
    )
    APP_TIMEZONE: str = Field(
        default="America/New_York",
        description="IANA timezone name (e.g. 'America/New_York').",
    )

    @model_validator(mode="after")
    def validate_llm_model(self) -> "Settings":
        if self.llm_provider not in [
            "lmstudio",
            "openai",
            "anthropic",
            "google_genai",
            "qwen",
        ]:
            raise ValueError(
                f"Unsupported provider '{self.llm_provider}'. Supported providers are: lmstudio, openai, anthropic, google_genai, qwen."
            )

        if self.llm_provider == "lmstudio":
            if self.LM_STUDIO_API_KEY is None:
                raise ValueError(
                    "LM_STUDIO_API_KEY environment variable is required for lmstudio provider."
                )
            if not self.LM_STUDIO_BASE_URL:
                raise ValueError(
                    "LM_STUDIO_BASE_URL environment variable is required for lmstudio provider."
                )
        elif self.llm_provider == "openai":
            if self.OPENAI_API_KEY is None:
                raise ValueError(
                    "OPENAI_API_KEY environment variable is required for openai provider."
                )
        elif self.llm_provider == "anthropic":
            if self.ANTHROPIC_API_KEY is None:
                raise ValueError(
                    "ANTHROPIC_API_KEY environment variable is required for anthropic provider."
                )
        elif self.llm_provider == "google_genai":
            if self.GEMINI_API_KEY is None:
                raise ValueError(
                    "GEMINI_API_KEY environment variable is required for google_genai provider."
                )
        elif self.llm_provider == "qwen":
            if self.QWEN_API_KEY is None:
                raise ValueError(
                    "QWEN_API_KEY environment variable is required for qwen provider."
                )
            if not self.QWEN_BASE_URL:
                raise ValueError(
                    "QWEN_BASE_URL environment variable is required for qwen provider."
                )

        return self

    @property
    def llm_provider(self) -> str:
        return self.LLM_MODEL.split(":")[0]

    @property
    def llm_model_name(self) -> str:
        return self.LLM_MODEL.split(":", 1)[1]

    @property
    def all_available_models(self) -> list[str]:
        if self.AVAILABLE_MODELS:
            return self.AVAILABLE_MODELS
        return [self.LLM_MODEL]

    def get_llm_client(self, model_str: str) -> BaseChatModel:
        parts = model_str.split(":", 1)
        provider = parts[0]
        model_name = parts[1] if len(parts) > 1 else ""

        if provider == "lmstudio":
            return ChatOpenAI(
                base_url=self.LM_STUDIO_BASE_URL,
                model=model_name,
                temperature=self.DEFAULT_TEMPERATURE,
                use_responses_api=True,
                api_key=self.LM_STUDIO_API_KEY.get_secret_value(),
            )
        elif provider == "openai":
            return ChatOpenAI(
                model=model_name,
                temperature=self.DEFAULT_TEMPERATURE,
                api_key=self.OPENAI_API_KEY.get_secret_value(),
            )
        elif provider == "anthropic":
            return ChatAnthropic(
                model=model_name,
                temperature=self.DEFAULT_TEMPERATURE,
                api_key=self.ANTHROPIC_API_KEY.get_secret_value(),
            )
        elif provider == "google_genai":
            return ChatGoogleGenerativeAI(
                model=model_name,
                temperature=self.DEFAULT_TEMPERATURE,
                thinking_level="medium",
                api_key=self.GEMINI_API_KEY.get_secret_value(),
            )
        elif provider == "qwen":
            return ChatOpenAI(
                base_url=self.QWEN_BASE_URL,
                model=model_name,
                temperature=self.DEFAULT_TEMPERATURE,
                api_key=self.QWEN_API_KEY.get_secret_value(),
                extra_body={"enable_thinking": True},
            )
        raise ValueError(f"Unsupported provider '{provider}'")

    @property
    def llm_client(self) -> BaseChatModel:
        return self.get_llm_client(self.LLM_MODEL)

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.APP_TIMEZONE)

    @property
    def DB_PATH(self) -> str:
        return os.path.join(self.MOUNT_FOLDER, "db")

    @property
    def CHECKPOINTER_DATABASE_PATH(self) -> str:
        return os.path.join(self.DB_PATH, "langgraph-checkpoints.db")

    @property
    def APP_DATABASE_PATH(self) -> str:
        return os.path.join(self.DB_PATH, "job-finder.db")


settings = Settings()
