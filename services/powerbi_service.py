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
    
    def get_workspace_info(self, workspace_id: str) -> dict:
        """
        Gets workspace information from Power BI API.
        
        Args:
            workspace_id: The Power BI workspace (group) ID
            
        Returns:
            Dictionary containing workspace details
            
        Raises:
            Exception: If API call fails
        """
        access_token, _ = self.get_access_token()
        
        url = f"{self.api_url}/groups/{workspace_id}"
        
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
                "Forbidden: Service Principal doesn't have access to this workspace. "
                "Ensure the app is added to the workspace as Admin or Member."
            )
        elif response.status_code == 404:
            raise Exception(
                f"Workspace not found: Check WORKSPACE_ID ({workspace_id}) is correct."
            )
        else:
            raise Exception(
                f"Failed to get workspace details: HTTP {response.status_code} - {response.text}"
            )
    
    def get_workspace_capacity(self, workspace_id: str) -> dict:
        """
        Checks if workspace has Premium/Embedded capacity assigned.
        
        Args:
            workspace_id: The Power BI workspace (group) ID
            
        Returns:
            Dictionary with capacity information
        """
        workspace_info = self.get_workspace_info(workspace_id)
        
        capacity_id = workspace_info.get("capacityId")
        is_on_dedicated_capacity = workspace_info.get("isOnDedicatedCapacity", False)
        
        return {
            "capacityId": capacity_id,
            "isOnDedicatedCapacity": is_on_dedicated_capacity,
            "workspaceName": workspace_info.get("name"),
            "workspaceType": workspace_info.get("type", "Unknown")
        }
    
    def run_diagnostics(self) -> dict:
        """
        Runs comprehensive diagnostics to validate Power BI prerequisites.
        
        Returns:
            Dictionary containing diagnostic results for each check:
            - overall_status: "healthy", "degraded", or "unhealthy"
            - checks: List of individual check results
            - summary: Human-readable summary
        """
        checks = []
        overall_healthy = True
        has_warnings = False
        
        # Check 1: Configuration completeness
        config_check = self._check_configuration()
        checks.append(config_check)
        if config_check["status"] == "fail":
            overall_healthy = False
            # Can't proceed without config
            return self._build_diagnostic_result(checks, overall_healthy, has_warnings)
        
        # Check 2: Azure AD Authentication
        auth_check = self._check_authentication()
        checks.append(auth_check)
        if auth_check["status"] == "fail":
            overall_healthy = False
            # Can't proceed without auth
            return self._build_diagnostic_result(checks, overall_healthy, has_warnings)
        
        # Check 3: Workspace Access
        workspace_check = self._check_workspace_access()
        checks.append(workspace_check)
        if workspace_check["status"] == "fail":
            overall_healthy = False
        elif workspace_check["status"] == "warning":
            has_warnings = True
        
        # Check 4: Capacity/License
        capacity_check = self._check_capacity()
        checks.append(capacity_check)
        if capacity_check["status"] == "fail":
            overall_healthy = False
        elif capacity_check["status"] == "warning":
            has_warnings = True
        
        # Check 5: Report Access
        report_check = self._check_report_access()
        checks.append(report_check)
        if report_check["status"] == "fail":
            overall_healthy = False
        elif report_check["status"] == "warning":
            has_warnings = True
        
        # Check 6: Embed Token Generation
        if overall_healthy:  # Only try if previous checks passed
            embed_check = self._check_embed_token_generation()
            checks.append(embed_check)
            if embed_check["status"] == "fail":
                overall_healthy = False
            elif embed_check["status"] == "warning":
                has_warnings = True
        
        return self._build_diagnostic_result(checks, overall_healthy, has_warnings)
    
    @staticmethod
    def _mask_id(value: str, visible_chars: int = 4) -> str:
        """Mask sensitive ID values, showing only first few characters."""
        if not value:
            return "(not set)"
        if len(value) <= visible_chars:
            return "*" * len(value)
        return f"{value[:visible_chars]}{'*' * 8}"
    
    def _check_configuration(self) -> dict:
        """Check if all required environment variables are configured."""
        is_valid, missing = Config.validate()
        
        if is_valid:
            return {
                "name": "configuration",
                "displayName": "Environment Configuration",
                "status": "pass",
                "message": "All required environment variables are configured",
                "details": {
                    "allRequiredVariablesSet": True,
                    "datasetIdConfigured": bool(Config.DATASET_ID)
                }
            }
        else:
            return {
                "name": "configuration",
                "displayName": "Environment Configuration",
                "status": "fail",
                "message": f"Missing required environment variables",
                "details": {
                    "missingVariables": missing
                },
                "hint": "Copy .env.example to .env and fill in your Azure AD and Power BI values"
            }
    
    def _check_authentication(self) -> dict:
        """Check Azure AD authentication with service principal."""
        try:
            token, expiry = self.get_access_token()
            import datetime
            # Calculate time until expiry without exposing exact timestamp
            seconds_until_expiry = int(expiry - time.time())
            minutes_until_expiry = seconds_until_expiry // 60
            
            return {
                "name": "authentication",
                "displayName": "Azure AD Authentication",
                "status": "pass",
                "message": "Successfully authenticated with Azure AD",
                "details": {
                    "tokenAcquired": True,
                    "tokenValidFor": f"{minutes_until_expiry} minutes"
                }
            }
        except Exception as e:
            error_msg = str(e)
            # Sanitize error message to avoid leaking sensitive details
            sanitized_error = self._sanitize_error_message(error_msg)
            hint = "Check CLIENT_ID, CLIENT_SECRET, and TENANT_ID values"
            
            if "invalid_client" in error_msg.lower():
                hint = "The CLIENT_SECRET may be expired or incorrect"
            elif "tenant" in error_msg.lower():
                hint = "The TENANT_ID may be incorrect or the tenant doesn't exist"
            elif "application" in error_msg.lower():
                hint = "The CLIENT_ID may be incorrect or the app registration doesn't exist"
            
            return {
                "name": "authentication",
                "displayName": "Azure AD Authentication",
                "status": "fail",
                "message": "Failed to authenticate with Azure AD",
                "details": {
                    "errorType": sanitized_error
                },
                "hint": hint
            }
    
    def _sanitize_error_message(self, error_msg: str) -> str:
        """Sanitize error messages to remove sensitive information."""
        import re
        # Remove GUIDs
        sanitized = re.sub(
            r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}',
            '[REDACTED-ID]',
            error_msg
        )
        # Remove potential tokens or secrets (long alphanumeric strings)
        sanitized = re.sub(
            r'[A-Za-z0-9_-]{40,}',
            '[REDACTED]',
            sanitized
        )
        # Categorize known error types
        if "unauthorized" in error_msg.lower():
            return "Authentication unauthorized"
        elif "forbidden" in error_msg.lower():
            return "Access forbidden"
        elif "not found" in error_msg.lower():
            return "Resource not found"
        elif "invalid_client" in error_msg.lower():
            return "Invalid client credentials"
        elif "invalid_grant" in error_msg.lower():
            return "Invalid grant"
        return sanitized[:200] if len(sanitized) > 200 else sanitized
    
    def _check_workspace_access(self) -> dict:
        """Check access to the Power BI workspace."""
        try:
            workspace_info = self.get_workspace_info(Config.WORKSPACE_ID)
            
            return {
                "name": "workspace_access",
                "displayName": "Workspace Access",
                "status": "pass",
                "message": "Successfully accessed workspace",
                "details": {
                    "accessible": True,
                    "workspaceType": workspace_info.get("type", "Unknown")
                }
            }
        except Exception as e:
            error_msg = str(e)
            sanitized_error = self._sanitize_error_message(error_msg)
            hint = "Ensure the Service Principal is added to the workspace as Admin or Member"
            
            if "not found" in error_msg.lower():
                hint = "The WORKSPACE_ID may be incorrect. Verify it in Power BI service URL."
            elif "forbidden" in error_msg.lower():
                hint = "Add the Service Principal to the workspace via 'Manage access' in Power BI"
            
            return {
                "name": "workspace_access",
                "displayName": "Workspace Access",
                "status": "fail",
                "message": "Cannot access Power BI workspace",
                "details": {
                    "errorType": sanitized_error
                },
                "hint": hint
            }
    
    def _check_capacity(self) -> dict:
        """Check if workspace has dedicated capacity (required for embedding)."""
        try:
            capacity_info = self.get_workspace_capacity(Config.WORKSPACE_ID)
            
            if capacity_info["isOnDedicatedCapacity"]:
                return {
                    "name": "capacity",
                    "displayName": "Dedicated Capacity",
                    "status": "pass",
                    "message": "Workspace has dedicated capacity assigned",
                    "details": {
                        "isOnDedicatedCapacity": True,
                        "capacityAssigned": True
                    }
                }
            else:
                return {
                    "name": "capacity",
                    "displayName": "Dedicated Capacity",
                    "status": "warning",
                    "message": "Workspace is not on dedicated capacity",
                    "details": {
                        "isOnDedicatedCapacity": False
                    },
                    "hint": "Embedding requires Power BI Premium, Embedded, or Fabric capacity. Assign capacity in the Power BI Admin Portal."
                }
        except Exception as e:
            sanitized_error = self._sanitize_error_message(str(e))
            return {
                "name": "capacity",
                "displayName": "Dedicated Capacity",
                "status": "warning",
                "message": "Could not verify capacity status",
                "details": {
                    "errorType": sanitized_error
                },
                "hint": "Ensure workspace has Premium/Embedded capacity for production embedding"
            }
    
    def _check_report_access(self) -> dict:
        """Check access to the specific report."""
        try:
            report_info = self.get_report_embed_url(Config.WORKSPACE_ID, Config.REPORT_ID)
            
            return {
                "name": "report_access",
                "displayName": "Report Access",
                "status": "pass",
                "message": "Successfully accessed report",
                "details": {
                    "accessible": True,
                    "hasDataset": bool(report_info.get("datasetId")),
                    "embedUrlAvailable": bool(report_info.get("embedUrl"))
                }
            }
        except Exception as e:
            error_msg = str(e)
            sanitized_error = self._sanitize_error_message(error_msg)
            hint = "Verify REPORT_ID is correct and exists in the workspace"
            
            if "not found" in error_msg.lower():
                hint = "The REPORT_ID may be incorrect. Copy it from the report URL in Power BI service."
            elif "forbidden" in error_msg.lower():
                hint = "The Service Principal may not have access to this specific report"
            
            return {
                "name": "report_access",
                "displayName": "Report Access",
                "status": "fail",
                "message": "Cannot access Power BI report",
                "details": {
                    "errorType": sanitized_error
                },
                "hint": hint
            }
    
    def _check_embed_token_generation(self) -> dict:
        """Check if embed token can be generated."""
        try:
            # Get report details first to get dataset ID
            report_info = self.get_report_embed_url(Config.WORKSPACE_ID, Config.REPORT_ID)
            dataset_id = report_info.get("datasetId") or Config.DATASET_ID
            
            # Try to generate embed token
            embed_token = self.generate_embed_token(
                workspace_id=Config.WORKSPACE_ID,
                report_id=Config.REPORT_ID,
                dataset_id=dataset_id
            )
            
            return {
                "name": "embed_token",
                "displayName": "Embed Token Generation",
                "status": "pass",
                "message": "Successfully generated embed token",
                "details": {
                    "tokenGenerated": True,
                    "tokenValid": bool(embed_token.get("token"))
                }
            }
        except Exception as e:
            error_msg = str(e)
            sanitized_error = self._sanitize_error_message(error_msg)
            hint = "Ensure workspace has proper capacity and Service Principal has embed permissions"
            
            if "forbidden" in error_msg.lower() or "capacity" in error_msg.lower():
                hint = "Embedding requires dedicated capacity (Premium, Embedded, or Fabric). Check capacity assignment."
            
            return {
                "name": "embed_token",
                "displayName": "Embed Token Generation",
                "status": "fail",
                "message": "Cannot generate embed token",
                "details": {
                    "errorType": sanitized_error
                },
                "hint": hint
            }
    
    def _build_diagnostic_result(self, checks: list, overall_healthy: bool, has_warnings: bool) -> dict:
        """Build the final diagnostic result dictionary."""
        passed = sum(1 for c in checks if c["status"] == "pass")
        failed = sum(1 for c in checks if c["status"] == "fail")
        warnings = sum(1 for c in checks if c["status"] == "warning")
        
        if overall_healthy and not has_warnings:
            status = "healthy"
            summary = "All diagnostic checks passed. Power BI embedding is ready."
        elif overall_healthy and has_warnings:
            status = "degraded"
            summary = f"Embedding may work but {warnings} warning(s) detected. Review warnings for production readiness."
        else:
            status = "unhealthy"
            summary = f"{failed} check(s) failed. Review the failed checks and their hints to resolve issues."
        
        return {
            "overallStatus": status,
            "summary": summary,
            "statistics": {
                "total": len(checks),
                "passed": passed,
                "failed": failed,
                "warnings": warnings
            },
            "checks": checks
        }


# Create a singleton instance for use throughout the application
powerbi_service = PowerBIService()
