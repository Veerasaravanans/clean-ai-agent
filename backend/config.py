"""
config.py - Application Configuration

Loads all settings from .env file using pydantic-settings.
VIO Cloud Platform is the PRIMARY LLM provider.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Optional, Literal
from functools import lru_cache
from datetime import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # ═══════════════════════════════════════════════════════════
    # Server Settings
    # ═══════════════════════════════════════════════════════════
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # ═══════════════════════════════════════════════════════════
    # ADB Settings
    # ═══════════════════════════════════════════════════════════
    adb_device_serial: Optional[str] = Field(default=None, description="ADB device serial")
    adb_timeout: int = Field(default=10, description="ADB command timeout")
    adb_retry_count: int = Field(default=3, description="ADB retry attempts")
    
    # ═══════════════════════════════════════════════════════════
    # LLM Provider Selection
    # ═══════════════════════════════════════════════════════════
    llm_provider: Literal["vio_cloud", "ollama"] = Field(
        default="vio_cloud",
        description="Primary LLM provider"
    )
    
    # ═══════════════════════════════════════════════════════════
    # VIO Cloud Platform (PRIMARY)
    # ═══════════════════════════════════════════════════════════
    vio_base_url: str = Field(
        default="https://vio.automotive-wan.com:446",
        description="VIO API endpoint"
    )
    vio_username: str = Field(default="uih62283", description="VIO username")
    vio_api_token: str = Field(
        default="VPImz2XnDYkC_aeEfQTK1iAwKOEDNoTrPulgF6XcH5E",
        description="VIO API token"
    )
    vio_token_expiry: str = Field(default="2026-10-10", description="Token expiry date")
    vio_verify_ssl: bool = Field(default=False, description="Verify SSL certificate")
    vio_timeout: int = Field(default=30, description="VIO request timeout")
    vio_max_retries: int = Field(default=3, description="VIO max retries")
    
    # VIO Model Selection
    vio_primary_model: str = Field(
        default="claude-4-5-sonnet-v1:0",
        description="Primary VIO model"
    )
    vio_fallback_fast: str = Field(
        default="gemini-2.5-pro",
        description="Fast fallback model"
    )
    vio_fallback_cheap: str = Field(
        default="gpt-4o-mini",
        description="Cheap fallback model"
    )
    vio_enable_fallback: bool = Field(default=True, description="Enable model fallback")
    
    # VIO Features
    vio_enable_knowledge: bool = Field(default=False, description="Enable VIO knowledge base")
    vio_enable_websearch: bool = Field(default=False, description="Enable VIO web search")
    vio_enable_reasoning: bool = Field(default=True, description="Enable VIO reasoning")
    vio_temperature_reasoning: float = Field(default=0.1, description="Temperature for reasoning")
    vio_temperature_analysis: float = Field(default=0.3, description="Temperature for analysis")
    vio_temperature_creative: float = Field(default=0.7, description="Temperature for creative")
    
    # VIO Cost Management
    vio_track_costs: bool = Field(default=True, description="Track VIO costs")
    vio_monthly_budget: float = Field(default=50.0, description="Monthly budget USD")
    vio_alert_threshold: float = Field(default=40.0, description="Alert threshold USD")
    
    # ═══════════════════════════════════════════════════════════
    # Ollama Settings (Fallback/Local Development)
    # ═══════════════════════════════════════════════════════════
    ollama_endpoint: str = Field(
        default="http://localhost:11434",
        description="Ollama API endpoint"
    )
    ollama_model: str = Field(default="llama3.1:13b", description="Ollama model")
    ollama_vision_model: str = Field(default="llava:7b", description="Ollama vision model")
    ollama_timeout: int = Field(default=60, description="Ollama timeout")
    
    # ═══════════════════════════════════════════════════════════
    # Vision & OCR Settings
    # ═══════════════════════════════════════════════════════════
    ocr_engine: str = Field(default="advanced", description="OCR engine")
    ocr_confidence_threshold: int = Field(default=60, description="OCR confidence threshold")
    vision_timeout: int = Field(default=30, description="Vision processing timeout")
    vision_use_ai: bool = Field(default=True, description="Use AI for vision")
    
    # ═══════════════════════════════════════════════════════════
    # Screenshot Settings
    # ═══════════════════════════════════════════════════════════
    screenshot_dir: str = Field(default="./data/screenshots", description="Screenshots directory")
    screenshot_quality: int = Field(default=85, description="Screenshot JPEG quality")
    screenshot_max_width: int = Field(default=1280, description="Max screenshot width")
    stream_quality: int = Field(default=70, description="Stream JPEG quality")
    stream_max_width: int = Field(default=720, description="Max stream width")
    stream_fps: int = Field(default=15, description="Stream FPS")
    
    # ═══════════════════════════════════════════════════════════
    # RAG Settings
    # ═══════════════════════════════════════════════════════════
    vector_db_path: str = Field(default="./data/vector_db", description="ChromaDB path")
    prompts_path: str = Field(default="./data/prompts", description="Prompts directory")
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        description="Sentence transformer model"
    )
    rag_top_k: int = Field(default=5, description="RAG top K results")
    rag_min_similarity: float = Field(default=0.7, description="RAG minimum similarity")
    
    # ═══════════════════════════════════════════════════════════
    # Test Cases Settings
    # ═══════════════════════════════════════════════════════════
    test_cases_dir: str = Field(default="./data/test_cases", description="Test cases directory")
    results_dir: str = Field(default="./data/results", description="Results directory")
    learned_solutions_file: str = Field(
        default="./data/prompts/learned_solutions.md",
        description="Learned solutions file"
    )
    
    # ═══════════════════════════════════════════════════════════
    # Verification Settings
    # ═══════════════════════════════════════════════════════════
    change_threshold: float = Field(default=1.0, description="Screen change threshold")
    max_retries: int = Field(default=3, description="Max action retries")
    hitl_timeout: int = Field(default=300, description="HITL timeout seconds")
    verification_method: str = Field(default="hybrid", description="Verification method")
    
    # ═══════════════════════════════════════════════════════════
    # Logging Settings
    # ═══════════════════════════════════════════════════════════
    log_file: str = Field(default="./logs/agent.log", description="Log file path")
    log_rotation: str = Field(default="daily", description="Log rotation")
    log_retention_days: int = Field(default=30, description="Log retention days")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @field_validator("vio_token_expiry")
    def check_token_expiry(cls, v):
        """Check if VIO token is still valid."""
        try:
            expiry_date = datetime.fromisoformat(v)
            if datetime.now() > expiry_date:
                logger.warning(f"⚠️  VIO token expired on {v}! Regenerate in VIO Application.")
            else:
                days_left = (expiry_date - datetime.now()).days
                if days_left < 7:
                    logger.warning(f"⚠️  VIO token expires in {days_left} days! Regenerate soon.")
                else:
                    logger.info(f"✅ VIO token valid for {days_left} days")
        except Exception as e:
            logger.error(f"❌ Invalid token expiry date format: {v}")
        return v

    @field_validator("llm_provider")
    def validate_llm_provider(cls, v):
        """Validate LLM provider choice."""
        if v == "vio_cloud":
            logger.info("✅ Using VIO Cloud Platform (Primary)")
        elif v == "ollama":
            logger.info("✅ Using Ollama (Local/Fallback)")
        return v
    
    def get_vio_model_config(self, model_type: str = "primary") -> dict:
        """
        Get VIO model configuration.
        
        Args:
            model_type: "primary", "fallback_fast", or "fallback_cheap"
            
        Returns:
            Model configuration dict
        """
        models = {
            "primary": {
                "name": self.vio_primary_model,
                "display_name": "Claude 4.5 Sonnet",
                "provider": "bedrock",
                "temperature": self.vio_temperature_reasoning
            },
            "fallback_fast": {
                "name": self.vio_fallback_fast,
                "display_name": "Gemini 2.5 Pro",
                "provider": "vertex",
                "temperature": self.vio_temperature_analysis
            },
            "fallback_cheap": {
                "name": self.vio_fallback_cheap,
                "display_name": "GPT-4o Mini",
                "provider": "azure",
                "temperature": self.vio_temperature_analysis
            }
        }
        return models.get(model_type, models["primary"])
    
    def create_directories(self):
        """Create required directories if they don't exist."""
        directories = [
            self.screenshot_dir,
            self.vector_db_path,
            self.prompts_path,
            self.test_cases_dir,
            self.results_dir,
            Path(self.log_file).parent
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        logger.info("✅ All required directories created/verified")
    
    def validate_vio_connection(self) -> bool:
        """
        Validate VIO connection settings.
        
        Returns:
            True if valid, False otherwise
        """
        issues = []
        
        if not self.vio_username:
            issues.append("VIO_USERNAME not set")
        
        if not self.vio_api_token or len(self.vio_api_token) < 20:
            issues.append("VIO_API_TOKEN invalid or not set")
        
        if not self.vio_base_url.startswith("https://"):
            issues.append("VIO_BASE_URL must use HTTPS")
        
        if issues:
            logger.error(f"❌ VIO configuration issues: {', '.join(issues)}")
            return False
        
        logger.info("✅ VIO configuration valid")
        return True
    
    def print_summary(self):
        """Print configuration summary."""
        print("\n" + "="*80)
        print("  AI AGENT FRAMEWORK - CONFIGURATION")
        print("="*80)
        print(f"Server: {self.host}:{self.port}")
        print(f"Debug Mode: {self.debug}")
        print(f"Log Level: {self.log_level}")
        print(f"\nLLM Provider: {self.llm_provider.upper()}")
        if self.llm_provider == "vio_cloud":
            print(f"  VIO Endpoint: {self.vio_base_url}")
            print(f"  VIO Username: {self.vio_username}")
            print(f"  Primary Model: {self.vio_primary_model}")
            print(f"  Fallback Enabled: {self.vio_enable_fallback}")
        else:
            print(f"  Ollama Endpoint: {self.ollama_endpoint}")
            print(f"  Ollama Model: {self.ollama_model}")
        print(f"\nADB Device: {self.adb_device_serial or 'Auto-detect'}")
        print(f"Test Cases: {self.test_cases_dir}")
        print(f"Results: {self.results_dir}")
        print("="*80 + "\n")


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance (Singleton pattern).
    
    Returns:
        Settings instance
    """
    return Settings()


# ═══════════════════════════════════════════════════════════
# Global settings instance
# ═══════════════════════════════════════════════════════════
settings = get_settings()


# ═══════════════════════════════════════════════════════════
# Configuration checker for CLI
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    
    print("\n🔧 Configuration Module Test\n")
    
    try:
        # Load settings
        config = get_settings()
        
        # Print summary
        config.print_summary()
        
        # Validate VIO
        if config.llm_provider == "vio_cloud":
            if config.validate_vio_connection():
                print("✅ VIO configuration valid\n")
            else:
                print("❌ VIO configuration invalid\n")
                sys.exit(1)
        
        # Create directories
        config.create_directories()
        
        print("✅ Configuration module working correctly!\n")
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ Configuration error: {e}\n")
        sys.exit(1)