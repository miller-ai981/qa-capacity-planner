# QA Sprint Capacity Planner - Complete Code with Charts Syncing Fixed
# Installation: pip install streamlit pandas plotly requests openpyxl

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import requests
import base64
from typing import Dict, List
import io

# ============================================================================
# CONFIGURATION & ASSUMPTIONS
# ============================================================================

DEFAULT_SPRINT_DAYS = 10
DEFAULT_DAILY_CAPACITY = 7
TOTAL_CAPACITY_PER_QA = DEFAULT_SPRINT_DAYS * DEFAULT_DAILY_CAPACITY

QA_HOURS_MAPPING = {
    1: 2, 2: 3, 3: 5, 4: 7, 5: 7, 6: 7, 7: 8, 8: 10, 9: 9, 10: 9
}

RISK_HIGH_THRESHOLD = 0
RISK_MEDIUM_THRESHOLD = 10

st.set_page_config(
    page_title="QA Capacity Planner",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# STYLING
# ============================================================================

# st.markdown("""
# <style>
#     @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
    
#     * { font-family: 'Inter', sans-serif; }
    
#     .stApp { background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%); }
#     .main { background: transparent; }
#     header { background: transparent !important; }
#     [data-testid="stHeader"] { background: transparent !important; display: none !important; }
#     #MainMenu { visibility: hidden; }
#     footer { visibility: hidden; }
    
#     div[data-testid="stMetricValue"] {
#         font-size: 36px; font-weight: 800;
#         background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
#         -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
#     }
#     div[data-testid="stMetricLabel"] { color: rgba(255, 255, 255, 0.9); font-weight: 600; }
#     div[data-testid="stMetricDelta"] { color: #48bb78; font-weight: 600; }
    
#     h1, h2, h3 { color: rgba(255, 255, 255, 0.95); font-weight: 700; }
#     h1 { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
#          -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
#          font-size: 48px; margin-bottom: 10px; }
    
#     .stButton>button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white !important;
#                       border-radius: 12px; padding: 12px 32px; font-weight: 700; border: none; }
#     .stButton>button:hover { transform: translateY(-2px); }
    
#     .stDownloadButton>button { background: rgba(255, 255, 255, 0.1) !important;
#                                border: 1px solid rgba(255, 255, 255, 0.2) !important;
#                                color: white !important; border-radius: 12px; padding: 12px 24px; }
    
#     [data-testid="stSidebar"] { background: linear-gradient(180deg, rgba(15, 12, 41, 0.95) 0%, rgba(48, 43, 99, 0.95) 100%); }
#     [data-testid="stSidebar"] h2 { color: white; font-weight: 700; }
    
#     .stTextInput>div>div>input, .stNumberInput>div>div>input {
#         background: rgba(240, 242, 246, 0.95) !important; border: 1px solid rgba(200, 200, 220, 0.5) !important;
#         color: #1a202c !important; padding: 12px !important;
#     }
    
#     .stTextInput>label, .stNumberInput>label { color: rgba(255, 255, 255, 0.95) !important; font-weight: 600 !important; }
    
#     .stTabs [data-baseweb="tab-list"] { gap: 8px; background: rgba(255, 255, 255, 0.05); padding: 10px; border-radius: 15px; }
#     .stTabs [aria-selected="true"] { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
    
#     .stDataFrame th { color: white !important; background-color: rgba(102, 126, 234, 0.5) !important; }
#     .stDataFrame td { color: #1a202c !important; background-color: rgba(255, 255, 255, 0.95) !important; }
#     [data-testid="stDataFrame"] * { color: #1a202c !important; }
#     [data-testid="stDataFrame"] thead * { color: white !important; }
    
#     .stMarkdown p, .stAlert p { color: rgba(255, 255, 255, 0.95) !important; }
#     label { color: rgba(255, 255, 255, 0.95) !important; }
    
#     .stAlert { background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-radius: 12px; }
    
#     .js-plotly-plot { background: rgba(255, 255, 255, 0.05) !important; border-radius: 15px; padding: 10px; }
    
#     .info-box { background: rgba(255, 255, 255, 0.1); padding: 15px; border-radius: 12px; color: white; }
# </style>
# """, unsafe_allow_html=True)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
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

class AzureDevOpsClient:
    def __init__(self, organization: str, project: str, pat: str):
        self.organization = organization
        self.project = project
        self.base_url = f"https://dev.azure.com/{organization}/{project}/_apis"
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Basic {base64.b64encode(f":{pat}".encode()).decode()}'
        }
    
    def get_sprints(self) -> List[Dict]:
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
            return [f for f in fields if f.get('custom', False) or 'QA' in f.get('name', '') or 'Test' in f.get('name', '')]
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

    def get_current_iteration_work_items(self, area_path_filter: str = None, qa_team: str = None) -> List[Dict]:
        try:
            current_iteration_path = self.get_current_iteration_path()
            wiql_query = {
                "query": """
                    SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State],
                           [System.AreaPath], [System.AssignedTo], [Microsoft.VSTS.Scheduling.StoryPoints]
                    FROM WorkItems
                    WHERE [System.IterationPath] = @CurrentIteration
                      AND [System.WorkItemType] IN ('User Story', 'Bug')
                      AND [System.State] NOT IN ('Closed', 'Done', 'Removed')
                """
            }
            if area_path_filter and area_path_filter.strip():
                wiql_query["query"] += f"\nAND [System.AreaPath] UNDER '{area_path_filter.strip()}'"
            wiql_query["query"] += "\nORDER BY [System.Id]"

            url = f"{self.base_url}/wit/wiql?api-version=7.0"
            response = requests.post(url, headers=self.headers, json=wiql_query)
            response.raise_for_status()

            work_item_refs = response.json().get("workItems", [])
            if not work_item_refs:
                return []

            all_work_items = []
            batch_size = 200

            for i in range(0, len(work_item_refs), batch_size):
                batch = work_item_refs[i:i + batch_size]
                ids = ",".join(str(wi["id"]) for wi in batch)
                details_url = f"{self.base_url}/wit/workitems?ids={ids}&$expand=fields&api-version=7.0"
                details_response = requests.get(details_url, headers=self.headers)
                details_response.raise_for_status()
                all_work_items.extend(details_response.json().get("value", []))

            return all_work_items
        except Exception as e:
            st.error(f"❌ Failed to fetch sprint work items: {str(e)}")
            return []

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def normalize_name(name: str) -> str:
    return name.strip().lower()

def extract_qa_owner(work_item: Dict, qa_field_reference: str) -> str:
    if not qa_field_reference or not qa_field_reference.strip():
        return 'Unassigned'
    fields = work_item.get('fields', {})
    qa_value = fields.get(qa_field_reference)
    if qa_value is None or qa_value == '':
        return 'Unassigned'
    if isinstance(qa_value, dict):
        display_name = qa_value.get('displayName', '')
        return display_name if display_name.strip() else 'Unassigned'
    if isinstance(qa_value, str):
        return qa_value.strip() if qa_value.strip() else 'Unassigned'
    return 'Unassigned'

def filter_work_items_by_qa_team(work_items_df: pd.DataFrame, qa_input: str) -> pd.DataFrame:
    if not qa_input or not qa_input.strip():
        return work_items_df
    qa_names = [normalize_name(n) for n in qa_input.split(',') if n.strip()]
    if not qa_names:
        return work_items_df
    df = work_items_df.copy()
    df['__qa_norm'] = df['QA Owner'].apply(normalize_name)
    filtered_df = df[df['__qa_norm'].isin(qa_names)]
    return filtered_df.drop(columns='__qa_norm')

def calculate_qa_hours(story_points: int) -> int:
    mapping = st.session_state.get('qa_hours_mapping', QA_HOURS_MAPPING)
    if story_points > 10:
        return mapping.get(10, 9)
    return mapping.get(story_points, 0)

def process_work_items(work_items: List[Dict]) -> pd.DataFrame:
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
        qa_name = extract_qa_owner(wi, qa_field_reference)
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
            'QA Owner': qa_name,
            'Assigned To': assigned_to_name
        })
    return pd.DataFrame(data)

def update_qa_assigned_hours(qa_members: List[Dict], work_items_df: pd.DataFrame) -> List[Dict]:
    assigned_hours = work_items_df[work_items_df['QA Owner'] != 'Unassigned'].groupby('QA Owner')['QA Hours'].sum().to_dict()
    for qa in qa_members:
        qa['assigned_hours'] = assigned_hours.get(qa['name'], 0)
    return qa_members

def calculate_capacity(work_items_df: pd.DataFrame, qa_members: List[Dict], sprint_days: int, daily_capacity: int) -> pd.DataFrame:
    """Calculate capacity for each QA member using WORK ITEMS as source of truth"""
    total_capacity = sprint_days * daily_capacity
    capacity_data = []

    assigned_hours_map = (
        work_items_df[work_items_df['QA Owner'] != 'Unassigned']
        .groupby('QA Owner')['QA Hours']
        .sum()
        .to_dict()
    )

    for qa in qa_members:
        qa_name = qa['name']
        available = total_capacity
        leave = qa.get('leave_hours', 0)
        support = qa.get('support_hours', 0)
        assigned = assigned_hours_map.get(qa_name, 0)
        adjusted = available - leave - support
        remaining = adjusted - assigned
        utilization = (assigned / adjusted * 100) if adjusted > 0 else 0

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
            'QA Name': qa_name,
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
# VISUALIZATIONS
# ============================================================================

def create_capacity_chart(capacity_df: pd.DataFrame):
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Assigned', x=capacity_df['QA Name'], y=capacity_df['Assigned Hours'], marker_color='#667eea'))
    fig.add_trace(go.Bar(name='Remaining', x=capacity_df['QA Name'], y=capacity_df['Remaining Hours'], marker_color='#48bb78'))
    fig.update_layout(
        title={'text': 'QA Workload Overview', 'font': {'size': 20, 'color': 'white', 'family': 'Inter'}},
        xaxis_title='QA Members', yaxis_title='Hours', barmode='stack',
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font={'color': 'white'}, height=400,
        showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font={'color': 'white'}),
        xaxis={'gridcolor': 'rgba(255,255,255,0.1)'}, yaxis={'gridcolor': 'rgba(255,255,255,0.1)'}
    )
    return fig

def create_risk_summary(capacity_df: pd.DataFrame):
    risk_counts = capacity_df['Risk Status'].value_counts()
    colors_map = {'🔴 Overallocated': '#fc4a1a', '🟡 Tight Buffer': '#f7b733', '🟢 Healthy': '#48bb78'}
    colors = [colors_map.get(label, '#667eea') for label in risk_counts.index]
    fig = go.Figure(data=[go.Pie(labels=risk_counts.index, values=risk_counts.values, marker_colors=colors, hole=0.4,
        textposition='inside', textinfo='label+percent', textfont={'size': 14, 'color': 'white'},
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>')])
    fig.update_layout(
        title={'text': 'Team Capacity Risk Status', 'font': {'size': 20, 'color': 'white', 'family': 'Inter'}},
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font={'color': 'white'}, height=400,
        showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5, font={'color': 'white'})
    )
    return fig

def create_utilization_gauge(capacity_df: pd.DataFrame):
    avg_utilization = capacity_df['Utilization %'].mean()
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta", value=avg_utilization,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Team Utilization", 'font': {'size': 24, 'color': 'white'}},
        delta={'reference': 80, 'increasing': {'color': "#fc4a1a"}, 'decreasing': {'color': '#48bb78'}},
        number={'font': {'size': 48, 'color': 'white'}, 'suffix': '%'},
        gauge={
            'axis': {'range': [None, 100], 'tickwidth': 2, 'tickcolor': "white"},
            'bar': {'color': "#667eea", 'thickness': 0.75},
            'bgcolor': "rgba(255,255,255,0.1)", 'borderwidth': 2, 'bordercolor': "white",
            'steps': [
                {'range': [0, 50], 'color': 'rgba(72, 187, 120, 0.3)'},
                {'range': [50, 75], 'color': 'rgba(79, 172, 254, 0.3)'},
                {'range': [75, 90], 'color': 'rgba(249, 151, 0, 0.3)'},
                {'range': [90, 100], 'color': 'rgba(252, 74, 26, 0.3)'}
            ],
            'threshold': {'line': {'color': "white", 'width': 4}, 'thickness': 0.75, 'value': 85}
        }
    ))
    fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font={'color': 'white', 'family': 'Inter'}, height=350)
    return fig

def create_capacity_heatmap(capacity_df: pd.DataFrame):
    metrics = ['Assigned Hours', 'Leave Hours', 'Support Hours', 'Remaining Hours']
    qa_members = capacity_df['QA Name'].tolist()
    z_data = [capacity_df[metric].tolist() for metric in metrics]
    fig = go.Figure(data=go.Heatmap(z=z_data, x=qa_members, y=metrics,
        colorscale=[[0, '#0f0c29'], [0.5, '#667eea'], [1, '#f7b733']],
        text=z_data, texttemplate='%{text} hrs', textfont={"size": 12, "color": "white"}, hoverongaps=False,
        colorbar=dict(title=dict(text="Hours", side="right"), tickmode="linear", tick0=0, dtick=10)))
    fig.update_layout(
        title={'text': "Team Capacity Heatmap", 'font': {'size': 20, 'color': 'white', 'family': 'Inter'}},
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font={'color': 'white'}, height=400,
        xaxis={'side': 'bottom'}, yaxis={'side': 'left'}
    )
    return fig

def create_workload_distribution(work_items_df: pd.DataFrame):
    total_hours = work_items_df['QA Hours'].sum()
    labels = ["Total"]
    parents = [""]
    values = [total_hours]
    colors = ['#667eea']
    type_groups = work_items_df.groupby('Type')['QA Hours'].sum().to_dict()
    for work_type, hours in type_groups.items():
        labels.append(work_type)
        parents.append("Total")
        values.append(hours)
        colors.append('#764ba2')
    for _, row in work_items_df.iterrows():
        labels.append(f"{row['Type'][:3]}-{row['ID']}")
        parents.append(row['Type'])
        values.append(row['QA Hours'])
        colors.append('#4facfe')
    fig = go.Figure(go.Sunburst(labels=labels, parents=parents, values=values, branchvalues="total",
        marker=dict(colors=colors, line=dict(color='white', width=2)),
        hovertemplate='<b>%{label}</b><br>Hours: %{value}<br><extra></extra>',
        textfont=dict(size=14, color='white')))
    fig.update_layout(
        title={'text': "Work Distribution by Type", 'font': {'size': 20, 'color': 'white', 'family': 'Inter'}},
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font={'color': 'white'}, height=450
    )
    return fig

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    if 'sidebar_open' not in st.session_state:
        st.session_state.sidebar_open = True
    
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
                Sprint Capacity Management & Risk Analytics
            </p>
        """, unsafe_allow_html=True)
    
    with col2:
        if st.session_state.get('azure_connected', False):
            st.success("✅ Connected to Azure DevOps")
        else:
            st.warning("⚠️ Using demo data")
    
    st.divider()
    
    # Sidebar Configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        st.subheader("🔗 Azure DevOps Connection")
        
        with st.form("azure_devops_form"):
            organization = st.text_input("Organization Name", value=st.session_state.get('azure_org', ''), placeholder="your-organization")
            project = st.text_input("Project Name", value=st.session_state.get('azure_project', ''), placeholder="your-project")
            pat = st.text_input("Personal Access Token (PAT)", type="password", placeholder="Paste your PAT here")
            test_connection = st.form_submit_button("🔐 Test Connection", use_container_width=True, type="primary")
        
        if test_connection:
            if not organization or not project or not pat:
                st.error("❌ Please fill in all fields")
            else:
                with st.spinner("Testing connection to Azure DevOps..."):
                    try:
                        client = AzureDevOpsClient(organization, project, pat)
                        sprints = client.get_sprints()
                        if sprints:
                            st.session_state.azure_org = organization
                            st.session_state.azure_project = project
                            st.session_state.azure_pat = pat
                            st.session_state.azure_connected = True
                            st.success(f"✅ Connected successfully! Found {len(sprints)} sprints")
                        else:
                            st.warning("⚠️ Connected but no sprints found")
                            st.session_state.azure_connected = False
                    except Exception as e:
                        st.session_state.azure_connected = False
                        st.error(f"❌ Connection error: {str(e)}")
        
        st.divider()
        st.subheader("🎯 Data Filters (Optional)")
        area_path_input = st.text_input("Area Path Filter (Advanced)", value=st.session_state.get('area_path_filter', ''))
        st.session_state.area_path_filter = area_path_input

        qa_team_input = st.text_input("QA Team Names (Comma-separated)", value=st.session_state.get('qa_team_filter', ''), placeholder="e.g., Sarah, Ahmed, Mike")
        st.session_state.qa_team_filter = qa_team_input
        if qa_team_input:
            qa_list = [name.strip() for name in qa_team_input.split(',') if name.strip()]
            st.caption(f"✓ Will filter to: {', '.join(qa_list)}")

        st.divider()
        st.subheader("🎯 QA Field Configuration")
        
        if st.session_state.get('azure_connected', False):
            try:
                organization = st.session_state.get('azure_org', '')
                project = st.session_state.get('azure_project', '')
                pat = st.session_state.get('azure_pat', '')
                client = AzureDevOpsClient(organization, project, pat)
                
                if 'azure_fields_cache' not in st.session_state:
                    with st.spinner("🔄 Detecting custom fields from Azure DevOps..."):
                        all_fields = client.get_custom_fields()
                        st.session_state.azure_fields_cache = all_fields if all_fields else []
                
                cached_fields = st.session_state.get('azure_fields_cache', [])
                if cached_fields:
                    field_options = sorted([
                        {'name': f['name'], 'reference': f['referenceName'], 'custom': f.get('custom', False)}
                        for f in cached_fields
                    ], key=lambda x: x['name'])
                    
                    field_labels = [
                        f"{f['name']} ({f['reference']})" + (" [Custom]" if f['custom'] else " [System]")
                        for f in field_options
                    ]
                    
                    selected_label = st.selectbox("Select QA Field", options=[''] + field_labels, index=0)
                    if selected_label:
                        selected_field = next((f for f, label in zip(field_options, field_labels) if label == selected_label), None)
                        if selected_field:
                            st.session_state.qa_field_reference = selected_field['reference']
                            st.success(f"✓ Selected: {selected_field['name']}")
                
                manual_field = st.text_input("Custom Field Reference (if not in list above)", value=st.session_state.get('qa_field_reference', ''), placeholder="e.g., Custom.QATestedBy")
                if manual_field and manual_field.strip():
                    st.session_state.qa_field_reference = manual_field.strip()
            except Exception as e:
                st.error(f"⚠️ Could not auto-detect fields: {str(e)}")
        else:
            st.warning("⚠️ Connect to Azure DevOps first to auto-detect fields")
            manual_field = st.text_input("Custom Field Reference (Manual Entry)", value=st.session_state.get('qa_field_reference', ''), placeholder="e.g., Custom.QATestedBy")
            if manual_field:
                st.session_state.qa_field_reference = manual_field.strip()

        st.divider()
        st.subheader("Sprint Assumptions")
        sprint_days = st.number_input("Sprint Length (days)", value=DEFAULT_SPRINT_DAYS, min_value=1, max_value=30)
        daily_capacity = st.number_input("QA Hours per Day", value=DEFAULT_DAILY_CAPACITY, min_value=1, max_value=12)
        total_per_qa = sprint_days * daily_capacity
        st.info(f"**Capacity per QA:** {total_per_qa} hours per sprint")
        
        st.divider()
        st.subheader("📋 Story Points → QA Hours")
        mapping_df = pd.DataFrame(list(QA_HOURS_MAPPING.items()), columns=['Story Points', 'QA Hours'])
        edited_mapping = st.data_editor(mapping_df, hide_index=True, use_container_width=True, num_rows="dynamic")
        
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
            if 'qa_hours_mapping' not in st.session_state:
                st.session_state.qa_hours_mapping = QA_HOURS_MAPPING.copy()
            st.session_state.qa_hours_mapping.update(new_mapping)
    
    # Initialize session state for demo data
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

    # =====================================================================
    # 🔥 SINGLE SOURCE OF TRUTH - Calculate capacity_df ONCE BEFORE TABS
    # =====================================================================

    raw_work_items_df = st.session_state.work_items_df
    qa_filter = st.session_state.get('qa_team_filter', '').strip()

    if qa_filter:
        qa_list = [name.strip() for name in qa_filter.split(',') if name.strip()]
        filtered_work_items_df = raw_work_items_df[raw_work_items_df['QA Owner'].isin(qa_list)].copy()
    else:
        filtered_work_items_df = raw_work_items_df.copy()

    st.session_state.work_items_df = filtered_work_items_df
    work_items_df = st.session_state.work_items_df

    # 🔥 CRITICAL FIX: Build qa_members from ACTUAL work items (not hardcoded names)
    qa_names_in_work = work_items_df[work_items_df['QA Owner'] != 'Unassigned']['QA Owner'].unique().tolist()
    
    # Start with existing QA members that are in work items
    qa_members_for_capacity = [qa for qa in st.session_state.qa_members if qa['name'] in qa_names_in_work]
    
    # Add any QA names from work items that aren't in the team list yet
    for qa_name in qa_names_in_work:
        if not any(qa['name'] == qa_name for qa in qa_members_for_capacity):
            qa_members_for_capacity.append({
                'name': qa_name,
                'leave_hours': 0,
                'support_hours': 0,
                'assigned_hours': 0
            })
    
    # 🔥 Calculate capacity with DYNAMIC QA names
    capacity_df = calculate_capacity(
        work_items_df,
        qa_members_for_capacity,
        sprint_days,
        daily_capacity
    )

    st.session_state.capacity_df = capacity_df

    # ========================================================================
    # TAB 1: CAPACITY OVERVIEW
    # ========================================================================
    with tab1:
        st.header("Sprint Capacity Overview")
        
        capacity_df = st.session_state.capacity_df
        work_items_df = st.session_state.work_items_df
        
        unassigned_items = work_items_df[work_items_df['QA Owner'] == 'Unassigned']
        unassigned_hours = unassigned_items['QA Hours'].sum()

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
            buffer = team_capacity - total_qa_hours
            st.metric("Capacity Buffer", f"{buffer} hrs", 
                     delta=f"{buffer} hrs remaining",
                     delta_color="normal" if buffer >= 0 else "inverse")
        
        if len(unassigned_items) > 0:
            st.warning(f"⚠️ **{len(unassigned_items)} work items ({unassigned_hours} hours) have no QA owner**")
         
        st.divider()
        
        st.subheader("📋 QA Capacity Table")
        st.dataframe(capacity_df, use_container_width=True, hide_index=True)
        
        st.subheader("📋 Work Items")
        display_cols = [col for col in work_items_df.columns if col != 'Assigned To']
        st.dataframe(work_items_df[display_cols], use_container_width=True, hide_index=True, height=400)
        
        st.markdown("**Risk Status Explained:**")
        for _, row in capacity_df.iterrows():
            if row['Risk Status'] == '🔴 Overallocated':
                st.error(f"**{row['QA Name']}**: {row['Risk Reason']}")
            elif row['Risk Status'] == '🟡 Tight Buffer':
                st.warning(f"**{row['QA Name']}**: {row['Risk Reason']}")
        
        st.divider()
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
            st.info("💡 **Quick Actions**\n- Review capacity table above\n- Check risk alerts\n- Export reports in Sprint Backlog tab")
        
        with st.expander("📈 Advanced Analytics", expanded=False):
            col5, col6 = st.columns(2)
            with col5:
                st.plotly_chart(create_capacity_heatmap(capacity_df), use_container_width=True)
            with col6:
                st.plotly_chart(create_workload_distribution(work_items_df), use_container_width=True)
        
        st.divider()
        st.subheader("💡 Capacity Recommendations")
        overallocated = capacity_df[capacity_df['Remaining Hours'] < 0]
        healthy = capacity_df[capacity_df['Remaining Hours'] >= 10]
        
        if not overallocated.empty and not healthy.empty:
            st.info(f"Consider redistributing work between {overallocated.iloc[0]['QA Name']} and {healthy.iloc[0]['QA Name']}")
        elif not overallocated.empty:
            st.warning("Team is overcommitted - consider moving work to next sprint")
        else:
            st.success("✅ Team capacity looks healthy for this sprint")
    
    # ========================================================================
    # TAB 2: SPRINT BACKLOG
    # ========================================================================
    with tab2:
        st.header("Sprint Backlog")
        
        organization = st.session_state.get('azure_org', '')
        project = st.session_state.get('azure_project', '')
        pat = st.session_state.get('azure_pat', '')
        
        if pat and organization and project:
            col1, col2 = st.columns([3, 1])
            with col1:
                sync_button = st.button("🔄 Sync from Azure DevOps", use_container_width=True)
            
            if sync_button:
                with st.spinner("Fetching sprint data from Azure DevOps..."):
                    try:
                        area_path_filter = st.session_state.get('area_path_filter', '')
                        qa_team_filter = st.session_state.get('qa_team_filter', '')
                        
                        client = AzureDevOpsClient(organization, project, pat)
                        work_items = client.get_current_iteration_work_items(area_path_filter=area_path_filter, qa_team=qa_team_filter)
                        
                        if work_items:
                            st.session_state.work_items_df = process_work_items(work_items)
                            st.session_state.work_items_df = st.session_state.work_items_df.sort_values('QA Owner', ascending=True).reset_index(drop=True)
                            st.session_state.qa_members = update_qa_assigned_hours(st.session_state.qa_members, st.session_state.work_items_df)
                            
                            if qa_team_filter:
                                st.session_state.work_items_df = filter_work_items_by_qa_team(st.session_state.work_items_df, qa_team_filter)
                            
                            # 🔥 CRITICAL: Recalculate capacity_df with newly synced work items
                            synced_work_items_df = st.session_state.work_items_df
                            qa_names_in_work = synced_work_items_df[synced_work_items_df['QA Owner'] != 'Unassigned']['QA Owner'].unique().tolist()
                            qa_members_for_capacity = [qa for qa in st.session_state.qa_members if qa['name'] in qa_names_in_work]
                            
                            for qa_name in qa_names_in_work:
                                if not any(qa['name'] == qa_name for qa in qa_members_for_capacity):
                                    qa_members_for_capacity.append({'name': qa_name, 'leave_hours': 0, 'support_hours': 0, 'assigned_hours': 0})
                            
                            st.session_state.capacity_df = calculate_capacity(synced_work_items_df, qa_members_for_capacity, sprint_days, daily_capacity)
                            
                            st.success(f"✅ Synced {len(st.session_state.work_items_df)} work items")
                            st.rerun()
                        else:
                            st.warning("No work items found in current iteration")
                    except Exception as e:
                        st.error(f"Failed to sync: {str(e)}")
        else:
            st.info("👆 Enter your Azure DevOps credentials in the sidebar to sync sprint data")
        
        work_items_df = st.session_state.work_items_df
        capacity_df = st.session_state.capacity_df
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("User Stories", len(work_items_df[work_items_df['Type'] == 'User Story']))
        with col2:
            st.metric("Bugs", len(work_items_df[work_items_df['Type'] == 'Bug']))
        with col3:
            unassigned_count = len(work_items_df[work_items_df['QA Owner'] == 'Unassigned'])
            st.metric("Unassigned (No QA Owner)", unassigned_count, delta="Needs QA assignment" if unassigned_count > 0 else None)
        with col4:
            unassigned_hours = work_items_df[work_items_df['QA Owner'] == 'Unassigned']['QA Hours'].sum()
            st.metric("Unassigned Hours", f"{unassigned_hours} hrs")
        
        st.divider()
        st.dataframe(work_items_df, use_container_width=True, hide_index=True, height=400)
        
        st.divider()
        st.subheader("📥 Export Data")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            csv = work_items_df.to_csv(index=False)
            st.download_button(label="Download as CSV", data=csv, file_name=f"sprint_backlog_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv", use_container_width=True)
        
        with col2:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                work_items_df.to_excel(writer, sheet_name='Work Items', index=False)
                capacity_df.to_excel(writer, sheet_name='QA Capacity', index=False)
            st.download_button(label="Download as Excel", data=buffer.getvalue(), file_name=f"sprint_capacity_{datetime.now().strftime('%Y%m%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    
    # ========================================================================
    # TAB 3: TEAM SETUP
    # ========================================================================
    with tab3:
        st.header("Team Setup")
        st.markdown("**Configure your QA team members and their availability**")
        
        capacity_df = st.session_state.capacity_df
        st.subheader("Current Team")
        st.dataframe(capacity_df[['QA Name', 'Available Hours', 'Leave Hours', 'Support Hours', 'Adjusted Capacity']], use_container_width=True, hide_index=True)
        
        st.divider()
        st.subheader("Add Team Member")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            new_name = st.text_input("Name")
        with col2:
            new_leave = st.number_input("Leave Hours", min_value=0, max_value=total_per_qa, value=0)
        with col3:
            new_support = st.number_input("Support Hours", min_value=0, max_value=total_per_qa, value=0)
        
        if st.button("Add Member"):
            if new_name:
                st.session_state.qa_members.append({'name': new_name, 'leave_hours': new_leave, 'support_hours': new_support, 'assigned_hours': 0})
                st.success(f"✅ Added {new_name} to the team")
                st.rerun()
            else:
                st.error("❌ Please enter a name")
    
    st.divider()
    st.markdown(f"""
    <div class="info-box">
    <strong>About This Tool</strong><br>
    QA capacity planning made simple. All calculations based on configurable assumptions.
    <br><br>
    <strong>Current Assumptions:</strong> Sprint = {sprint_days} days, Daily capacity = {daily_capacity} hours per QA, Total = {sprint_days * daily_capacity} hours per QA per sprint
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()