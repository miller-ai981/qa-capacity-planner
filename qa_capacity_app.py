# QA Sprint Capacity Planner
# A simple, trustworthy tool for QA capacity planning
#
# Installation: pip install streamlit pandas plotly requests openpyxl

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import requests
import base64
import json
from typing import Dict, List, Optional
import io

# CHANGE LOG (Recent updates):
# - Fixed calculate_qa_hours() to read from session state (user-editable mapping)
# - Added Azure DevOps connection form with Test Connection button
# - Added connection status display in header
# - Block sprint sync unless Azure is connected
# - Reduced chart overload (moved advanced charts to expander)
# - Added last sync time tracking

# ============================================================================
# CONFIGURATION & ASSUMPTIONS
# ============================================================================

# Default assumptions (editable by user)
DEFAULT_SPRINT_DAYS = 10
DEFAULT_DAILY_CAPACITY = 7
TOTAL_CAPACITY_PER_QA = DEFAULT_SPRINT_DAYS * DEFAULT_DAILY_CAPACITY  # 70 hours

# QA Hours Mapping: Story Points → QA Testing Hours
# Based on typical QA effort for different story sizes
QA_HOURS_MAPPING = {
    1: 2,   # Small story: Quick testing
    2: 3,   # Small-medium: Basic feature testing
    3: 5,   # Medium: Standard feature testing
    4: 7,   # Medium-large: Complex feature
    5: 7,   # Large: Significant testing effort
    6: 7,   # Large: Extended testing
    7: 8,   # Very large: Comprehensive testing
    8: 10,  # Very large: Full regression needed
    9: 9,   # Extra large: Extensive testing
    10: 9   # Extra large: Maximum effort
}

# Risk thresholds (hours remaining)
RISK_HIGH_THRESHOLD = 0      # Overallocated
RISK_MEDIUM_THRESHOLD = 10   # Tight buffer

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="QA Capacity Planner",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# STYLING
# ============================================================================

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    /* Global text color override - catches all grey text */
    # body, p, span, div, label, h1, h2, h3, h4, h5, h6, li, td, th, a {
    #     color: rgba(255, 255, 255, 0.95) !important;
    # }
    
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    }
    
    .main {
        background: transparent;
    }
    
    /* Remove white banner/header */
    header {
        background: transparent !important;
    }
    
    [data-testid="stHeader"] {
        background: transparent !important;
        display: none !important;
    }
    
    /* Hide default Streamlit toolbar */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Glass morphism cards */
    .metric-card {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 25px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px 0 rgba(31, 38, 135, 0.5);
    }
    
    /* Modern metrics */
    div[data-testid="stMetricValue"] {
        font-size: 36px;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    div[data-testid="stMetricLabel"] {
        color: rgba(255, 255, 255, 0.9);
        font-weight: 600;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    div[data-testid="stMetricDelta"] {
        color: #48bb78;
        font-weight: 600;
    }
    
    /* Headers */
    h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: 800;
        font-size: 48px;
        margin-bottom: 10px;
    }
    
    h2, h3 {
        color: rgba(255, 255, 255, 0.95);
        font-weight: 700;
    }
    
    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        border-radius: 12px;
        padding: 12px 32px;
        font-weight: 700;
        border: none;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-size: 14px;
    }
    
    .stButton>button:hover {
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        transform: translateY(-2px);
    }
    
    /* Download buttons - glassmorphism style */
    .stDownloadButton>button {
        background: rgba(255, 255, 255, 0.1) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        color: white !important;
        border-radius: 12px;
        padding: 12px 24px;
        font-weight: 600;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        transition: all 0.3s ease;
    }
    
    .stDownloadButton>button:hover {
        background: rgba(255, 255, 255, 0.15) !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
        transform: translateY(-2px);
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(15, 12, 41, 0.95) 0%, rgba(48, 43, 99, 0.95) 100%);
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    [data-testid="stSidebar"] h2 {
        color: white;
        font-weight: 700;
    }
    
    /* Input fields */
    .stTextInput>div>div>input, .stNumberInput>div>div>input {
        background: rgba(240, 242, 246, 0.95) !important;
        border: 1px solid rgba(200, 200, 220, 0.5) !important;
        border-radius: 10px !important;
        color: #1a202c !important;
        padding: 12px !important;
        backdrop-filter: blur(5px) !important;
        font-weight: 500 !important;
    }
    
    .stTextInput>div>div>input::placeholder, .stNumberInput>div>div>input::placeholder {
        color: rgba(100, 100, 120, 0.6) !important;
    }
    
    .stTextInput>div>div>input:focus, .stNumberInput>div>div>input:focus {
        border: 2px solid #667eea !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1) !important;
        color: #1a202c !important;
        background: rgba(255, 255, 255, 0.98) !important;
    }
    
    /* Password input text should also be black */
    input[type="password"] {
        color: #1a202c !important;
        background: rgba(240, 242, 246, 0.95) !important;
        font-weight: 600 !important;
    }
    
    /* Input labels */
    .stTextInput>label, .stNumberInput>label, .stFileUploader>label {
        color: rgba(255, 255, 255, 0.95) !important;
        font-weight: 600 !important;
        font-size: 14px !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(255, 255, 255, 0.05);
        padding: 10px;
        border-radius: 15px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: rgba(255, 255, 255, 0.7);
        border-radius: 10px;
        padding: 12px 24px;
        font-weight: 600;
        transition: all 0.3s;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    /* Dataframe */
    .dataframe {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Column headers in dataframes */
    .stDataFrame th {
        color: white !important;
        background-color: rgba(102, 126, 234, 0.5) !important;
        font-weight: 600 !important;
    }
    
    /* Dataframe cells - FORCE DARK TEXT WITH HIGHEST SPECIFICITY */
    .stDataFrame td {
        color: #1a202c !important;
        background-color: rgba(255, 255, 255, 0.95) !important;
        font-weight: 500 !important;
    }
    
    /* Target the actual text elements inside cells */
    .stDataFrame td div {
        color: #1a202c !important;
    }
    
    .stDataFrame td span {
        color: #1a202c !important;
    }
    
    .stDataFrame td p {
        color: #1a202c !important;
    }
    
    /* Dataframe container */
    [data-testid="stDataFrame"] {
        background: rgba(255, 255, 255, 0.95) !important;
    }
    
    /* Table body background */
    [data-testid="stDataFrame"] table {
        background-color: white !important;
    }
    
    [data-testid="stDataFrame"] tbody {
        background-color: white !important;
    }
    
    /* Table rows */
    [data-testid="stDataFrame"] tbody tr {
        background-color: rgba(255, 255, 255, 0.95) !important;
    }
    
    [data-testid="stDataFrame"] tbody tr:hover {
        background-color: rgba(240, 242, 246, 1) !important;
    }
    
    /* Force all text in dataframes to be dark */
    [data-testid="stDataFrame"] * {
        color: #1a202c !important;
    }
    
    /* But keep headers white */
    [data-testid="stDataFrame"] thead * {
        color: white !important;
    }
    
    /* Make other text white (not in dataframes) */
    .stMarkdown p,
    .stMarkdown span,
    .stMarkdown div,
    .stAlert p,
    .stAlert span {
        color: rgba(255, 255, 255, 0.95) !important;
    }
    
    /* Headings white */
    h1, h2, h3, h4, h5, h6 {
        color: rgba(255, 255, 255, 0.95) !important;
    }
    
    /* Labels white */
    label:not([data-testid="stDataFrame"] label) {
        color: rgba(255, 255, 255, 0.95) !important;
    }
    
    /* Alerts */
    .stAlert {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        border-left: 4px solid;
    }
    
    /* Info boxes text */
    .stAlert p, .stAlert li, .stAlert strong {
        color: rgba(255, 255, 255, 0.95) !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: rgba(255, 255, 255, 0.05) !important;
        border-radius: 10px !important;
        color: white !important;
        font-weight: 600 !important;
    }
    
    .streamlit-expanderHeader:hover {
        background: rgba(255, 255, 255, 0.1) !important;
    }
    
    .streamlit-expanderContent {
        background: rgba(255, 255, 255, 0.03) !important;
        border-radius: 10px !important;
        color: white !important;
    }
    
    /* File uploader - make it visible */
    .stFileUploader {
        background: rgba(240, 242, 246, 0.2) !important;
        border: 2px dashed rgba(200, 200, 220, 0.5) !important;
        border-radius: 12px !important;
        padding: 15px !important;
    }
    
    .stFileUploader label {
        color: rgba(255, 255, 255, 0.95) !important;
        font-weight: 600 !important;
    }
    
    .stFileUploader section {
        background: rgba(240, 242, 246, 0.9) !important;
        border: 1px solid rgba(200, 200, 220, 0.5) !important;
        border-radius: 8px !important;
        padding: 10px !important;
    }
    
    .stFileUploader section > div {
        color: #4a5568 !important;
    }
    
    .stFileUploader button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        padding: 8px 16px !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
    }
    
    .stFileUploader small {
        color: rgba(200, 200, 220, 0.9) !important;
    }
    
    /* Selectbox container */
    .stSelectbox>div>div {
        background: rgba(240, 242, 246, 0.95) !important;
        border: 1px solid rgba(200, 200, 220, 0.5) !important;
        color: #1a202c !important;
    }
    
    /* Selectbox text */
    .stSelectbox>div>div>div {
        color: #1a202c !important;
        background: rgba(240, 242, 246, 0.95) !important;
        font-weight: 500 !important;
    }
    
    .stSelectbox>label {
        color: rgba(255, 255, 255, 0.95) !important;
        font-weight: 600 !important;
    }
    
    /* Plotly charts background */
    .js-plotly-plot {
        background: rgba(255, 255, 255, 0.05) !important;
        border-radius: 15px;
        padding: 10px;
        backdrop-filter: blur(10px);
    }
    
    /* All paragraph text */
    p {
        color: rgba(255, 255, 255, 0.95) !important;
    }
    
    /* Markdown text */
    .stMarkdown p, .stMarkdown li, .stMarkdown strong, .stMarkdown em {
        color: rgba(255, 255, 255, 0.95) !important;
    }
    
    .info-box {
        background: rgba(255, 255, 255, 0.1);
        padding: 15px;
        border-radius: 12px;
        border-left: 4px solid #667eea;
        color: white;
        margin: 10px 0;
        backdrop-filter: blur(10px);
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# AZURE DEVOPS INTEGRATION
# ============================================================================

# class AzureDevOpsClient:
#     """Simple Azure DevOps API client for fetching work items"""
    
#     def __init__(self, organization: str, project: str, pat: str):
#         self.organization = organization
#         self.project = project
#         self.base_url = f"https://dev.azure.com/{organization}/{project}/_apis"
#         self.headers = {
#             'Content-Type': 'application/json',
#             'Authorization': f'Basic {base64.b64encode(f":{pat}".encode()).decode()}'
#         }
    
#     def get_sprints(self) -> List[Dict]:
#         """Fetch available sprints"""
#         url = f"{self.base_url}/work/teamsettings/iterations?api-version=7.0"
#         try:
#             response = requests.get(url, headers=self.headers)
#             response.raise_for_status()
#             return response.json().get('value', [])
#         except Exception as e:
#             st.error(f"Failed to fetch sprints: {str(e)}")
#             return []
    
#     def get_sprint_work_items(self, iteration_path: str) -> List[Dict]:
#         """Fetch work items for a specific sprint with pagination support"""
#         wiql_query = {
#             "query": f"""
#                 SELECT [System.Id], [System.Title], [System.WorkItemType], 
#                        [System.State], [Microsoft.VSTS.Scheduling.StoryPoints],
#                        [System.AreaPath], [System.AssignedTo]
#                 FROM WorkItems
#                 WHERE [System.IterationPath] = '{iteration_path}'
#                   AND [System.WorkItemType] IN ('User Story', 'Bug')
#                   AND [System.State] <> 'Removed'
#                 ORDER BY [System.Id]
#             """
#         }
        
#         url = f"{self.base_url}/wit/wiql?api-version=7.0"
#         try:
#             response = requests.post(url, headers=self.headers, json=wiql_query)
#             response.raise_for_status()
#             work_item_refs = response.json().get('workItems', [])
            
#             if not work_item_refs:
#                 return []
            
#             # Fetch work item details with pagination (max 200 IDs per request)
#             all_work_items = []
#             batch_size = 200
            
#             for i in range(0, len(work_item_refs), batch_size):
#                 batch = work_item_refs[i:i + batch_size]
#                 ids = ','.join([str(wi['id']) for wi in batch])
#                 details_url = f"{self.base_url}/wit/workitems?ids={ids}&api-version=7.0"
#                 details_response = requests.get(details_url, headers=self.headers)
#                 details_response.raise_for_status()
                
#                 batch_items = details_response.json().get('value', [])
#                 all_work_items.extend(batch_items)
            
#             return all_work_items
            
#         except requests.exceptions.HTTPError as e:
#             if e.response.status_code == 401:
#                 st.error("❌ Authentication failed. Please check your Personal Access Token.")
#             elif e.response.status_code == 404:
#                 st.error("❌ Project or organization not found. Please verify your configuration.")
#             else:
#                 st.error(f"❌ HTTP Error: {e.response.status_code} - {str(e)}")
#             return []
#         except requests.exceptions.RequestException as e:
#             st.error(f"❌ Connection error: {str(e)}")
#             return []
#         except Exception as e:
#             st.error(f"❌ Unexpected error: {str(e)}")
#             return []
class AzureDevOpsClient:
    """Simple Azure DevOps API client for fetching work items"""
    
    def __init__(self, organization: str, project: str, pat: str):
        self.organization = organization
        self.project = project
        self.base_url = f"https://dev.azure.com/{organization}/{project}/_apis"
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Basic {base64.b64encode(f":{pat}".encode()).decode()}'
        }
    
    def get_sprints(self) -> List[Dict]:
        """Fetch available sprints"""
        url = f"{self.base_url}/work/teamsettings/iterations?api-version=7.0"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json().get('value', [])
        except Exception as e:
            st.error(f"Failed to fetch sprints: {str(e)}")
            return []
        

    def get_custom_fields(self) -> List[Dict]:
        url = f"{self.base_url}/wit/fields?api-version=7.0"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            fields = response.json().get('value', [])
            
            # Filter to show only custom fields and QA-related fields
            qa_relevant_fields = [
                f for f in fields 
                if f.get('custom', False) or 'QA' in f.get('name', '') or 'Test' in f.get('name', '')
            ]
            
            return qa_relevant_fields
        except Exception as e:
            st.error(f"Failed to fetch field definitions: {str(e)}")
            return []

    def get_current_iteration_path(self) -> str:
        url = f"{self.base_url}/work/teamsettings/iterations?api-version=7.0"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()

        iterations = response.json().get("value", [])
        for iteration in iterations:
            if iteration.get("attributes", {}).get("timeFrame") == "current":
                return iteration.get("path")

        raise Exception("No active (current) iteration found for this team.")

    # CHANGE: Removed get_sprint_work_items() that used hardcoded iteration_path
    # NEW METHOD: Use @CurrentIteration macro instead
    # def get_current_iteration_work_items(
    #     self,
    #     area_path_filter: str = None,
    #     qa_team: str = None
    # ) -> List[Dict]:


    #     try:
    #         # ✅ STEP 1: Resolve current iteration path explicitly
    #         current_iteration_path = self.get_current_iteration_path()

    #         # ✅ STEP 2: Build WIQL with explicit iteration path
    #         wiql_query = {
    #             "query": """
    #                 SELECT
    #                     [System.Id],
    #                     [System.Title],
    #                     [System.WorkItemType],
    #                     [System.State],
    #                     [System.AreaPath],
    #                     [System.AssignedTo],
    #                     [Microsoft.VSTS.Scheduling.StoryPoints]
    #                 FROM WorkItems
    #                 WHERE
    #                     [System.IterationPath] = @CurrentIteration
    #                     AND [System.WorkItemType] IN ('User Story', 'Bug')
    #                     AND [System.State] NOT IN ('Closed', 'Done', 'Removed')
    #             """
    #         }



    #         # ✅ Optional AreaPath filter
    #         if area_path_filter and area_path_filter.strip():
    #             wiql_query["query"] += (
    #                 f"\nAND [System.AreaPath] UNDER '{area_path_filter.strip()}'"
    #             )

    #         wiql_query["query"] += "\nORDER BY [System.Id]"

    #         # ✅ STEP 3: Execute WIQL
    #         url = f"{self.base_url}/wit/wiql?api-version=7.0"
    #         response = requests.post(url, headers=self.headers, json=wiql_query)
    #         response.raise_for_status()

    #         work_item_refs = response.json().get("workItems", [])
    #         if not work_item_refs:
    #             return []

    #         # ✅ STEP 4: Fetch details in batches
    #         all_work_items = []
    #         batch_size = 200

    #         for i in range(0, len(work_item_refs), batch_size):
    #             batch = work_item_refs[i:i + batch_size]
    #             ids = ",".join(str(wi["id"]) for wi in batch)

    #             details_url = (
    #                 f"{self.base_url}/wit/workitems"
    #                 f"?ids={ids}&api-version=7.0"
    #             )

    #             details_response = requests.get(details_url, headers=self.headers)
    #             details_response.raise_for_status()
    #             all_work_items.extend(details_response.json().get("value", []))

    #         return all_work_items

    #     except requests.exceptions.HTTPError as e:
    #         st.error(f"❌ HTTP Error: {e.response.status_code} - {e.response.text}")
    #         return []
    #     except Exception as e:
    #         st.error(f"❌ Failed to fetch sprint work items: {str(e)}")
    #         return []
    def get_current_iteration_work_items(
        self,
        area_path_filter: str = None,
        qa_team: str = None
    ) -> List[Dict]:
        """
        Fetch work items for CURRENT ITERATION ONLY.
        Uses only standard fields to avoid WIQL errors.
        """
        try:
            current_iteration_path = self.get_current_iteration_path()

            wiql_query = {
                "query": """
                    SELECT
                        [System.Id],
                        [System.Title],
                        [System.WorkItemType],
                        [System.State],
                        [System.AreaPath],
                        [System.AssignedTo],
                        [Microsoft.VSTS.Scheduling.StoryPoints]
                    FROM WorkItems
                    WHERE
                        [System.IterationPath] = @CurrentIteration
                        AND [System.WorkItemType] IN ('User Story', 'Bug')
                        AND [System.State] NOT IN ('Closed', 'Done', 'Removed')
                """
            }

            if area_path_filter and area_path_filter.strip():
                wiql_query["query"] += (
                    f"\nAND [System.AreaPath] UNDER '{area_path_filter.strip()}'"
                )

            wiql_query["query"] += "\nORDER BY [System.Id]"

            url = f"{self.base_url}/wit/wiql?api-version=7.0"
            response = requests.post(url, headers=self.headers, json=wiql_query)
            response.raise_for_status()

            work_item_refs = response.json().get("workItems", [])
            if not work_item_refs:
                return []

            # Fetch details in batches
            all_work_items = []
            batch_size = 200

            for i in range(0, len(work_item_refs), batch_size):
                batch = work_item_refs[i:i + batch_size]
                ids = ",".join(str(wi["id"]) for wi in batch)

                # details_url = (
                #     f"{self.base_url}/wit/workitems"
                #     f"?ids={ids}&api-version=7.0"
                # )
                details_url = (
                    f"{self.base_url}/wit/workitems"
                    f"?ids={ids}"
                    f"&$expand=fields"
                    f"&api-version=7.0"
                )


                details_response = requests.get(details_url, headers=self.headers)
                details_response.raise_for_status()
                all_work_items.extend(details_response.json().get("value", []))

            return all_work_items

        except requests.exceptions.HTTPError as e:
            st.error(f"❌ HTTP Error: {e.response.status_code} - {e.response.text}")
            return []
        except Exception as e:
            st.error(f"❌ Failed to fetch sprint work items: {str(e)}")
            return []

# ============================================================================
# PROBLEM 3: QA TEAM FILTERING (Client-side)
# ============================================================================

# def filter_work_items_by_qa_team(work_items_df: pd.DataFrame, qa_team_input: str) -> pd.DataFrame:
#     """
#     CHANGE: Filter work items to ONLY include items assigned to defined QA team
    
#     Args:
#         work_items_df: DataFrame of work items from Azure
#         qa_team_input: Comma-separated QA names (e.g. "Sarah, Ahmed, Mike")
    
#     Returns:
#         Filtered DataFrame with only QA-owned items
        
#     RATIONALE:
#     - Developers, PMs, designers appear in AssignedTo
#     - Azure has no "QA Role" system field
#     - User explicitly defines their QA team
#     - Simple, secure, works everywhere
#     """
#     if not qa_team_input or not qa_team_input.strip():
#         # If no QA team defined, return all items (fallback to old behavior)
#         return work_items_df
    
#     # Parse comma-separated QA names and strip whitespace
#     qa_names = [name.strip() for name in qa_team_input.split(',') if name.strip()]
    
#     if not qa_names:
#         return work_items_df
    
#     # Filter: Keep only items assigned to defined QA team
#     # Items assigned to others (devs, PMs) are excluded
#     filtered = work_items_df[work_items_df['Assigned QA'].isin(qa_names)]
    
#     # Also keep unassigned items (QA will assign them)
#     unassigned = work_items_df[work_items_df['Assigned QA'] == 'Unassigned']
    
#     result = pd.concat([filtered, unassigned], ignore_index=True)
#     return result.sort_values('Assigned QA')  # PROBLEM 5: Sort by Assigned QA
def extract_qa_owner(work_item: Dict, qa_field_reference: str) -> str:
    """
    Extract QA owner name from work item using provided field reference.
    
    Safely handles:
    - Person object (dict with 'displayName')
    - String value
    - Missing/None value
    - Empty value
    - Invalid field reference
    
    Args:
        work_item: Work item dict from Azure DevOps
        qa_field_reference: Field reference name (e.g., 'Custom.QATestedBy')
    
    Returns:
        QA owner name or 'Unassigned'
    """
    # No field configured
    if not qa_field_reference or not qa_field_reference.strip():
        return 'Unassigned'
    
    fields = work_item.get('fields', {})
    qa_value = fields.get(qa_field_reference)
    
    # Field doesn't exist in this work item
    if qa_value is None or qa_value == '':
        return 'Unassigned'
    
    # Handle person object (dict with displayName)
    if isinstance(qa_value, dict):
        display_name = qa_value.get('displayName', '')
        return display_name if display_name.strip() else 'Unassigned'
    
    # Handle string value
    if isinstance(qa_value, str):
        return qa_value.strip() if qa_value.strip() else 'Unassigned'
    
    # Fallback for other types
    return 'Unassigned'
def filter_work_items_by_qa_team(work_items_df: pd.DataFrame, qa_team_input: str) -> pd.DataFrame:
    '''Filter work items to only include items with QA owner in defined team'''
    if not qa_team_input or not qa_team_input.strip():
        return work_items_df
    
    qa_names = [name.strip() for name in qa_team_input.split(',') if name.strip()]
    
    if not qa_names:
        return work_items_df
    
    # Filter using 'QA Owner' column (universal)
    filtered = work_items_df[work_items_df['QA Owner'].isin(qa_names)]
    unassigned = work_items_df[work_items_df['QA Owner'] == 'Unassigned']
    
    result = pd.concat([filtered, unassigned], ignore_index=True)
    return result.sort_values('QA Owner').reset_index(drop=True)


# ============================================================================
# CAPACITY CALCULATION LOGIC
# ============================================================================

def calculate_qa_hours(story_points: int) -> int:
    """
    Convert story points to estimated QA hours
    
    CHANGE LOG: Now reads from session state if mapping was edited by user
    Falls back to default QA_HOURS_MAPPING if not customized
    """
    # Use custom mapping if user edited it, otherwise use default
    mapping = st.session_state.get('qa_hours_mapping', QA_HOURS_MAPPING)
    
    if story_points > 10:
        # For story points above 10, use the max mapping value
        return mapping.get(10, 9)
    return mapping.get(story_points, 0)

# def process_work_items(work_items: List[Dict]) -> pd.DataFrame:
#     """Convert Azure DevOps work items to structured data
    
#     CHANGE: Better handling of missing/malformed data
#     """
#     data = []
#     for wi in work_items:
#         fields = wi.get('fields', {})
        
#         # Handle missing story points gracefully
#         story_points = fields.get('Microsoft.VSTS.Scheduling.StoryPoints')
#         if story_points is None or story_points == '':
#             story_points = 0
#         else:
#             try:
#                 story_points = int(story_points)
#             except (ValueError, TypeError):
#                 story_points = 0
        
#         # Handle missing assigned to (defensive)
#         assigned_to = fields.get('System.AssignedTo', {})
#         if isinstance(assigned_to, dict):
#             assigned_qa = assigned_to.get('displayName', 'Unassigned')
#         else:
#             assigned_qa = 'Unassigned'
        
#         # CHANGE: Validate assigned_qa is not None or empty
#         if not assigned_qa or assigned_qa.strip() == '':
#             assigned_qa = 'Unassigned'
        
#         data.append({
#             'ID': wi.get('id'),
#             'Title': fields.get('System.Title', ''),
#             'Type': fields.get('System.WorkItemType', ''),
#             'State': fields.get('System.State', ''),
#             'Story Points': story_points,
#             'QA Hours': calculate_qa_hours(story_points),
#             'Assigned QA': assigned_qa
#         })
    
#     return pd.DataFrame(data)

# def process_work_items(work_items: List[Dict]) -> pd.DataFrame:
#     '''Convert Azure DevOps work items to structured data'''
#     data = []
#     for wi in work_items:
#         fields = wi.get('fields', {})
        
#         story_points = fields.get('Microsoft.VSTS.Scheduling.StoryPoints')
#         if story_points is None or story_points == '':
#             story_points = 0
#         else:
#             try:
#                 story_points = int(story_points)
#             except (ValueError, TypeError):
#                 story_points = 0
        
#         # CHANGE: Extract TestedBy (QA ownership field)
#         tested_by = fields.get('Microsoft.VSTS.Common.TestedBy', {})
#         if isinstance(tested_by, dict):
#             qa_name = tested_by.get('displayName', 'Unassigned')
#         else:
#             qa_name = 'Unassigned'
        
#         if not qa_name or qa_name.strip() == '':
#             qa_name = 'Unassigned'
        
#         # Keep Assigned To for reference (optional)
#         assigned_to = fields.get('System.AssignedTo', {})
#         if isinstance(assigned_to, dict):
#             assigned_to_name = assigned_to.get('displayName', 'Unassigned')
#         else:
#             assigned_to_name = 'Unassigned'
        
#         data.append({
#             'ID': wi.get('id'),
#             'Title': fields.get('System.Title', ''),
#             'Type': fields.get('System.WorkItemType', ''),
#             'State': fields.get('System.State', ''),
#             'Story Points': story_points,
#             'QA Hours': calculate_qa_hours(story_points),
#             'Tested By': qa_name,  # CHANGE: New column using TestedBy field
#             'Assigned To': assigned_to_name  # Optional reference
#         })
    
#     return pd.DataFrame(data)
def process_work_items(work_items: List[Dict]) -> pd.DataFrame:
    '''Convert Azure DevOps work items to structured data'''
    data = []
    qa_field_reference = st.session_state.get('qa_field_reference', '')
    
    for wi in work_items:
        fields = wi.get('fields', {})
        
        story_points = fields.get('Microsoft.VSTS.Scheduling.StoryPoints')
        if story_points is None or story_points == '':
            story_points = 0
        else:
            try:
                story_points = int(story_points)
            except (ValueError, TypeError):
                story_points = 0
        
        # ✅ CHANGE 3: Use extract_qa_owner with user-provided field reference
        qa_name = extract_qa_owner(wi, qa_field_reference)
        
        # Keep Assigned To for reference (optional)
        assigned_to = fields.get('System.AssignedTo', {})
        if isinstance(assigned_to, dict):
            assigned_to_name = assigned_to.get('displayName', 'Unassigned')
        else:
            assigned_to_name = 'Unassigned'
        
        data.append({
            'ID': wi.get('id'),
            'Title': fields.get('System.Title', ''),
            'Type': fields.get('System.WorkItemType', ''),
            'State': fields.get('System.State', ''),
            'Story Points': story_points,
            'QA Hours': calculate_qa_hours(story_points),
            'QA Owner': qa_name,  # ✅ Universal column name
            'Assigned To': assigned_to_name
        })
    
    return pd.DataFrame(data)

# def update_qa_assigned_hours(qa_members: List[Dict], work_items_df: pd.DataFrame) -> List[Dict]:
#     """
#     Automatically update assigned hours for each QA member based on work items
#     """
#     # Calculate assigned hours from work items
#     assigned_hours = work_items_df[work_items_df['Assigned QA'] != 'Unassigned'].groupby('Assigned QA')['QA Hours'].sum().to_dict()
    
#     # Update QA members
#     for qa in qa_members:
#         qa['assigned_hours'] = assigned_hours.get(qa['name'], 0)
    
#     return qa_members

def update_qa_assigned_hours(qa_members: List[Dict], work_items_df: pd.DataFrame) -> List[Dict]:
    '''Automatically update assigned hours for each QA member based on work items'''
    assigned_hours = work_items_df[work_items_df['QA Owner'] != 'Unassigned'].groupby('QA Owner')['QA Hours'].sum().to_dict()
    
    for qa in qa_members:
        qa['assigned_hours'] = assigned_hours.get(qa['name'], 0)
    
    return qa_members

def calculate_capacity(qa_members: List[Dict], sprint_days: int, daily_capacity: int) -> pd.DataFrame:
    """
    Calculate capacity for each QA member
    
    Logic:
    - Available Hours = Sprint Days × Daily Capacity
    - Adjusted Capacity = Available - Leave - Support
    - Remaining Capacity = Adjusted - Assigned
    - Risk based on remaining capacity
    """
    total_capacity = sprint_days * daily_capacity
    capacity_data = []
    
    for qa in qa_members:
        available = total_capacity
        leave = qa.get('leave_hours', 0)
        support = qa.get('support_hours', 0)
        assigned = qa.get('assigned_hours', 0)
        
        adjusted = available - leave - support
        remaining = adjusted - assigned
        utilization = (assigned / adjusted * 100) if adjusted > 0 else 0
        
        # Risk assessment (clear logic)
        if remaining < RISK_HIGH_THRESHOLD:
            risk = "🔴 Overallocated"
            risk_reason = f"Assigned hours exceed capacity by {abs(remaining)} hours"
        elif remaining < RISK_MEDIUM_THRESHOLD:
            risk = "🟡 Tight Buffer"
            risk_reason = f"Only {remaining} hours remaining"
        else:
            risk = "🟢 Healthy"
            risk_reason = f"{remaining} hours buffer available"
        
        capacity_data.append({
            'QA Name': qa['name'],
            'Available Hours': available,
            'Leave Hours': leave,
            'Support Hours': support,
            'Adjusted Capacity': adjusted,
            'Assigned Hours': assigned,
            'Remaining Hours': remaining,
            'Utilization %': round(utilization, 1),
            'Risk Status': risk,
            'Risk Reason': risk_reason
        })
    
    return pd.DataFrame(capacity_data)

# ============================================================================
# VISUALIZATION (Simple & Clear)
# ============================================================================

def create_capacity_chart(capacity_df: pd.DataFrame):
    """Simple bar chart showing capacity breakdown"""
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Assigned',
        x=capacity_df['QA Name'],
        y=capacity_df['Assigned Hours'],
        marker_color='#667eea'
    ))
    
    fig.add_trace(go.Bar(
        name='Remaining',
        x=capacity_df['QA Name'],
        y=capacity_df['Remaining Hours'],
        marker_color='#48bb78'
    ))
    
    fig.update_layout(
        title='QA Workload Overview',
        xaxis_title='QA Members',
        yaxis_title='Hours',
        barmode='stack',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'},
        height=400
    )
    
    return fig

def create_risk_summary(capacity_df: pd.DataFrame):
    """Simple pie chart showing risk distribution"""
    risk_counts = capacity_df['Risk Status'].value_counts()
    
    colors = {
        '🔴 Overallocated': '#fc4a1a',
        '🟡 Tight Buffer': '#f7b733',
        '🟢 Healthy': '#48bb78'
    }
    
    fig = go.Figure(data=[go.Pie(
        labels=risk_counts.index,
        values=risk_counts.values,
        marker_colors=[colors.get(label, '#667eea') for label in risk_counts.index],
        hole=0.4
    )])
    
    fig.update_layout(
        title='Team Capacity Risk Status',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'},
        height=350
    )
    
    return fig

# ============================================================================
# VISUALIZATION (Beautiful & Professional)
# ============================================================================

def create_capacity_chart(capacity_df: pd.DataFrame):
    """Stacked bar chart showing capacity breakdown"""
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Assigned',
        x=capacity_df['QA Name'],
        y=capacity_df['Assigned Hours'],
        marker_color='#667eea'
    ))
    
    fig.add_trace(go.Bar(
        name='Remaining',
        x=capacity_df['QA Name'],
        y=capacity_df['Remaining Hours'],
        marker_color='#48bb78'
    ))
    
    fig.update_layout(
        title={
            'text': 'QA Workload Overview',
            'font': {'size': 20, 'color': 'white', 'family': 'Inter'}
        },
        xaxis_title='QA Members',
        yaxis_title='Hours',
        barmode='stack',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'},
        height=400,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font={'color': 'white'}
        ),
        xaxis={'gridcolor': 'rgba(255,255,255,0.1)'},
        yaxis={'gridcolor': 'rgba(255,255,255,0.1)'}
    )
    
    return fig

def create_risk_summary(capacity_df: pd.DataFrame):
    """Donut chart showing risk distribution"""
    risk_counts = capacity_df['Risk Status'].value_counts()
    
    colors_map = {
        '🔴 Overallocated': '#fc4a1a',
        '🟡 Tight Buffer': '#f7b733',
        '🟢 Healthy': '#48bb78'
    }
    
    colors = [colors_map.get(label, '#667eea') for label in risk_counts.index]
    
    fig = go.Figure(data=[go.Pie(
        labels=risk_counts.index,
        values=risk_counts.values,
        marker_colors=colors,
        hole=0.4,
        textposition='inside',
        textinfo='label+percent',
        textfont={'size': 14, 'color': 'white'},
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
    )])
    
    fig.update_layout(
        title={
            'text': 'Team Capacity Risk Status',
            'font': {'size': 20, 'color': 'white', 'family': 'Inter'}
        },
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'},
        height=400,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.1,
            xanchor="center",
            x=0.5,
            font={'color': 'white'}
        )
    )
    
    return fig

def create_utilization_gauge(capacity_df: pd.DataFrame):
    """Gauge chart for team utilization"""
    avg_utilization = capacity_df['Utilization %'].mean()
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=avg_utilization,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Team Utilization", 'font': {'size': 24, 'color': 'white'}},
        delta={'reference': 80, 'increasing': {'color': "#fc4a1a"}, 'decreasing': {'color': '#48bb78'}},
        number={'font': {'size': 48, 'color': 'white'}, 'suffix': '%'},
        gauge={
            'axis': {'range': [None, 100], 'tickwidth': 2, 'tickcolor': "white"},
            'bar': {'color': "#667eea", 'thickness': 0.75},
            'bgcolor': "rgba(255,255,255,0.1)",
            'borderwidth': 2,
            'bordercolor': "white",
            'steps': [
                {'range': [0, 50], 'color': 'rgba(72, 187, 120, 0.3)'},
                {'range': [50, 75], 'color': 'rgba(79, 172, 254, 0.3)'},
                {'range': [75, 90], 'color': 'rgba(249, 151, 0, 0.3)'},
                {'range': [90, 100], 'color': 'rgba(252, 74, 26, 0.3)'}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 4},
                'thickness': 0.75,
                'value': 85
            }
        }
    ))
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white', 'family': 'Inter'},
        height=350
    )
    
    return fig

def create_capacity_heatmap(capacity_df: pd.DataFrame):
    """Heatmap showing capacity metrics"""
    metrics = ['Assigned Hours', 'Leave Hours', 'Support Hours', 'Remaining Hours']
    qa_members = capacity_df['QA Name'].tolist()
    
    z_data = []
    for metric in metrics:
        z_data.append(capacity_df[metric].tolist())
    
    fig = go.Figure(data=go.Heatmap(
        z=z_data,
        x=qa_members,
        y=metrics,
        colorscale=[
            [0, '#0f0c29'],
            [0.5, '#667eea'],
            [1, '#f7b733']
        ],
        text=z_data,
        texttemplate='%{text} hrs',
        textfont={"size": 12, "color": "white"},
        hoverongaps=False,
        colorbar=dict(
            title=dict(text="Hours", side="right"),
            tickmode="linear",
            tick0=0,
            dtick=10
        )
    ))
    
    fig.update_layout(
        title={
            'text': "Team Capacity Heatmap",
            'font': {'size': 20, 'color': 'white', 'family': 'Inter'}
        },
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'},
        height=400,
        xaxis={'side': 'bottom'},
        yaxis={'side': 'left'}
    )
    
    return fig

def create_workload_distribution(work_items_df: pd.DataFrame):
    """Sunburst chart for work distribution"""
    # Create hierarchical data
    total_hours = work_items_df['QA Hours'].sum()
    
    labels = ["Total"]
    parents = [""]
    values = [total_hours]
    colors = ['#667eea']
    
    # Group by Type for simpler, clearer visualization
    type_groups = work_items_df.groupby('Type')['QA Hours'].sum().to_dict()
    for work_type, hours in type_groups.items():
        labels.append(work_type)
        parents.append("Total")
        values.append(hours)
        colors.append('#764ba2')
    
    # Add individual items
    for _, row in work_items_df.iterrows():
        labels.append(f"{row['Type'][:3]}-{row['ID']}")
        parents.append(row['Type'])
        values.append(row['QA Hours'])
        colors.append('#4facfe')
    
    fig = go.Figure(go.Sunburst(
        labels=labels,
        parents=parents,
        values=values,
        branchvalues="total",
        marker=dict(
            colors=colors,
            line=dict(color='white', width=2)
        ),
        hovertemplate='<b>%{label}</b><br>Hours: %{value}<br><extra></extra>',
        textfont=dict(size=14, color='white')
    ))
    
    fig.update_layout(
        title={
            'text': "Work Distribution by Type",
            'font': {'size': 20, 'color': 'white', 'family': 'Inter'}
        },
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'},
        height=450
    )
    
    return fig

def create_capacity_waterfall(capacity_df: pd.DataFrame):
    """Waterfall chart showing capacity breakdown for first QA"""
    if len(capacity_df) == 0:
        return go.Figure()
    
    qa_member = capacity_df.iloc[0]['QA Name']
    
    fig = go.Figure(go.Waterfall(
        name="Capacity Breakdown",
        orientation="v",
        measure=["absolute", "relative", "relative", "relative", "total"],
        x=["Available<br>Hours", "Leave<br>Hours", "Support<br>Hours", "Assigned<br>Hours", "Remaining<br>Capacity"],
        textposition="outside",
        text=[f"{capacity_df.iloc[0]['Available Hours']}", 
              f"-{capacity_df.iloc[0]['Leave Hours']}", 
              f"-{capacity_df.iloc[0]['Support Hours']}",
              f"-{capacity_df.iloc[0]['Assigned Hours']}",
              f"{capacity_df.iloc[0]['Remaining Hours']}"],
        y=[capacity_df.iloc[0]['Available Hours'], 
           -capacity_df.iloc[0]['Leave Hours'], 
           -capacity_df.iloc[0]['Support Hours'],
           -capacity_df.iloc[0]['Assigned Hours'],
           capacity_df.iloc[0]['Remaining Hours']],
        connector={"line": {"color": "rgba(255,255,255,0.3)"}},
        decreasing={"marker": {"color": "#fc4a1a"}},
        increasing={"marker": {"color": "#4facfe"}},
        totals={"marker": {"color": "#667eea"}},
        textfont={"color": "white", "size": 14}
    ))
    
    fig.update_layout(
        title={
            'text': f"Capacity Breakdown: {qa_member}",
            'font': {'size': 20, 'color': 'white', 'family': 'Inter'}
        },
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'},
        height=400,
        showlegend=False,
        xaxis={'gridcolor': 'rgba(255,255,255,0.1)'},
        yaxis={'gridcolor': 'rgba(255,255,255,0.1)', 'title': 'Hours'}
    )
    
    return fig

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    # CHANGE: Initialize session state for sidebar visibility
    if 'sidebar_open' not in st.session_state:
        st.session_state.sidebar_open = True
    
    # Header with logo and connection status
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("""
            <h1 style='text-align: left; margin-bottom: 5px;'>
                <span style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                            font-size: 48px; font-weight: 800;'>
                    🎯 QA Capacity Intelligence Platform
                </span>
            </h1>
            <p style='color: rgba(255,255,255,0.7); font-size: 18px; margin-top: -10px; font-weight: 500;'>
                AI-Powered Sprint Capacity Management & Risk Analytics
            </p>
        """, unsafe_allow_html=True)
    
    with col2:
        # CHANGE: Show Azure connection status
        if st.session_state.get('azure_connected', False):
            st.success("✅ Connected to Azure DevOps")
            if 'last_sync_time' in st.session_state:
                st.caption(f"Last sync: {st.session_state.last_sync_time}")
        else:
            st.warning("⚠️ Using demo data")
        
        # CHANGE: Sidebar toggle button
        if st.button("☰ Settings", use_container_width=True, help="Open/close sidebar"):
            st.info("👈 Look at the sidebar on the left (or click the **>** arrow at top-left)")
    
    st.divider()
    
    # Sidebar Configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Add instruction to reopen sidebar
        st.markdown("""
        <div style='background: rgba(102, 126, 234, 0.2); padding: 10px; border-radius: 8px; margin-bottom: 15px;'>
        <small>💡 <b>Tip:</b> Click the <b>&gt;</b> arrow at top-left to reopen this sidebar anytime</small>
        </div>
        """, unsafe_allow_html=True)
        
        st.subheader("🔗 Azure DevOps Connection")
        
        # CHANGE: Wrap Azure DevOps inputs in a form for proper submission
        with st.form("azure_devops_form"):
            # Clear instructions
            with st.expander("📖 How to get Azure DevOps credentials", expanded=False):
                st.markdown("""
                **Step 1: Organization & Project**
                - Organization: The name in your Azure DevOps URL
                  - Example: `dev.azure.com/YOUR-ORG`
                - Project: Your project name
                
                **Step 2: Create Personal Access Token (PAT)**
                1. Go to Azure DevOps
                2. Click User Settings (top right) → Personal Access Tokens
                3. Click "+ New Token"
                4. Name: "QA Capacity Planner"
                5. **Scopes: Select "Work Items" → Check "Read"** ✅
                6. Click "Create"
                7. **Copy the token immediately** (you won't see it again!)
                8. Paste it below
                """)
            
            st.warning("⚠️ Your PAT is sensitive - keep it secure")
            
            organization = st.text_input(
                "Organization Name", 
                value=st.session_state.get('azure_org', ''),
                placeholder="your-organization",
                help="Example: If your URL is dev.azure.com/mycompany, enter 'mycompany'"
            )
            
            project = st.text_input(
                "Project Name", 
                value=st.session_state.get('azure_project', ''),
                placeholder="your-project",
                help="Your Azure DevOps project name"
            )
            
            pat = st.text_input(
                "Personal Access Token (PAT)", 
                type="password",
                placeholder="Paste your PAT here",
                help="Must have 'Work Items (Read)' permission"
            )
            
            # CHANGE: Add Test Connection button inside form
            test_connection = st.form_submit_button("🔐 Test Connection", use_container_width=True, type="primary")
        
        # CHANGE: Handle connection test
        if test_connection:
            if not organization or not project or not pat:
                st.error("❌ Please fill in all fields")
            else:
                with st.spinner("Testing connection to Azure DevOps..."):
                    try:
                        # Lightweight test: fetch sprints
                        client = AzureDevOpsClient(organization, project, pat)
                        sprints = client.get_sprints()
                        
                        if sprints:
                            # Store credentials and connection status
                            st.session_state.azure_org = organization
                            st.session_state.azure_project = project
                            st.session_state.azure_pat = pat
                            st.session_state.azure_connected = True
                            st.session_state.azure_sprints = sprints
                            
                            st.success(f"✅ Connected successfully! Found {len(sprints)} sprints")
                        else:
                            st.warning("⚠️ Connected but no sprints found")
                            st.session_state.azure_connected = False
                            
                    except requests.exceptions.HTTPError as e:
                        st.session_state.azure_connected = False
                        if e.response.status_code == 401:
                            st.error("❌ Authentication failed - Invalid PAT or insufficient permissions")
                            st.info("💡 Make sure your PAT has 'Work Items (Read)' scope enabled")
                        elif e.response.status_code == 404:
                            st.error("❌ Organization or Project not found")
                            st.info("💡 Double-check your organization and project names")
                        else:
                            st.error(f"❌ Connection failed: {e.response.status_code}")
                    except Exception as e:
                        st.session_state.azure_connected = False
                        st.error(f"❌ Connection error: {str(e)}")
        
        # Show current connection status
        if st.session_state.get('azure_connected', False):
            st.success(f"✅ Connected to: {st.session_state.get('azure_org')}/{st.session_state.get('azure_project')}")
        
        st.divider()

        st.subheader("🎯 Data Filters (Optional)")
        st.markdown("*Advanced options to scope data. Leave empty to fetch all.*")

        # CHANGE: Optional AreaPath filter (Problem 2)
        area_path_input = st.text_input(
        "Area Path Filter (Advanced)",
        value=st.session_state.get('area_path_filter', ''),
        placeholder="e.g., MyCompany\\Engineering\\QA",
        help="Leave empty to include all areas. Advanced users can scope to team area."
        )
        st.session_state.area_path_filter = area_path_input

        # CHANGE: QA Team definition (Problem 3)
        qa_team_input = st.text_input(
            "QA Team Names (Comma-separated)",
            value=st.session_state.get('qa_team_filter', ''),
            placeholder="e.g., Sarah, Ahmed, Mike",
            help="Define your QA team. Only items where QA Owner = these names will be included."  # CHANGE
        )
        st.session_state.qa_team_filter = qa_team_input

        if qa_team_input:
            qa_list = [name.strip() for name in qa_team_input.split(',') if name.strip()]
            st.caption(f"✓ Will filter to: {', '.join(qa_list)}")

        st.divider()

        st.subheader("🎯 QA Field Configuration")
        st.markdown("*Select which Azure DevOps field contains QA tester names*")
        
        # ✅ Step 1: Check if we can fetch fields
        if st.session_state.get('azure_connected', False):
            try:
                organization = st.session_state.get('azure_org', '')
                project = st.session_state.get('azure_project', '')
                pat = st.session_state.get('azure_pat', '')
                
                # Fetch fields from Azure
                client = AzureDevOpsClient(organization, project, pat)
                
                # Check if we already have fields cached
                if 'azure_fields_cache' not in st.session_state:
                    with st.spinner("🔄 Detecting custom fields from Azure DevOps..."):
                        all_fields = client.get_custom_fields()
                        if all_fields:
                            st.session_state.azure_fields_cache = all_fields
                            st.success(f"✅ Found {len(all_fields)} custom/QA-related fields")
                        else:
                            st.warning("⚠️ No custom fields detected. Manual entry required.")
                            st.session_state.azure_fields_cache = []
                
                # ✅ Step 2: Build dropdown options
                cached_fields = st.session_state.get('azure_fields_cache', [])
                
                if cached_fields:
                    # Sort by name for better UX
                    field_options = sorted([
                        {
                            'name': f['name'],
                            'reference': f['referenceName'],
                            'custom': f.get('custom', False)
                        }
                        for f in cached_fields
                    ], key=lambda x: x['name'])
                    
                    # Create display labels
                    field_labels = [
                        f"{f['name']} ({f['reference']})" + (" [Custom]" if f['custom'] else " [System]")
                        for f in field_options
                    ]
                    
                    # ✅ Step 3: Dropdown selector
                    selected_label = st.selectbox(
                        "Select QA Field",
                        options=[''] + field_labels,
                        index=0,
                        help="Choose the field that contains QA tester names. "
                             "Look for fields like 'QA Owner', 'Tester', etc."
                    )
                    
                    if selected_label:
                        # Extract reference name from selection
                        selected_field = next(
                            (f for f, label in zip(field_options, field_labels) if label == selected_label),
                            None
                        )
                        if selected_field:
                            qa_field_ref = selected_field['reference']
                            st.session_state.qa_field_reference = qa_field_ref
                            
                            st.success(f"✓ Selected: {selected_field['name']}")
                            st.caption(f"Reference: `{qa_field_ref}`")
                    else:
                        st.info("👆 Select a field above or enter manually below")
                
                # ✅ Step 4: Manual entry fallback
                st.markdown("---")
                st.markdown("**Or enter manually:**")
                manual_field = st.text_input(
                    "Custom Field Reference (if not in list above)",
                    value=st.session_state.get('qa_field_reference', ''),
                    placeholder="e.g., Custom.QATestedBy",
                    help="Enter the exact field reference name if it's not in the dropdown above."
                )
                
                if manual_field and manual_field.strip():
                    st.session_state.qa_field_reference = manual_field.strip()
                    st.info(f"✓ Using manual field: {manual_field.strip()}")
                
                # ✅ Step 5: Show current status
                current_field = st.session_state.get('qa_field_reference', '')
                if current_field:
                    st.markdown(f"**Currently configured:** `{current_field}`")
                else:
                    st.warning("⚠️ No QA field configured - QA owners will show as 'Unassigned'")
                    
            except Exception as e:
                st.error(f"⚠️ Could not auto-detect fields: {str(e)}")
                st.markdown("**Enter field reference manually:**")
                manual_field = st.text_input(
                    "Custom Field Reference",
                    value=st.session_state.get('qa_field_reference', ''),
                    placeholder="e.g., Custom.QATestedBy"
                )
                if manual_field:
                    st.session_state.qa_field_reference = manual_field.strip()
        
        else:
            st.warning("⚠️ Connect to Azure DevOps first to auto-detect fields")
            manual_field = st.text_input(
                "Custom Field Reference (Manual Entry)",
                value=st.session_state.get('qa_field_reference', ''),
                placeholder="e.g., Custom.QATestedBy"
            )
            if manual_field:
                st.session_state.qa_field_reference = manual_field.strip()

        st.divider()
        
        st.subheader("Sprint Assumptions")
        st.markdown("*These defaults can be edited*")
        sprint_days = st.number_input("Sprint Length (days)", value=DEFAULT_SPRINT_DAYS, min_value=1, max_value=30)
        daily_capacity = st.number_input("QA Hours per Day", value=DEFAULT_DAILY_CAPACITY, min_value=1, max_value=12)
        
        total_per_qa = sprint_days * daily_capacity
        st.info(f"**Capacity per QA:** {total_per_qa} hours per sprint")
        
        st.divider()
        
        # Editable QA hours mapping
        st.subheader("📋 Story Points → QA Hours")
        st.markdown("*Edit this mapping to match your team's estimation*")
        
        # Convert mapping to dataframe for editing
        mapping_df = pd.DataFrame(list(QA_HOURS_MAPPING.items()), 
                                 columns=['Story Points', 'QA Hours'])
        
        edited_mapping = st.data_editor(
            mapping_df,
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic"
        )
        
        # Update global mapping from edited values
        if edited_mapping is not None and len(edited_mapping) > 0:
            new_mapping = {}
            for _, row in edited_mapping.iterrows():
                try:
                    sp = int(row['Story Points'])
                    hours = int(row['QA Hours'])
                    if sp > 0 and hours > 0:
                        new_mapping[sp] = hours
                except (ValueError, TypeError):
                    continue
            
            # Update session state mapping
            if 'qa_hours_mapping' not in st.session_state:
                st.session_state.qa_hours_mapping = QA_HOURS_MAPPING.copy()
            st.session_state.qa_hours_mapping.update(new_mapping)
    
    # Initialize session state for demo data
    # if 'work_items_df' not in st.session_state:
    #     st.session_state.work_items_df = pd.DataFrame({
    #         'ID': [42540, 42541, 42542, 42543, 42544],
    #         'Title': ['User login flow', 'API integration', 'UI redesign', 'Bug fix - crash', 'Data export'],
    #         'Type': ['User Story', 'User Story', 'User Story', 'Bug', 'User Story'],
    #         'State': ['New', 'In Progress', 'New', 'New', 'In Progress'],
    #         'Story Points': [5, 8, 3, 2, 5],
    #         'QA Hours': [7, 10, 5, 3, 7],
    #         'Assigned QA': ['Sarah', 'Sarah', 'Ahmed', 'Unassigned', 'Ahmed']
    #     })
    if 'work_items_df' not in st.session_state:
        st.session_state.work_items_df = pd.DataFrame({
            'ID': [42540, 42541, 42542, 42543, 42544],
            'Title': ['User login flow', 'API integration', 'UI redesign', 'Bug fix - crash', 'Data export'],
            'Type': ['User Story', 'User Story', 'User Story', 'Bug', 'User Story'],
            'State': ['New', 'In Progress', 'New', 'New', 'In Progress'],
            'Story Points': [5, 8, 3, 2, 5],
            'QA Hours': [7, 10, 5, 3, 7],
            'QA Owner': ['Sarah', 'Sarah', 'Ahmed', 'Unassigned', 'Ahmed'],
            'Assigned To': ['Dev1', 'Dev2', 'Dev3', 'Dev4', 'Dev5']
        })

    
    if 'qa_members' not in st.session_state:
        st.session_state.qa_members = [
            {'name': 'Sarah', 'leave_hours': 14, 'support_hours': 0, 'assigned_hours': 17},
            {'name': 'Ahmed', 'leave_hours': 0, 'support_hours': 7, 'assigned_hours': 10},
            {'name': 'Mike', 'leave_hours': 7, 'support_hours': 0, 'assigned_hours': 20}
        ]
    
    # Main Tabs
    tab1, tab2, tab3 = st.tabs(["📊 Capacity Overview", "📋 Sprint Backlog", "👥 Team Setup"])
    
    # ========================================================================
    # TAB 1: CAPACITY OVERVIEW (Most Important)
    # ========================================================================
    with tab1:
        st.header("Sprint Capacity Overview")
        
        # Calculate capacity
        capacity_df = calculate_capacity(st.session_state.qa_members, sprint_days, daily_capacity)
        work_items_df = st.session_state.work_items_df
        
        # Calculate unassigned hours
        unassigned_items = work_items_df[work_items_df['QA Owner'] == 'Unassigned']  # ✅ CORRECT
        unassigned_hours = unassigned_items['QA Hours'].sum()

        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Work Items", len(work_items_df),
                     delta=f"{len(unassigned_items)} unassigned" if len(unassigned_items) > 0 else None,
                     delta_color="inverse" if len(unassigned_items) > 0 else "off")
        
        with col2:
            total_qa_hours = work_items_df['QA Hours'].sum()
            st.metric("Total QA Hours Needed", f"{total_qa_hours} hrs")
        
        with col3:
            team_capacity = capacity_df['Adjusted Capacity'].sum()
            st.metric("Team Capacity", f"{team_capacity} hrs")
        
        with col4:
            # Buffer calculation includes unassigned work
            buffer = team_capacity - total_qa_hours
            st.metric("Capacity Buffer", f"{buffer} hrs", 
                     delta=f"{buffer} hrs remaining",
                     delta_color="normal" if buffer >= 0 else "inverse")
        
        # Show unassigned warning if exists
        if len(unassigned_items) > 0:
            st.warning(f"⚠️ **{len(unassigned_items)} work items ({unassigned_hours} hours) have no QA owner** - Configure QA field in sidebar")
         
        st.divider()
        
        # Main capacity table (CENTERPIECE)
        st.subheader("📋 QA Capacity Table")
        st.markdown("*This is your sprint planning reference*")
        
        # Display with clean formatting
        display_df = capacity_df[[
            'QA Name', 'Available Hours', 'Leave Hours', 'Support Hours',
            'Adjusted Capacity', 'Assigned Hours', 'Remaining Hours', 
            'Utilization %', 'Risk Status'
        ]]
        
        display_cols = [col for col in work_items_df.columns if col != 'Assigned To']
        st.dataframe(work_items_df[display_cols], use_container_width=True, hide_index=True, height=400)
        
        # Risk explanations
        st.markdown("**Risk Status Explained:**")
        for _, row in capacity_df.iterrows():
            if row['Risk Status'] == '🔴 Overallocated':
                st.error(f"**{row['QA Name']}**: {row['Risk Reason']}")
            elif row['Risk Status'] == '🟡 Tight Buffer':
                st.warning(f"**{row['QA Name']}**: {row['Risk Reason']}")
        
        st.divider()
        
        # CHANGE: Reduce chart overload - show essential charts first
        st.subheader("📊 Key Metrics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.plotly_chart(create_capacity_chart(capacity_df), use_container_width=True)
        
        with col2:
            st.plotly_chart(create_utilization_gauge(capacity_df), use_container_width=True)
        
        col3, col4 = st.columns(2)
        
        with col3:
            st.plotly_chart(create_risk_summary(capacity_df), use_container_width=True)
        
        with col4:
            # Placeholder for key metric or keep empty for balance
            st.info("""
            💡 **Quick Actions**
            - Review capacity table above
            - Check risk alerts
            - Export reports in Sprint Backlog tab
            """)
        
        # CHANGE: Move advanced charts into expander
        with st.expander("📈 Advanced Analytics", expanded=False):
            st.markdown("*Additional visualizations for deeper analysis*")
            
            col5, col6 = st.columns(2)
            
            with col5:
                st.plotly_chart(create_capacity_heatmap(capacity_df), use_container_width=True)
            
            with col6:
                st.plotly_chart(create_workload_distribution(work_items_df), use_container_width=True)
            
            col7, col8 = st.columns(2)
            
            with col7:
                if len(capacity_df) > 0:
                    st.plotly_chart(create_capacity_waterfall(capacity_df), use_container_width=True)
            
            with col8:
                st.info("""
                📊 **Chart Explanations**
                - **Heatmap**: Compare metrics across team
                - **Sunburst**: Work distribution by type
                - **Waterfall**: Capacity breakdown detail
                """)
        
        # Recommendations (rule-based, not AI)
        st.divider()
        st.subheader("💡 Capacity Recommendations")
        
        overallocated = capacity_df[capacity_df['Remaining Hours'] < 0]
        healthy = capacity_df[capacity_df['Remaining Hours'] >= 10]
        
        if not overallocated.empty and not healthy.empty:
            st.info(f"""
            **Suggested Action:** Consider redistributing work  
            - {overallocated.iloc[0]['QA Name']} is overallocated by {abs(overallocated.iloc[0]['Remaining Hours'])} hours
            - {healthy.iloc[0]['QA Name']} has {healthy.iloc[0]['Remaining Hours']} hours available
            - Moving 1-2 items could balance the load
            """)
        elif not overallocated.empty:
            st.warning("""
            **Action Needed:** Team is overcommitted  
            - Consider moving work to next sprint
            - Or negotiate reduced scope for some items
            """)
        else:
            st.success("✅ Team capacity looks healthy for this sprint")
    
    # ========================================================================
    # TAB 2: SPRINT BACKLOG
    # ========================================================================
    with tab2:
        st.header("Sprint Backlog")
        
        # Azure DevOps sync
        if pat and organization and project:
            col1, col2 = st.columns([3, 1])
            with col1:
                sync_button = st.button("🔄 Sync from Azure DevOps", use_container_width=True)
            with col2:
                if st.button("🗑️ Clear PAT", use_container_width=True):
                    st.session_state.pat_cleared = True
                    st.info("PAT cleared from memory")
            
            # if sync_button:
            #     with st.spinner("Fetching sprint data from Azure DevOps..."):
            #         try:
            #             client = AzureDevOpsClient(organization, project, pat)
            #             sprints = client.get_sprints()
                        
            #             if sprints:
            #                 sprint_names = [s['name'] for s in sprints]
            #                 selected_sprint = st.selectbox("Select Sprint", sprint_names)
                            
            #                 if selected_sprint:
            #                     sprint = next((s for s in sprints if s['name'] == selected_sprint), None)
            #                     if sprint:
            #                         work_items = client.get_sprint_work_items(sprint['path'])
            #                         if work_items:
            #                             st.session_state.work_items_df = process_work_items(work_items)
                                        
            #                             # Automatically update assigned hours
            #                             st.session_state.qa_members = update_qa_assigned_hours(
            #                                 st.session_state.qa_members, 
            #                                 st.session_state.work_items_df
            #                             )
                                        
            #                             st.success(f"✅ Synced {len(work_items)} work items and updated QA assignments")
            #                             st.rerun()
            #                         else:
            #                             st.warning("No work items found in this sprint")
            #             else:
            #                 st.error("No sprints found. Please check your Azure DevOps configuration.")
            #         except Exception as e:
            #             st.error(f"Failed to sync: {str(e)}")
            if sync_button:
             with st.spinner("Fetching sprint data from Azure DevOps..."):
                try:
                    # CHANGE: Get optional AreaPath and QA Team filters from session state
                    area_path_filter = st.session_state.get('area_path_filter', '')
                    qa_team_filter = st.session_state.get('qa_team_filter', '')
                    
                    client = AzureDevOpsClient(organization, project, pat)
                    
                    # CHANGE: Call new method that uses @CurrentIteration macro
                    work_items = client.get_current_iteration_work_items(
                        area_path_filter=area_path_filter,
                        qa_team=qa_team_filter
                    )
                    
                    if work_items:
                        # Process work items (existing function)
                        st.session_state.work_items_df = process_work_items(work_items)
                        
                        # CHANGE (PROBLEM 5): Sort by Assigned QA for better readability
                        # st.session_state.work_items_df = st.session_state.work_items_df.sort_values(
                        #     'Assigned QA', 
                        #     ascending=True
                        # ).reset_index(drop=True)

                        st.session_state.work_items_df = st.session_state.work_items_df.sort_values(
                            'QA Owner',  # CHANGE: Sort by Tested By
                            ascending=True
                        ).reset_index(drop=True)
                        
                        # PROBLEM 4 FIX: Recalculate assigned hours for each QA member
                        # This is the CRITICAL step that was missing
                        st.session_state.qa_members = update_qa_assigned_hours(
                            st.session_state.qa_members, 
                            st.session_state.work_items_df
                        )
                        
                        # PROBLEM 3: Apply QA Team filter if defined
                        if qa_team_filter:
                            st.session_state.work_items_df = filter_work_items_by_qa_team(
                                st.session_state.work_items_df,
                                qa_team_filter
                            )
                        
                        item_count = len(st.session_state.work_items_df)
                        st.success(f"✅ Synced {item_count} work items and updated QA assignments")
                        st.rerun()
                    else:
                        st.warning("No work items found in current iteration. Verify sprint is active.")
                except Exception as e:
                    st.error(f"Failed to sync: {str(e)}")
        else:
            st.info("👆 Enter your Azure DevOps credentials in the sidebar to sync sprint data")
        
        # Work items summary
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("User Stories", len(work_items_df[work_items_df['Type'] == 'User Story']))
        with col2:
            st.metric("Bugs", len(work_items_df[work_items_df['Type'] == 'Bug']))
        with col3:
            unassigned_count = len(work_items_df[work_items_df['QA Owner'] == 'Unassigned'])  # CHANGE
            st.metric("Unassigned (No QA Owner)", unassigned_count,  # CHANGE label
                     delta="Needs QA assignment" if unassigned_count > 0 else None,  # CHANGE text
                     delta_color="inverse" if unassigned_count > 0 else "off")
        with col4:
            unassigned_hours = work_items_df[work_items_df['QA Owner'] == 'Unassigned']['QA Hours'].sum()  # CHANGE
            st.metric("Unassigned Hours", f"{unassigned_hours} hrs")
        
        st.divider()
        
        # Highlight unassigned items
        if unassigned_count > 0:
            st.warning(f"⚠️ {unassigned_count} items have no QA owner (QA Owner field is empty) - Assign in Azure DevOps")

        
        # Work items table - ensure text is visible
        st.dataframe(
            work_items_df,
            use_container_width=True,
            hide_index=True,
            height=400
        )
        
        st.divider()
        
        # Export options
        st.subheader("📥 Export Data")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # CSV export
            csv = work_items_df.to_csv(index=False)
            st.download_button(
                label="Download as CSV",
                data=csv,
                file_name=f"sprint_backlog_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            # Excel export with capacity
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                work_items_df.to_excel(writer, sheet_name='Work Items', index=False)
                capacity_df.to_excel(writer, sheet_name='QA Capacity', index=False)
            
            st.download_button(
                label="Download as Excel",
                data=buffer.getvalue(),
                file_name=f"sprint_capacity_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        with col3:
            # Summary report
            report = f"""QA CAPACITY SUMMARY
Sprint Planning Date: {datetime.now().strftime('%Y-%m-%d')}

ASSUMPTIONS:
- Sprint Length: {sprint_days} days
- Daily QA Capacity: {daily_capacity} hours
- Total Capacity per QA: {sprint_days * daily_capacity} hours

WORK ITEMS:
- Total Items: {len(work_items_df)}
- Total QA Hours: {work_items_df['QA Hours'].sum()}

TEAM CAPACITY:
- Total Adjusted Capacity: {capacity_df['Adjusted Capacity'].sum()} hours
- Total Assigned: {capacity_df['Assigned Hours'].sum()} hours
- Remaining Buffer: {capacity_df['Remaining Hours'].sum()} hours

RISK STATUS:
{capacity_df[['QA Name', 'Risk Status', 'Risk Reason']].to_string(index=False)}
"""
            
            st.download_button(
                label="Download Summary Report",
                data=report,
                file_name=f"capacity_summary_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain",
                use_container_width=True
            )
    
    # ========================================================================
    # TAB 3: TEAM SETUP
    # ========================================================================
    with tab3:
        st.header("Team Setup")
        
        st.markdown("**Configure your QA team members and their availability**")
        
        # Current team
        capacity_df = calculate_capacity(st.session_state.qa_members, sprint_days, daily_capacity)
        
        st.subheader("Current Team")
        st.dataframe(
            capacity_df[['QA Name', 'Available Hours', 'Leave Hours', 'Support Hours', 'Adjusted Capacity']],
            use_container_width=True,
            hide_index=True
        )
        
        st.divider()
        
        # Add new QA member
        st.subheader("Add Team Member")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            new_name = st.text_input("Name")
        with col2:
            new_leave = st.number_input("Leave Hours", min_value=0, max_value=total_per_qa, value=0,
                                       help="Cannot exceed total sprint capacity")
        with col3:
            new_support = st.number_input("Support Hours", min_value=0, max_value=total_per_qa, value=0,
                                         help="Cannot exceed total sprint capacity")
        
        if st.button("Add Member"):
            if new_name:
                if new_leave < 0 or new_support < 0:
                    st.error("❌ Leave and Support hours cannot be negative")
                elif new_leave + new_support > total_per_qa:
                    st.error(f"❌ Leave + Support hours cannot exceed total capacity ({total_per_qa} hrs)")
                else:
                    st.session_state.qa_members.append({
                        'name': new_name,
                        'leave_hours': new_leave,
                        'support_hours': new_support,
                        'assigned_hours': 0
                    })
                    st.success(f"✅ Added {new_name} to the team")
                    st.rerun()
            else:
                st.error("❌ Please enter a name")
        
        st.divider()
        
        # Upload leave and support data
        st.subheader("📤 Upload Team Availability (Optional)")
        
        tab_leave, tab_support = st.tabs(["Leave Data", "Support Hours"])
        
        with tab_leave:
            st.markdown("*Upload a CSV with columns: **QA Name, Leave Hours***")
            leave_file = st.file_uploader("Choose Leave CSV file", type=['csv'], key="leave_upload")
            
            if leave_file:
                try:
                    leave_df = pd.read_csv(leave_file)
                    
                    # Validate columns
                    if 'QA Name' not in leave_df.columns or 'Leave Hours' not in leave_df.columns:
                        st.error("❌ CSV must have columns: 'QA Name' and 'Leave Hours'")
                    else:
                        st.dataframe(leave_df, use_container_width=True)
                        
                        if st.button("Import Leave Data", key="import_leave"):
                            # Validate and update
                            errors = []
                            for _, row in leave_df.iterrows():
                                leave_hours = row['Leave Hours']
                                if leave_hours < 0:
                                    errors.append(f"{row['QA Name']}: Negative hours not allowed")
                                elif leave_hours > total_per_qa:
                                    errors.append(f"{row['QA Name']}: Exceeds capacity ({total_per_qa} hrs)")
                            
                            if errors:
                                for error in errors:
                                    st.error(f"❌ {error}")
                            else:
                                for _, row in leave_df.iterrows():
                                    for qa in st.session_state.qa_members:
                                        if qa['name'] == row['QA Name']:
                                            qa['leave_hours'] = int(row['Leave Hours'])
                                st.success("✅ Leave data imported successfully")
                                st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed to read CSV: {str(e)}")
        
        with tab_support:
            st.markdown("*Upload a CSV with columns: **QA Name, Support Hours***")
            support_file = st.file_uploader("Choose Support CSV file", type=['csv'], key="support_upload")
            
            if support_file:
                try:
                    support_df = pd.read_csv(support_file)
                    
                    # Validate columns
                    if 'QA Name' not in support_df.columns or 'Support Hours' not in support_df.columns:
                        st.error("❌ CSV must have columns: 'QA Name' and 'Support Hours'")
                    else:
                        st.dataframe(support_df, use_container_width=True)
                        
                        if st.button("Import Support Data", key="import_support"):
                            # Validate and update
                            errors = []
                            for _, row in support_df.iterrows():
                                support_hours = row['Support Hours']
                                if support_hours < 0:
                                    errors.append(f"{row['QA Name']}: Negative hours not allowed")
                                elif support_hours > total_per_qa:
                                    errors.append(f"{row['QA Name']}: Exceeds capacity ({total_per_qa} hrs)")
                            
                            if errors:
                                for error in errors:
                                    st.error(f"❌ {error}")
                            else:
                                for _, row in support_df.iterrows():
                                    for qa in st.session_state.qa_members:
                                        if qa['name'] == row['QA Name']:
                                            qa['support_hours'] = int(row['Support Hours'])
                                st.success("✅ Support data imported successfully")
                                st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed to read CSV: {str(e)}")
    
    # Footer with assumptions
    st.divider()
    st.markdown("""
    <div class="info-box">
    <strong>About This Tool</strong><br>
    This tool helps QA teams plan sprint capacity without spreadsheets. All calculations are based on configurable assumptions shown in the sidebar.
    Numbers shown here should match your exported reports exactly.
    <br><br>
    <strong>Current Assumptions:</strong> Sprint = {0} days, Daily capacity = {1} hours per QA, Total = {2} hours per QA per sprint
    </div>
    """.format(sprint_days, daily_capacity, sprint_days * daily_capacity), unsafe_allow_html=True)

if __name__ == "__main__":
    main()