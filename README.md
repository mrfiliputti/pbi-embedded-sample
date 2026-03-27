# Power BI Embedded Demo Application

A complete Flask application demonstrating **Power BI Embedded** using the **"App Owns Data"** (Embed for your customers) pattern. This app allows embedding Power BI reports in a web page and applying filters dynamically via a dropdown.

## Features

- 🔐 **Service Principal Authentication** - Secure OAuth 2.0 client credentials flow
- 📊 **Power BI Report Embedding** - Using the official `powerbi-client` JavaScript library
- 🔍 **Dynamic Filtering** - Apply filters via dropdown without page reload
- ⚡ **Token Caching** - Optimized AAD token management
- 🛡️ **Error Handling** - Meaningful error messages with troubleshooting hints

## Project Structure

```
PBI-Embedded/
├── app.py                      # Flask application (main entry point)
├── config.py                   # Configuration and environment validation
├── requirements.txt            # Python dependencies
├── .env.example               # Sample environment variables
├── README.md                  # This file
├── services/
│   ├── __init__.py
│   └── powerbi_service.py     # Power BI API integration
├── templates/
│   └── index.html             # Main HTML page
└── static/
    └── js/
        └── app.js             # Frontend JavaScript
```

## Prerequisites

Before running this application, you need:

1. **Python 3.8+** installed
2. **Power BI Pro or Premium Per User (PPU)** license
3. **Power BI Workspace** with a published report
4. **Azure AD App Registration** with Service Principal configured
5. **Power BI Tenant Settings** configured to allow Service Principals

---

## Creating and Publishing a Power BI Report for Embedding

This section provides a complete step-by-step guide to create a Power BI report from scratch and make it ready for embedding via Power BI Embedded.

### Step 1: Install Power BI Desktop

1. Download **Power BI Desktop** from the [Microsoft Store](https://aka.ms/pbidesktopstore) or [Download Center](https://powerbi.microsoft.com/desktop/)
2. Install and launch Power BI Desktop
3. Sign in with your organizational account (requires Power BI Pro or PPU license)

### Step 2: Create a New Report with Sample Data

For this demo, we'll create a simple sales report:

1. Open **Power BI Desktop**
2. Click **Get data** → **Enter data** (or use **Excel workbook** / **SQL Server** for real data)
3. Create a sample table with the following data:

| Product | Q1 Forecast | Q1 Actual | Q2 Forecast | Q2 Actual | Q3 Forecast | Q3 Actual | Q4 Forecast | Q4 Actual | Total Forecast | Total Actual |
   |---------|-------------|-----------|-------------|-----------|-------------|-----------|-------------|-----------|----------------|--------------|
   | Laptops | 50000 | 48500 | 55000 | 57200 | 60000 | 58000 | 70000 | 72500 | 235000 | 236200 |
   | Monitors | 25000 | 26800 | 28000 | 27500 | 30000 | 31200 | 35000 | 34000 | 118000 | 119500 |
   | Keyboards | 8000 | 7500 | 9000 | 9200 | 10000 | 10500 | 12000 | 11800 | 39000 | 39000 |
   | Mice | 5000 | 5200 | 5500 | 5400 | 6000 | 6100 | 7000 | 7200 | 23500 | 23900 |
   | Headsets | 12000 | 11500 | 14000 | 14800 | 15000 | 15200 | 18000 | 17500 | 59000 | 59000 |
   | Webcams | 6000 | 6500 | 7000 | 7200 | 8000 | 7800 | 9000 | 9500 | 30000 | 31000 |

4. Name the table `Sales` and click **Load**


### Step 3: Build Visualizations

1. In the **Report view** (left sidebar), create visualizations:

   **Suggested visuals:**
   - **Bar Chart**: Drag `Category` to Axis, `Sales` to Values
   - **Pie Chart**: Drag `Region` to Legend, `Quantity` to Values
   - **Card**: Drag `Sales` to display total sales
   - **Table**: Drag `Category`, `Region`, `Sales`, `Quantity`

   **Suggested visuals for SalesForecast table:**
   - **Clustered Bar Chart**: Drag `Product` to Axis, `Total Forecast` and `Total Actual` to Values (compare totals)
   - **Line Chart**: Create measures for quarterly trends (Q1-Q4 Forecast vs Actual)
   - **Matrix**: Drag `Product` to Rows, all quarterly values to Values
   - **KPI Card**: Show variance between Total Forecast and Total Actual
   - **Waterfall Chart**: Visualize quarterly contributions to total sales

2. Arrange visuals on the canvas
3. Add a title using a **Text box**: "Sales Dashboard"

### Step 4: Verify Table and Column Names

**⚠️ Important:** Note the exact table and column names for filtering:

1. Click the **Model view** icon (left sidebar - looks like 3 connected boxes)
2. You'll see your table structure:
   ```
   Sales (table name)
   ├── Product (column - use this for filtering)
   ├── Q1 Forecast
   ├── Q1 Actual
   ├── Q2 Forecast
   ├── Q2 Actual
   ├── Q3 Forecast
   ├── Q3 Actual
   ├── Q4 Forecast
   ├── Q4 Actual
   ├── Total Forecast
   └── Total Actual
   ```
3. **Remember these names** - you'll need them to configure filters in the app

### Step 5: Save the Report Locally

1. Click **File** → **Save as**
2. Save as `SalesReport.pbix` in a location you can find later
3. This is your local backup

### Step 6: Create a Power BI Workspace

Reports must be published to a **Workspace** (not "My Workspace") for embedding:

1. Go to [Power BI Service](https://app.powerbi.com)
2. Sign in with your organizational account
3. In the left navigation, click **Workspaces** → **Create a workspace**
4. Enter a name (e.g., "Embedded Reports Workspace")
5. **Important:** Choose the workspace type:
   - **Pro workspace**: Requires all users to have Pro license
   - **Premium Per User**: Better for embedding scenarios
   - **Premium capacity**: Best for production (dedicated resources)
6. Click **Save**

### Step 7: Publish the Report to the Workspace

1. In **Power BI Desktop**, click **Publish** (Home ribbon)
2. Sign in if prompted
3. Select your workspace (e.g., "Embedded Reports Workspace")
4. Click **Select**
5. Wait for the publish to complete
6. Click **Open 'SalesReport.pbix' in Power BI** to view it online

### Step 8: Verify the Published Report

1. In Power BI Service, navigate to your workspace
2. You should see:
   - **Report**: SalesReport
   - **Dataset**: SalesReport (semantic model)
3. Click on the report to open and verify it works correctly

### Step 9: Get the Workspace ID and Report ID

These IDs are required for embedding:

#### Workspace ID:
1. Open your workspace in Power BI Service
2. Look at the URL in the browser:
   ```
   https://app.powerbi.com/groups/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/list
                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                  This is your WORKSPACE_ID
   ```

#### Report ID:
1. Open your report in the workspace
2. Look at the URL:
   ```
   https://app.powerbi.com/groups/.../reports/yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy/...
                                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                              This is your REPORT_ID
   ```

### Step 10: Configure Dataset Credentials (If Using External Data)

If your report connects to external data sources (SQL Server, SharePoint, etc.):

1. In your workspace, click on **Settings** (gear icon) next to the dataset
2. Go to **Data source credentials**
3. Click **Edit credentials** for each data source
4. Enter credentials and configure:
   - **Authentication method**: Basic, OAuth2, etc.
   - **Privacy level**: Organizational (recommended for embedding)
5. Click **Sign in** / **Save**

### Step 11: Enable Service Principal Access

The Service Principal needs explicit access to the workspace:

1. In your workspace, click **Access** (top right)
2. Enter your app registration name (e.g., "PowerBI-Embedded-App")
3. Select role:
   - **Member**: Can view and interact with content
   - **Admin**: Full control (recommended for embedded apps)
4. Click **Add**

### Summary: Required Values for `.env`

After completing these steps, you should have:

| Value | Where to Find | Example |
|-------|---------------|---------|
| `WORKSPACE_ID` | Workspace URL after `/groups/` | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `REPORT_ID` | Report URL after `/reports/` | `yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy` |
| `CLIENT_ID` | Azure AD App Registration | `aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa` |
| `CLIENT_SECRET` | Azure AD → Certificates & secrets | `your-secret-value` |
| `TENANT_ID` | Azure AD Overview page | `bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb` |

### Filter Configuration for This Example

Update `app.py` with the table/column from your report:

```python
filter_config = {
    "tableName": "Sales",      # Your table name from Step 4
    "columnName": "Category",  # Column to filter on
}

filter_values = [
    "All",
    "Account",
    "Customer", 
    "Region",
    "Product"
]
```

---

## Setup Guide

### Step 1: Register an Azure AD Application

1. Go to [Azure Portal](https://portal.azure.com) → **Azure Active Directory** → **App registrations**
2. Click **New registration**
3. Enter a name (e.g., "PowerBI-Embedded-App")
4. Select **Accounts in this organizational directory only**
5. Click **Register**
6. Note down:
   - **Application (client) ID** → `CLIENT_ID`
   - **Directory (tenant) ID** → `TENANT_ID`

### Step 2: Create a Client Secret

1. In your app registration, go to **Certificates & secrets**
2. Click **New client secret**
3. Add a description and select expiration
4. Click **Add**
5. **Copy the secret value immediately** → `CLIENT_SECRET`
   - ⚠️ You won't be able to see it again!

### Step 3: Create a Security Group (Recommended)

1. Go to **Azure Active Directory** → **Groups** → **New group**
2. Create a Security group (e.g., "PowerBI-Embedded-Apps")
3. Add your Service Principal as a member:
   - Go to the group → **Members** → **Add members**
   - Search for your app registration name
   - Add it as a member

### Step 4: Configure Power BI Tenant Settings

1. Go to [Power BI Admin Portal](https://app.powerbi.com/admin-portal)
2. Navigate to **Tenant settings**
3. Enable the following settings:

   | Setting | Configuration |
   |---------|---------------|
   | **Allow service principals to use Power BI APIs** | Enable for your security group |
   | **Allow service principals to create and use profiles** | Enable for your security group |
   | **Embed content in apps** | Enable for the entire organization or your group |

4. Click **Apply** for each setting (changes may take up to 15 minutes)

### Step 5: Add Service Principal to Power BI Workspace

1. Go to your Power BI workspace
2. Click **Access** (or **Manage access**)
3. Add your Service Principal:
   - Search for your app registration name
   - Select **Admin** or **Member** role
   - Click **Add**

### Step 6: Get Workspace ID and Report ID

#### Finding the Workspace ID:
1. Open your workspace in Power BI Service
2. Look at the URL: `https://app.powerbi.com/groups/{WORKSPACE_ID}/...`
3. Copy the GUID after `/groups/`

#### Finding the Report ID:
1. Open your report in Power BI Service
2. Look at the URL: `https://app.powerbi.com/groups/{workspace}/reports/{REPORT_ID}/...`
3. Copy the GUID after `/reports/`

---

## Configuration

### Step 1: Create Environment File

```bash
# Copy the example file
cp .env.example .env
```

### Step 2: Fill in Your Values

Edit `.env` with your actual values:

```env
# Azure AD Credentials
CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
CLIENT_SECRET=your_secret_value_here
TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# Power BI Configuration
WORKSPACE_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
REPORT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# Optional
DATASET_ID=
FLASK_SECRET_KEY=your-random-secret-key
FLASK_DEBUG=True
```

---

## Running the Application

### Step 1: Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Run the Application

```bash
# Using Flask CLI
flask run

# Or run directly
python app.py
```

### Step 3: Open in Browser

Navigate to: **http://localhost:5000**

---

## Configuring the Filter (Table and Column Names)

The dropdown filter needs to know which table and column to filter in your Power BI report.

### Finding Table and Column Names

1. **Open your report in Power BI Desktop**
2. Go to **Model view** (left sidebar)
3. Find the table containing the data you want to filter
4. Note the **exact table name** and **column name**

   Example:
   - Table: `Sales`
   - Column: `Category`

### Updating the Filter Configuration

#### Option 1: Update in Backend (Recommended)

Edit `app.py`, find the `/api/filter-values` endpoint:

```python
filter_config = {
    "tableName": "Sales",       # ← Replace with your table name
    "columnName": "Category",   # ← Replace with your column name
}
```

Also update the filter values to match your data:

```python
filter_values = [
    "All",           # Keep this for clearing filters
    "Electronics",   # ← Your actual filter values
    "Clothing",
    "Furniture",
    # ... add your values
]
```

#### Option 2: Update in Frontend

If you prefer, edit `static/js/app.js`:

```javascript
let filterConfig = {
    tableName: "Sales",       // ← Replace with your table name
    columnName: "Category"    // ← Replace with your column name
};
```

---

## Testing the Application

1. **Open the application** at http://localhost:5000
2. **Wait for the report to load** (status will show "Report ready")
3. **Select a value** from the dropdown
4. **Observe the report filter** - the report should update without page reload
5. **Select "All"** to clear the filter

### Expected Behavior

| Action | Result |
|--------|--------|
| Page load | Report embeds with no filters |
| Select value (e.g., "Product") | Report filters to show only that value |
| Select "All" | All filters are cleared |

---

## Troubleshooting

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| **401 Unauthorized** | Invalid credentials | Check `CLIENT_ID`, `CLIENT_SECRET`, `TENANT_ID` |
| **403 Forbidden** | Insufficient permissions | Add Service Principal to workspace as Admin/Member |
| **404 Not Found** | Invalid IDs | Verify `WORKSPACE_ID` and `REPORT_ID` |
| **Filter doesn't work** | Wrong table/column name | Check exact names in Power BI Desktop Model view |

### Checking Authentication

Test your credentials by visiting:
```
http://localhost:5000/api/health
```

Expected response:
```json
{
    "status": "healthy",
    "message": "Application is running and can authenticate with Azure AD"
}
```

### Browser Console Errors

Open browser Developer Tools (F12) → Console tab to see detailed JavaScript errors.

Common issues:
- **"table not found"** → Update `tableName` in filter config
- **"column not found"** → Update `columnName` in filter config
- **CORS errors** → Ensure you're accessing via `localhost`, not `127.0.0.1`

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main HTML page with embedded report |
| `/api/embed-config` | GET | Returns embed token and configuration |
| `/api/filter-values` | GET | Returns dropdown values and filter config |
| `/api/health` | GET | Health check endpoint |

### Example Response: `/api/embed-config`

```json
{
    "embedToken": "eyJ0eXAiOiJKV1Q...",
    "embedUrl": "https://app.powerbi.com/reportEmbed?reportId=...",
    "reportId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "datasetId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "tokenExpiry": "2024-01-15T12:00:00Z"
}
```

---

## Security Considerations

⚠️ **Important for Production:**

1. **Never commit `.env`** - Add it to `.gitignore`
2. **Rotate client secrets** regularly
3. **Use HTTPS** in production
4. **Implement proper authentication** for your users
5. **Monitor embed token usage** via Azure logs
6. **Consider Row-Level Security (RLS)** for user-specific data access

---

## Additional Resources

- [Power BI Embedded Documentation](https://docs.microsoft.com/en-us/power-bi/developer/embedded/)
- [Register an Azure AD App](https://docs.microsoft.com/en-us/power-bi/developer/embedded/register-app)
- [Embed Setup Tool](https://app.powerbi.com/embedsetup)
- [powerbi-client JavaScript Library](https://github.com/microsoft/PowerBI-JavaScript)
- [Power BI REST API Reference](https://docs.microsoft.com/en-us/rest/api/power-bi/)

---

## License

This demo application is provided as-is for educational purposes.
