/**
 * Power BI Embedded Frontend Application
 * 
 * This module handles:
 * - Fetching embed configuration from the backend
 * - Embedding the Power BI report using powerbi-client
 * - Applying filters based on dropdown selection
 * - Status updates and error handling
 */

// =============================================================================
// Global Variables
// =============================================================================

/** @type {powerbi.Report|null} - Reference to the embedded Power BI report */
let report = null;

/** @type {Object} - Filter configuration from the backend */
let filterConfig = {
    tableName: "<TABLE_NAME>",
    columnName: "<COLUMN_NAME>"
};

/** @type {boolean} - Flag to track if the report is fully loaded */
let isReportLoaded = false;

// =============================================================================
// DOM Elements
// =============================================================================

const filterSelect = document.getElementById("filterSelect");
const reportContainer = document.getElementById("reportContainer");
const statusIndicator = document.getElementById("statusIndicator");
const statusText = document.getElementById("statusText");

// =============================================================================
// Status Management
// =============================================================================

/**
 * Updates the status indicator with the given state and message
 * @param {string} state - One of: "loading", "ready", "error"
 * @param {string} message - Status message to display
 */
function updateStatus(state, message) {
    statusIndicator.className = `status-indicator ${state}`;
    statusText.textContent = message;
}

// =============================================================================
// API Functions
// =============================================================================

/**
 * Fetches the embed configuration from the backend API
 * @returns {Promise<Object>} Embed configuration object
 * @throws {Object} Error object with message and optional data
 */
async function fetchEmbedConfig() {
    const response = await fetch("/api/embed-config");
    const data = await response.json().catch(() => ({}));
    
    if (!response.ok) {
        const error = new Error(data.details || data.error || `HTTP ${response.status}`);
        error.data = data;  // Attach full error data for display
        throw error;
    }
    
    return data;
}

/**
 * Fetches filter values from the backend API
 * @returns {Promise<Object>} Object containing values array and filterConfig
 */
async function fetchFilterValues() {
    const response = await fetch("/api/filter-values");
    
    if (!response.ok) {
        console.warn("Failed to fetch filter values, using defaults");
        return {
            values: ["All", "Account", "Customer", "Region", "Product"],
            filterConfig: filterConfig
        };
    }
    
    return response.json();
}

// =============================================================================
// Dropdown Management
// =============================================================================

/**
 * Populates the filter dropdown with values from the backend
 * @param {string[]} values - Array of filter values
 */
function populateFilterDropdown(values) {
    filterSelect.innerHTML = "";
    
    values.forEach(value => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        filterSelect.appendChild(option);
    });
    
    // Disable until report is loaded
    filterSelect.disabled = true;
}

// =============================================================================
// Power BI Embedding
// =============================================================================

/**
 * Embeds the Power BI report into the container
 * @param {Object} embedConfig - Configuration from the backend API
 */
function embedReport(embedConfig) {
    // Clear loading state from container
    reportContainer.classList.remove("loading");
    reportContainer.innerHTML = "";
    
    // Get the Power BI embed instance
    const powerbiClient = window.powerbi;
    
    // Configuration for embedding the report
    const config = {
        type: "report",
        tokenType: powerbiClient.models.TokenType.Embed,
        accessToken: embedConfig.embedToken,
        embedUrl: embedConfig.embedUrl,
        id: embedConfig.reportId,
        permissions: powerbiClient.models.Permissions.Read,
        settings: {
            // Panes configuration - hide filter pane since we use our own dropdown
            panes: {
                filters: {
                    visible: false,  // Hide the built-in filter pane
                    expanded: false
                },
                pageNavigation: {
                    visible: true
                }
            },
            // Background setting
            background: powerbiClient.models.BackgroundType.Transparent,
            // Layout settings for responsive behavior
            layoutType: powerbiClient.models.LayoutType.Custom,
            customLayout: {
                displayOption: powerbiClient.models.DisplayOption.FitToPage
            }
        }
    };
    
    // Embed the report
    report = powerbiClient.embed(reportContainer, config);
    
    // Set up event handlers
    setupReportEventHandlers();
}

/**
 * Sets up event handlers for the embedded report
 */
function setupReportEventHandlers() {
    // Handle report loaded event
    // Note: "loaded" fires when the report structure is loaded (before rendering)
    report.on("loaded", function() {
        console.log("Report loaded - structure ready");
    });
    
    // Handle report rendered event
    // Note: "rendered" fires when the report is fully rendered and visible
    report.on("rendered", function() {
        console.log("Report rendered - fully ready");
        isReportLoaded = true;
        
        // Enable the filter dropdown now that report is ready
        filterSelect.disabled = false;
        updateStatus("ready", "Report ready - select a filter");
    });
    
    // Handle errors
    report.on("error", function(event) {
        console.error("Report error:", event.detail);
        updateStatus("error", "Report error occurred");
        
        // Show error in container
        displayError("Report Error", event.detail.message || "An error occurred while loading the report");
    });
    
    // Handle page changes (optional, for debugging)
    report.on("pageChanged", function(event) {
        console.log("Page changed to:", event.detail.newPage.displayName);
    });
}

/**
 * Displays an error message in the report container
 * @param {string} title - Error title
 * @param {string} message - Error message details
 * @param {Object} errorData - Optional error data object from API
 */
function displayError(title, message, errorData = null) {
    reportContainer.classList.remove("loading");
    
    // Check if this is a configuration error
    if (errorData && errorData.missingVariables) {
        const missingVars = errorData.missingVariables.join(", ");
        reportContainer.innerHTML = `
            <div class="error-message" style="background: #fff3cd; border-color: #ffc107; color: #856404;">
                <h3>⚙️ Configuration Required</h3>
                <p style="margin-top: 10px;">The application is running, but Power BI credentials are not configured.</p>
                <p style="margin-top: 15px;">
                    <strong>Missing environment variables:</strong>
                </p>
                <code style="display: block; background: rgba(0,0,0,0.1); padding: 10px; margin: 10px 0; border-radius: 4px;">
                    ${missingVars}
                </code>
                <p style="margin-top: 15px;">
                    <strong>To configure:</strong>
                </p>
                <ol style="margin-top: 10px; margin-left: 20px;">
                    <li>Copy <code>.env.example</code> to <code>.env</code></li>
                    <li>Fill in your Azure AD and Power BI values</li>
                    <li>Restart the application</li>
                </ol>
                <p style="margin-top: 15px;">
                    See <a href="https://docs.microsoft.com/en-us/power-bi/developer/embedded/register-app" target="_blank">Power BI Embedded documentation</a> for setup instructions.
                </p>
            </div>
        `;
        return;
    }
    
    // Standard error display
    reportContainer.innerHTML = `
        <div class="error-message">
            <h3>${title}</h3>
            <p>${message}</p>
            ${errorData && errorData.hint ? `<p style="margin-top: 10px;"><strong>Hint:</strong> ${errorData.hint}</p>` : ""}
            <p style="margin-top: 15px;">
                <strong>Troubleshooting steps:</strong>
            </p>
            <ul style="margin-top: 10px; margin-left: 20px;">
                <li>Check that all environment variables are correctly set</li>
                <li>Verify the Service Principal has access to the workspace</li>
                <li>Ensure the workspace has Pro or Premium capacity</li>
                <li>Check the browser console for more details</li>
            </ul>
        </div>
    `;
}

// =============================================================================
// Filter Application
// =============================================================================

/**
 * Creates a Basic Filter object for Power BI
 * @param {string} tableName - Name of the table in the Power BI model
 * @param {string} columnName - Name of the column to filter
 * @param {string[]} values - Array of values to filter by
 * @returns {Object} Power BI BasicFilter object
 */
function createBasicFilter(tableName, columnName, values) {
    const powerbiClient = window.powerbi;
    
    return {
        $schema: "http://powerbi.com/product/schema#basic",
        target: {
            table: tableName,
            column: columnName
        },
        operator: "In",
        values: values,
        filterType: powerbiClient.models.FilterType.Basic
    };
}

/**
 * Applies a filter to the embedded report
 * @param {string} selectedValue - The value selected from the dropdown
 */
async function applyFilter(selectedValue) {
    if (!report || !isReportLoaded) {
        console.warn("Report not ready, cannot apply filter");
        return;
    }
    
    try {
        if (selectedValue === "All" || selectedValue === "") {
            // Clear all report-level filters
            await report.removeFilters();
            updateStatus("ready", "Filters cleared");
            console.log("Filters removed");
        } else {
            // Create and apply a basic filter
            const filter = createBasicFilter(
                filterConfig.tableName,
                filterConfig.columnName,
                [selectedValue]
            );
            
            // Apply filter at the report level
            // This affects all pages in the report
            await report.setFilters([filter]);
            updateStatus("ready", `Filtered by: ${selectedValue}`);
            console.log("Filter applied:", filter);
        }
    } catch (error) {
        console.error("Error applying filter:", error);
        updateStatus("error", "Filter error - check console");
        
        // Common filter errors and their causes
        if (error.message && error.message.includes("table")) {
            console.error(
                "HINT: The table name might be incorrect. " +
                "Update <TABLE_NAME> in /api/filter-values or filterConfig."
            );
        }
        if (error.message && error.message.includes("column")) {
            console.error(
                "HINT: The column name might be incorrect. " +
                "Update <COLUMN_NAME> in /api/filter-values or filterConfig."
            );
        }
    }
}

// =============================================================================
// Event Listeners
// =============================================================================

/**
 * Handle dropdown change events
 */
filterSelect.addEventListener("change", function(event) {
    const selectedValue = event.target.value;
    console.log("Filter selection changed:", selectedValue);
    
    // Update status to show we're applying the filter
    updateStatus("loading", "Applying filter...");
    
    // Apply the filter
    applyFilter(selectedValue);
});

// =============================================================================
// Initialization
// =============================================================================

/**
 * Initialize the application
 * - Fetch filter values and populate dropdown
 * - Fetch embed config and embed the report
 */
async function initialize() {
    updateStatus("loading", "Initializing...");
    
    try {
        // Fetch filter values and embed config in parallel
        const [filterData, embedConfig] = await Promise.all([
            fetchFilterValues(),
            fetchEmbedConfig()
        ]);
        
        // Update filter configuration from backend
        if (filterData.filterConfig) {
            filterConfig = filterData.filterConfig;
        }
        
        // Populate the dropdown
        populateFilterDropdown(filterData.values);
        
        // Update status
        updateStatus("loading", "Embedding report...");
        
        // Embed the Power BI report
        embedReport(embedConfig);
        
    } catch (error) {
        console.error("Initialization error:", error);
        updateStatus("error", "Failed to initialize");
        displayError("Initialization Error", error.message, error.data || null);
        
        // Re-enable dropdown with error state
        filterSelect.disabled = true;
        filterSelect.innerHTML = '<option value="">Error loading values</option>';
    }
}

// =============================================================================
// Start Application
// =============================================================================

// Wait for DOM to be fully loaded before initializing
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize);
} else {
    // DOM already loaded
    initialize();
}
