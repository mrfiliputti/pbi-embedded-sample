"""
Power BI Embedded Flask Application.
Main application entry point with API endpoints for embed configuration and filter values.
"""

from flask import Flask, render_template, jsonify
from config import Config
from services.powerbi_service import powerbi_service

# Initialize Flask application
app = Flask(__name__)
app.config["SECRET_KEY"] = Config.SECRET_KEY
app.config["DEBUG"] = Config.DEBUG


# =============================================================================
# API Endpoints
# =============================================================================

@app.route("/api/embed-config", methods=["GET"])
def get_embed_config():
    """
    Returns the embed configuration needed to embed the Power BI report.
    
    Response JSON:
        {
            "embedToken": "token string",
            "embedUrl": "https://app.powerbi.com/...",
            "reportId": "guid",
            "datasetId": "guid",
            "tokenExpiry": "ISO datetime string"
        }
        
    Error Response:
        {
            "error": "Error message",
            "details": "Additional details if available"
        }
    """
    # Check if configuration is complete before attempting to get embed config
    if not Config.is_configured():
        missing_vars = Config.get_missing_vars()
        return jsonify({
            "error": "Configuration incomplete",
            "details": f"Missing environment variables: {', '.join(missing_vars)}",
            "hint": "Copy .env.example to .env and fill in your Azure AD and Power BI values",
            "missingVariables": missing_vars
        }), 503
    
    try:
        embed_config = powerbi_service.get_embed_config()
        return jsonify(embed_config), 200
    
    except Exception as e:
        error_message = str(e)
        
        # Provide helpful error messages based on common issues
        if "unauthorized" in error_message.lower():
            return jsonify({
                "error": "Authentication failed",
                "details": error_message,
                "hint": "Check CLIENT_ID, CLIENT_SECRET, and TENANT_ID values"
            }), 401
        
        elif "forbidden" in error_message.lower():
            return jsonify({
                "error": "Access denied",
                "details": error_message,
                "hint": "Ensure Service Principal is added to the workspace with proper permissions"
            }), 403
        
        elif "not found" in error_message.lower():
            return jsonify({
                "error": "Resource not found",
                "details": error_message,
                "hint": "Verify WORKSPACE_ID and REPORT_ID are correct"
            }), 404
        
        else:
            return jsonify({
                "error": "Failed to get embed configuration",
                "details": error_message
            }), 500


@app.route("/api/filter-values", methods=["GET"])
def get_filter_values():
    """
    Returns the list of values for the dropdown filter.
    
    In a production scenario, these values could come from:
    - A database query
    - Power BI REST API (querying the dataset)
    - An external service
    
    For this demo, we return hardcoded values representing common filter options.
    
    Response JSON:
        {
            "values": ["All", "Option1", "Option2", ...],
            "filterConfig": {
                "tableName": "<TABLE_NAME>",
                "columnName": "<COLUMN_NAME>"
            }
        }
    """
    try:
        # Product filter values used by the frontend dropdown.
        filter_values = [
            "All",           # Special value to clear filters
            "Laptops",
            "Monitors",
            "Keyboards",
            "Mice",
            "Headsets",
            "Webcams"
        ]
        
        # Filter configuration for report-level filtering.
        # Update tableName if your model uses a different table that contains Product.
        filter_config = {
            "tableName": Config.FILTER_TABLE_NAME,
            "tableCandidates": Config.FILTER_TABLE_CANDIDATES,
            "columnName": Config.FILTER_COLUMN_NAME,
        }
        
        return jsonify({
            "values": filter_values,
            "filterConfig": filter_config
        }), 200
    
    except Exception as e:
        return jsonify({
            "error": "Failed to get filter values",
            "details": str(e)
        }), 500


@app.route("/api/health", methods=["GET"])
def health_check():
    """
    Health check endpoint to verify the application is running.
    Also validates that Power BI service can acquire tokens.
    """
    # Check configuration status
    if not Config.is_configured():
        missing_vars = Config.get_missing_vars()
        return jsonify({
            "status": "unconfigured",
            "message": f"Missing environment variables: {', '.join(missing_vars)}",
            "configured": False,
            "missingVariables": missing_vars
        }), 200  # Return 200 so frontend knows app is running
    
    try:
        # Try to acquire a token to verify connectivity
        powerbi_service.get_access_token()
        
        return jsonify({
            "status": "healthy",
            "message": "Application is running and can authenticate with Azure AD",
            "configured": True
        }), 200
    
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "message": str(e),
            "configured": True
        }), 503


@app.route("/api/diagnose", methods=["GET"])
def diagnose():
    """
    Comprehensive diagnostic endpoint for validating Power BI prerequisites.
    
    Performs the following checks:
    1. Configuration - Validates all required environment variables
    2. Authentication - Tests Azure AD authentication with service principal
    3. Workspace Access - Verifies access to the Power BI workspace
    4. Capacity - Checks if workspace has dedicated capacity (Premium/Embedded/Fabric)
    5. Report Access - Validates access to the specific report
    6. Embed Token - Tests embed token generation capability
    
    Response JSON:
        {
            "overallStatus": "healthy" | "degraded" | "unhealthy",
            "summary": "Human-readable summary",
            "statistics": {
                "total": 6,
                "passed": 6,
                "failed": 0,
                "warnings": 0
            },
            "checks": [
                {
                    "name": "check_name",
                    "displayName": "Human Readable Name",
                    "status": "pass" | "fail" | "warning",
                    "message": "Description",
                    "details": { ... },
                    "hint": "How to fix (if applicable)"
                },
                ...
            ]
        }
    
    Status Codes:
        200 - Diagnostics completed (check overallStatus for health)
        500 - Unexpected error during diagnostics
    """
    try:
        diagnostics = powerbi_service.run_diagnostics()
        return jsonify(diagnostics), 200
    
    except Exception as e:
        return jsonify({
            "overallStatus": "error",
            "summary": "An unexpected error occurred during diagnostics",
            "error": str(e),
            "checks": []
        }), 500


# =============================================================================
# Frontend Routes
# =============================================================================

@app.route("/")
def index():
    """
    Serves the main HTML page with the embedded Power BI report.
    """
    return render_template("index.html")


# =============================================================================
# Error Handlers
# =============================================================================

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors."""
    return jsonify({
        "error": "Not Found",
        "details": "The requested resource was not found"
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({
        "error": "Internal Server Error",
        "details": "An unexpected error occurred"
    }), 500


# =============================================================================
# Application Entry Point
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Power BI Embedded Demo Application")
    print("=" * 60)
    print(f"Report ID: {Config.REPORT_ID}")
    print(f"Workspace ID: {Config.WORKSPACE_ID}")
    print("=" * 60)
    print("\nStarting Flask server...")
    print("Open http://localhost:5000 in your browser\n")
    
    app.run(host="0.0.0.0", port=5000, debug=Config.DEBUG)
