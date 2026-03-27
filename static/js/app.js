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
    tableName: "Sales",
    columnName: "Product"
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
    const data = await response.json().catch(() => ({}));
    
    if (!response.ok) {
        const error = new Error(data.details || data.error || `HTTP ${response.status}`);
        error.data = data;
        throw error;
    }
    
    return data;
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
    
    // Resolve Power BI service and models from global objects exposed by the CDN bundle.
    const powerbiService = window.powerbi;
    const powerbiModels = (window["powerbi-client"] && window["powerbi-client"].models) ||
        (powerbiService && powerbiService.models);

    if (!powerbiService || !powerbiModels) {
        throw new Error(
            "Power BI client library is not fully loaded. Verify the powerbi-client script is available."
        );
    }
    
    // Configuration for embedding the report
    const config = {
        type: "report",
        tokenType: powerbiModels.TokenType.Embed,
        accessToken: embedConfig.embedToken,
        embedUrl: embedConfig.embedUrl,
        id: embedConfig.reportId,
        permissions: powerbiModels.Permissions.Read,
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
            background: powerbiModels.BackgroundType.Transparent,
            // Layout settings for responsive behavior
            layoutType: powerbiModels.LayoutType.Custom,
            customLayout: {
                displayOption: powerbiModels.DisplayOption.FitToPage
            }
        }
    };
    
    // Embed the report
    report = powerbiService.embed(reportContainer, config);
    
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
    const powerbiService = window.powerbi;
    const powerbiModels = (window["powerbi-client"] && window["powerbi-client"].models) ||
        (powerbiService && powerbiService.models);

    if (!powerbiModels) {
        throw new Error("Power BI models are unavailable. Cannot create filters.");
    }
    
    return {
        $schema: "http://powerbi.com/product/schema#basic",
        target: {
            table: tableName,
            column: columnName
        },
        operator: "In",
        values: values,
        filterType: powerbiModels.FilterType.Basic
    };
}

/**
 * Creates an Advanced Filter object using text containment.
 * @param {string} tableName - Name of the table in the Power BI model
 * @param {string} columnName - Name of the column to filter
 * @param {string} value - Value to match with Contains
 * @returns {Object} Power BI AdvancedFilter object
 */
function createContainsFilter(tableName, columnName, value) {
    const powerbiService = window.powerbi;
    const powerbiModels = (window["powerbi-client"] && window["powerbi-client"].models) ||
        (powerbiService && powerbiService.models);

    if (!powerbiModels) {
        throw new Error("Power BI models are unavailable. Cannot create filters.");
    }

    return {
        $schema: "http://powerbi.com/product/schema#advanced",
        target: {
            table: tableName,
            column: columnName
        },
        logicalOperator: "And",
        conditions: [
            {
                operator: "Contains",
                value: value
            }
        ],
        filterType: powerbiModels.FilterType.Advanced
    };
}

/**
 * Returns unique candidate table names for filter target resolution.
 * @returns {string[]}
 */
function getFilterTableCandidates() {
    const configuredCandidates = Array.isArray(filterConfig.tableCandidates)
        ? filterConfig.tableCandidates
        : [];

    const combined = [filterConfig.tableName, ...configuredCandidates]
        .map(value => (value || "").trim())
        .filter(Boolean);

    return [...new Set(combined)];
}

/**
 * Returns table and matrix visuals from the active page.
 * @returns {Promise<Array>} List of Power BI visuals
 */
async function getTabularVisuals() {
    const page = await report.getActivePage();
    const visuals = await page.getVisuals();
    return visuals.filter(visual => visual.type === "table" || visual.type === "matrix");
}

/**
 * Applies or clears filters on tabular visuals and returns update statistics.
 * @param {Object[]|null} filters - Filters to apply, or null/[] to clear
 * @returns {Promise<{total: number, succeeded: number}>}
 */
async function applyFiltersToTabularVisuals(filters) {
    const powerbiService = window.powerbi;
    const powerbiModels = (window["powerbi-client"] && window["powerbi-client"].models) ||
        (powerbiService && powerbiService.models);

    if (!powerbiModels) {
        throw new Error("Power BI models are unavailable. Cannot update visual filters.");
    }

    const tabularVisuals = await getTabularVisuals();
    const nextFilters = Array.isArray(filters) ? filters : [];
    const operation = powerbiModels.FiltersOperations.Replace;
    let succeeded = 0;

    for (const visual of tabularVisuals) {
        try {
            if (typeof visual.updateFilters === "function") {
                await visual.updateFilters(operation, nextFilters);
            } else if (nextFilters.length) {
                await visual.setFilters(nextFilters);
            } else {
                await visual.removeFilters();
            }
            succeeded += 1;
        } catch (visualError) {
            console.warn(`Unable to update filters on visual ${visual.name} (${visual.type})`, visualError);
        }
    }

    return { total: tabularVisuals.length, succeeded };
}

/**
 * Applies or clears filters on the active page.
 * @param {Object[]|null} filters - Filter array to apply, or null to clear
 */
async function applyFiltersToActivePage(filters) {
    const powerbiService = window.powerbi;
    const powerbiModels = (window["powerbi-client"] && window["powerbi-client"].models) ||
        (powerbiService && powerbiService.models);

    if (!powerbiModels) {
        throw new Error("Power BI models are unavailable. Cannot update page filters.");
    }

    const page = await report.getActivePage();
    const nextFilters = Array.isArray(filters) ? filters : [];

    if (typeof page.updateFilters === "function") {
        await page.updateFilters(powerbiModels.FiltersOperations.Replace, nextFilters);
    } else if (nextFilters.length) {
        await page.setFilters(nextFilters);
    } else {
        await page.removeFilters();
    }
}

/**
 * Clears filter scopes in report, active page, and tabular visuals.
 */
async function clearAllFilterScopes() {
    const powerbiService = window.powerbi;
    const powerbiModels = (window["powerbi-client"] && window["powerbi-client"].models) ||
        (powerbiService && powerbiService.models);

    if (!powerbiModels) {
        throw new Error("Power BI models are unavailable. Cannot clear filters.");
    }

    if (typeof report.removeFilters === "function") {
        await report.removeFilters();
    } else if (typeof report.updateFilters === "function") {
        await report.updateFilters(powerbiModels.FiltersOperations.Replace, []);
    }

    await applyFiltersToActivePage([]);
    await applyFiltersToTabularVisuals([]);
}

/**
 * Applies selected value using candidate table targets until one works.
 * @param {string} selectedValue
 * @returns {Promise<Object[]>}
 */
async function applyFilterWithFallbackTargets(selectedValue) {
    const powerbiService = window.powerbi;
    const powerbiModels = (window["powerbi-client"] && window["powerbi-client"].models) ||
        (powerbiService && powerbiService.models);

    if (!powerbiModels) {
        throw new Error("Power BI models are unavailable. Cannot apply filters.");
    }

    const candidates = getFilterTableCandidates();
    if (!candidates.length) {
        throw new Error("No tableName candidate available for filtering.");
    }

    const failures = [];

    for (const tableName of candidates) {
        const candidateFilters = [
            {
                label: "basic-in",
                filter: createBasicFilter(tableName, filterConfig.columnName, [selectedValue])
            },
            {
                label: "advanced-contains",
                filter: createContainsFilter(tableName, filterConfig.columnName, selectedValue)
            }
        ];

        for (const attempt of candidateFilters) {
            try {
                await clearAllFilterScopes();

                if (typeof report.updateFilters === "function") {
                    await report.updateFilters(powerbiModels.FiltersOperations.Replace, [attempt.filter]);
                } else {
                    await report.setFilters([attempt.filter]);
                }

                await applyFiltersToActivePage([attempt.filter]);
                const visualResult = await applyFiltersToTabularVisuals([attempt.filter]);

                if (visualResult.total > 0 && visualResult.succeeded === 0) {
                    throw new Error("Filter target rejected by all table/matrix visuals");
                }

                console.log("Filter target applied successfully:", {
                    tableName,
                    strategy: attempt.label
                });
                return [attempt.filter];
            } catch (error) {
                failures.push({
                    tableName,
                    strategy: attempt.label,
                    error: error.message || String(error)
                });
            }
        }
    }

    throw new Error(
        `Unable to apply filter to any candidate table. Attempts: ${JSON.stringify(failures)}`
    );
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
        const normalizedValue = (selectedValue || "").trim().toLowerCase();
        const isAllSelection = normalizedValue === "all" || normalizedValue === "";

        if (isAllSelection) {
            await clearAllFilterScopes();
            updateStatus("ready", "Filters cleared");
            console.log("Filters removed");
        } else {
            const appliedFilters = await applyFilterWithFallbackTargets(selectedValue);
            updateStatus("ready", `Filtered by: ${selectedValue}`);
            console.log("Filters applied:", appliedFilters);
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
