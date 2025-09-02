import streamlit as st
from mcp import stdio_client, StdioServerParameters
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from utils.prompts import HOUSING_FORECASTER_PROMPT

# Initialize MCP client using your local MCP server
@st.cache_resource
def get_mcp_client():
    return MCPClient(lambda: stdio_client(
        StdioServerParameters(
            command="uv",
            args=["run", "forecaster/forecast.py"]
        )
    ))

# Initialize Bedrock model
@st.cache_resource
def get_bedrock_model():
    return BedrockModel(
        model_id="us.anthropic.claude-3-5-sonnet-20240620-v1:0",
        region_name="us-east-1",
        temperature=0.2
    )

st.set_page_config(page_title="🏘️ Housing Demand Forecaster", layout="centered")
st.title("🏘️ Malaysian Housing Demand Forecast Tool")
st.markdown("""
Use this tool to forecast housing demand for **any state and district** in Malaysia based on **population** and **household income data**.
""")

state = st.text_input("Enter State Name (e.g., Johor):")
district = st.text_input("Enter District Name (e.g., Muar):")

if st.button("📊 Forecast Housing Demand"):
    if not state or not district:
        st.warning("Please enter both state and district.")
    else:
        with st.spinner("⏳ Running forecast with MCP..."):
            mcp_client = get_mcp_client()
            bedrock_model = get_bedrock_model()

            with mcp_client:
                tools = mcp_client.list_tools_sync()
                agent = Agent(
                    model=bedrock_model,
                    system_prompt=HOUSING_FORECASTER_PROMPT,
                    tools=tools
                )
                prompt = f"Forecast housing demand in the state '{state}' and district '{district}' based on population and household income. Suggest suitable price range for PRIMA housing development."
                response = agent(prompt)
                st.success("✅ Forecast complete.")
                st.markdown("### 🧠 AI Forecast Insight:")
                st.markdown(response)
