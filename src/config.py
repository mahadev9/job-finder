import os

from langchain.chat_models import BaseChatModel
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
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
        description="The language model to use for generating responses. Format: provider:model_name (e.g., 'openai:gpt-5.4')",
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
    DEFAULT_TEMPERATURE: float = Field(
        0.7,
        description="The default temperature for language model responses. Higher values (e.g., 0.9) make output more random, while lower values (e.g., 0.2) make it more focused and deterministic.",
    )

    @model_validator(mode="after")
    def validate_llm_model(self) -> "Settings":
        if self.llm_provider not in ["lmstudio", "openai", "anthropic", "google_genai"]:
            raise ValueError(
                f"Unsupported provider '{self.llm_provider}'. Supported providers are: lmstudio, openai, anthropic, google_genai."
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

        return self

    @property
    def llm_provider(self) -> str:
        return self.LLM_MODEL.split(":")[0]

    @property
    def llm_model_name(self) -> str:
        return self.LLM_MODEL.split(":", 1)[1]

    @property
    def llm_client(self) -> BaseChatModel:
        if self.llm_provider == "lmstudio":
            return ChatOpenAI(
                base_url=self.LM_STUDIO_BASE_URL,
                model=self.llm_model_name,
                temperature=self.DEFAULT_TEMPERATURE,
                use_responses_api=True,
                api_key=self.LM_STUDIO_API_KEY.get_secret_value(),
            )
        elif self.llm_provider == "openai":
            return ChatOpenAI(
                model=self.llm_model_name,
                temperature=self.DEFAULT_TEMPERATURE,
                api_key=self.OPENAI_API_KEY.get_secret_value(),
            )
        elif self.llm_provider == "anthropic":
            return ChatAnthropic(
                model=self.llm_model_name,
                temperature=self.DEFAULT_TEMPERATURE,
                api_key=self.ANTHROPIC_API_KEY.get_secret_value(),
            )
        elif self.llm_provider == "google_genai":
            return ChatGoogleGenerativeAI(
                model=self.llm_model_name,
                temperature=self.DEFAULT_TEMPERATURE,
                thinking_level="medium",
                api_key=self.GEMINI_API_KEY.get_secret_value(),
            )

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
