import os
import sys
import json
import boto3
import streamlit as st
from boto3.session import Session
from datetime import timedelta

from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from utils.prompts import HOUSING_FORECASTER_PROMPT

# Force correct AWS profile
os.environ["AWS_PROFILE"] = "agentcore"

@st.cache_resource
def get_agentcore_runtime_config():
    boto_session = Session(profile_name="agentcore")
    region = boto_session.region_name
    credentials = boto_session.get_credentials()

    # Debug: Check session + credentials
    if credentials is None or credentials.access_key is None:
        st.warning("⚠️ No AWS credentials found for profile 'agentcore'")
        print("❌ boto_session.get_credentials() returned None or missing access key")
        sys.exit(1)
    else:
        print(f"✅ AWS profile loaded: {credentials.access_key[:4]}******")
        print(f"✅ Using region: {region}")

    try:
        # Retrieve Agent ARN from SSM
        ssm_client = boto3.client('ssm', region_name=region)
        agent_arn_response = ssm_client.get_parameter(Name='/mcp_server/runtime/agent_arn')
        agent_arn = agent_arn_response['Parameter']['Value']
        print(f"✅ Retrieved Agent ARN: {agent_arn}")

        # Retrieve bearer token from Secrets Manager
        secrets_client = boto3.client('secretsmanager', region_name=region)
        response = secrets_client.get_secret_value(SecretId='mcp_server/cognito/credentials')
        secret_value = response['SecretString']
        parsed_secret = json.loads(secret_value)
        bearer_token = parsed_secret.get('bearer_token')

        if not bearer_token or len(bearer_token) < 20:
            st.warning("⚠️ Bearer token is missing or too short.")
            print("❌ bearer_token is missing or invalid in Secrets Manager")
            sys.exit(1)

        print(f"✅ Bearer token retrieved (length: {len(bearer_token)})")

        # Build MCP URL
        encoded_arn = agent_arn.replace(":", "%3A").replace("/", "%2F")
        mcp_url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
        print(f"🔗 MCP URL: {mcp_url}")

        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json"
        }

        return {
            "region": region,
            "mcp_url": mcp_url,
            "headers": headers
        }

    except Exception as e:
        st.error(f"❌ Failed to load MCP AgentCore runtime config: {e}")
        print(f"❌ Exception during runtime config: {e}")
        sys.exit(1)

# MCP Client using AgentCore endpoint
@st.cache_resource
def get_mcp_client():
    print("get MCP Client")
    config = get_agentcore_runtime_config()
    return MCPClient(lambda: streamablehttp_client(
        config["mcp_url"],
        config["headers"],
        timeout=timedelta(seconds=120),
        terminate_on_close=False
    ))

# Bedrock model setup
@st.cache_resource
def get_bedrock_model():
    print("get Bedrock Model")
    return BedrockModel(
        model_id="us.anthropic.claude-3-5-sonnet-20240620-v1:0",
        region_name="us-east-1",
        temperature=0.2
    )

# --- Streamlit UI ---
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
        with st.spinner("⏳ Running forecast using MCP AgentCore..."):
            mcp_client = get_mcp_client()
            bedrock_model = get_bedrock_model()

            with mcp_client:
                tools = mcp_client.list_tools_sync()
                agent = Agent(
                    model=bedrock_model,
                    system_prompt=HOUSING_FORECASTER_PROMPT,
                    tools=tools
                )
                prompt = (f"User Input: State = '{state}' and District = '{district}' ")
                response = agent(prompt)
                st.success("✅ Forecast complete.")
                st.markdown("### 🧠 AI Forecast Insight:")
                st.markdown(response)
