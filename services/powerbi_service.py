"""
Power BI Service module.
Handles Azure AD authentication and Power BI REST API interactions.
Implements token caching to avoid unnecessary token requests.
"""

import time
from typing import Optional, Tuple
import msal
import requests
from config import Config


class PowerBIService:
    """
    Service class for Power BI Embedded operations.
    Implements AAD authentication with token caching and embed token generation.
    """
    
    # Class-level token cache
    _cached_token: Optional[str] = None
    _token_expiry: float = 0
    
    # Buffer time in seconds before token expiry to refresh (5 minutes)
    TOKEN_REFRESH_BUFFER = 300
    
    def __init__(self):
        """
        Initialize the Power BI service with MSAL confidential client.
        Only creates the MSAL client if configuration is complete.
        """
        self.client_id = Config.CLIENT_ID
        self.client_secret = Config.CLIENT_SECRET
        self.tenant_id = Config.TENANT_ID
        self.authority = Config.AUTHORITY_URL
        self.scope = [Config.POWER_BI_SCOPE]
        self.api_url = Config.POWER_BI_API_URL
        
        # Only initialize MSAL client if credentials are configured
        if Config.is_configured():
            self.msal_app = msal.ConfidentialClientApplication(
                client_id=self.client_id,
                client_credential=self.client_secret,
                authority=self.authority,
            )
        else:
            self.msal_app = None
    
    def get_access_token(self) -> Tuple[str, float]:
        """
        Acquires an Azure AD access token for Power BI API.
        Implements caching to avoid requesting a new token if current one is valid.
        
        Returns:
            Tuple containing (access_token, expiry_timestamp)
            
        Raises:
            Exception: If token acquisition fails or service is not configured
        """
        # Check if MSAL client is initialized
        if self.msal_app is None:
            missing = Config.get_missing_vars()
            raise Exception(f"Power BI service not configured. Missing: {', '.join(missing)}")
        
        current_time = time.time()
        
        # Check if cached token is still valid (with buffer time)
        if (PowerBIService._cached_token and 
            PowerBIService._token_expiry > current_time + self.TOKEN_REFRESH_BUFFER):
            return PowerBIService._cached_token, PowerBIService._token_expiry
        
        # Acquire a new token using client credentials flow
        result = self.msal_app.acquire_token_for_client(scopes=self.scope)
        
        if "access_token" in result:
            # Cache the token and calculate expiry time
            PowerBIService._cached_token = result["access_token"]
            # expires_in is in seconds; convert to absolute timestamp
            expires_in = result.get("expires_in", 3600)
            PowerBIService._token_expiry = current_time + expires_in
            
            return PowerBIService._cached_token, PowerBIService._token_expiry
        
        # Handle error cases
        error_description = result.get("error_description", "Unknown error")
        error_code = result.get("error", "unknown_error")
        raise Exception(f"Failed to acquire AAD token: [{error_code}] {error_description}")
    
    def get_report_embed_url(self, workspace_id: str, report_id: str) -> dict:
        """
        Gets the embed URL and other details for a report from Power BI API.
        
        Args:
            workspace_id: The Power BI workspace (group) ID
            report_id: The Power BI report ID
            
        Returns:
            Dictionary containing report details including embedUrl
            
        Raises:
            Exception: If API call fails
        """
        access_token, _ = self.get_access_token()
        
        url = f"{self.api_url}/groups/{workspace_id}/reports/{report_id}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            raise Exception("Unauthorized: Invalid or expired access token")
        elif response.status_code == 403:
            raise Exception(
                "Forbidden: Service Principal doesn't have access to this report. "
                "Ensure the app is added to the workspace as Admin or Member."
            )
        elif response.status_code == 404:
            raise Exception(
                f"Report not found: Check WORKSPACE_ID ({workspace_id}) and "
                f"REPORT_ID ({report_id}) are correct."
            )
        else:
            raise Exception(
                f"Failed to get report details: HTTP {response.status_code} - {response.text}"
            )
    
    def generate_embed_token(
        self, 
        workspace_id: str, 
        report_id: str, 
        dataset_id: Optional[str] = None,
        access_level: str = "View"
    ) -> dict:
        """
        Generates an embed token for the specified report using Power BI REST API.
        
        Args:
            workspace_id: The Power BI workspace (group) ID
            report_id: The Power BI report ID
            dataset_id: Optional dataset ID for additional permissions
            access_level: Access level for the token ("View", "Edit", "Create")
            
        Returns:
            Dictionary containing the embed token and expiry information
            
        Raises:
            Exception: If token generation fails
        """
        access_token, _ = self.get_access_token()
        
        # Use the GenerateToken API endpoint for reports
        url = f"{self.api_url}/groups/{workspace_id}/reports/{report_id}/GenerateToken"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Request body for embed token generation
        body = {
            "accessLevel": access_level,
            "allowSaveAs": False  # Set to True if you need SaveAs capability
        }
        
        # If dataset ID is provided, include it for scenarios requiring dataset access
        if dataset_id:
            body["datasetId"] = dataset_id
        
        response = requests.post(url, headers=headers, json=body)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            raise Exception("Unauthorized: Invalid or expired access token")
        elif response.status_code == 403:
            raise Exception(
                "Forbidden: Cannot generate embed token. "
                "Ensure the workspace has Pro/Premium capacity and "
                "the Service Principal has proper permissions."
            )
        else:
            raise Exception(
                f"Failed to generate embed token: HTTP {response.status_code} - {response.text}"
            )
    
    def get_embed_config(self) -> dict:
        """
        Gets complete embed configuration including embed URL and token.
        This is the main method called by the API endpoint.
        
        Returns:
            Dictionary containing all information needed to embed the report:
            - accessToken: AAD token (for reference/debugging, typically not exposed)
            - embedToken: The token used for embedding
            - embedUrl: URL for the report
            - reportId: Report identifier
            - datasetId: Dataset identifier (if available)
            - tokenExpiry: When the embed token expires
            
        Raises:
            Exception: If any step in the process fails
        """
        workspace_id = Config.WORKSPACE_ID
        report_id = Config.REPORT_ID
        dataset_id = Config.DATASET_ID if Config.DATASET_ID else None
        
        # Get report details including embed URL
        report_details = self.get_report_embed_url(workspace_id, report_id)
        embed_url = report_details.get("embedUrl")
        actual_dataset_id = report_details.get("datasetId", dataset_id)
        
        # Generate embed token
        embed_token_response = self.generate_embed_token(
            workspace_id=workspace_id,
            report_id=report_id,
            dataset_id=actual_dataset_id,
        )
        
        embed_token = embed_token_response.get("token")
        token_expiry = embed_token_response.get("expiration")
        
        return {
            "embedToken": embed_token,
            "embedUrl": embed_url,
            "reportId": report_id,
            "datasetId": actual_dataset_id,
            "tokenExpiry": token_expiry,
        }


# Create a singleton instance for use throughout the application
powerbi_service = PowerBIService()
