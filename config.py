"""
Configuration module for Power BI Embedded application.
Loads and validates environment variables at startup (fail-fast approach).
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """
    Configuration class that loads and validates all required environment variables.
    Raises ValueError if any required variable is missing.
    """
    
    # Azure AD / Service Principal credentials
    CLIENT_ID: str = os.getenv("CLIENT_ID", "")
    CLIENT_SECRET: str = os.getenv("CLIENT_SECRET", "")
    TENANT_ID: str = os.getenv("TENANT_ID", "")
    
    # Power BI workspace and report identifiers
    WORKSPACE_ID: str = os.getenv("WORKSPACE_ID", "")
    REPORT_ID: str = os.getenv("REPORT_ID", "")
    
    # Optional: Dataset ID (if needed for row-level security or specific scenarios)
    DATASET_ID: str = os.getenv("DATASET_ID", "")

    # Filter configuration used by /api/filter-values.
    FILTER_TABLE_NAME: str = os.getenv("FILTER_TABLE_NAME", "Sales")
    FILTER_TABLE_CANDIDATES: list = [
        value.strip()
        for value in os.getenv("FILTER_TABLE_CANDIDATES", "Sales,SalesForecast").split(",")
        if value.strip()
    ]
    FILTER_COLUMN_NAME: str = os.getenv("FILTER_COLUMN_NAME", "Product")
    
    # Power BI API scope for authentication
    POWER_BI_SCOPE: str = "https://analysis.windows.net/powerbi/api/.default"
    
    # Azure AD authority URL
    AUTHORITY_URL: str = f"https://login.microsoftonline.com/{TENANT_ID}"
    
    # Power BI API base URL
    POWER_BI_API_URL: str = "https://api.powerbi.com/v1.0/myorg"
    
    # Flask configuration
    SECRET_KEY: str = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG: bool = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")
    
    @classmethod
    def validate(cls) -> tuple:
        """
        Validates that all required environment variables are set.
        Returns a tuple of (is_valid: bool, missing_vars: list).
        Does NOT raise an exception - allows the app to start and show the frontend.
        """
        required_vars = {
            "CLIENT_ID": cls.CLIENT_ID,
            "CLIENT_SECRET": cls.CLIENT_SECRET,
            "TENANT_ID": cls.TENANT_ID,
            "WORKSPACE_ID": cls.WORKSPACE_ID,
            "REPORT_ID": cls.REPORT_ID,
        }
        
        missing_vars = [name for name, value in required_vars.items() if not value]
        
        return (len(missing_vars) == 0, missing_vars)
    
    @classmethod
    def is_configured(cls) -> bool:
        """
        Returns True if all required environment variables are set.
        """
        is_valid, _ = cls.validate()
        return is_valid
    
    @classmethod
    def get_missing_vars(cls) -> list:
        """
        Returns list of missing environment variable names.
        """
        _, missing = cls.validate()
        return missing
    
    @classmethod
    def get_embed_config(cls) -> dict:
        """
        Returns a dictionary with the embed configuration parameters.
        """
        return {
            "workspace_id": cls.WORKSPACE_ID,
            "report_id": cls.REPORT_ID,
            "dataset_id": cls.DATASET_ID,
        }


# Log configuration status on startup (but don't fail)
is_valid, missing = Config.validate()
if not is_valid:
    print(f"WARNING: Missing environment variables: {', '.join(missing)}")
    print("The frontend will load, but Power BI embedding will fail until configured.")
    print("Copy .env.example to .env and fill in your values.")
