from typing import Any, Dict
import httpx
import os
import json
from mcp.server.fastmcp import FastMCP
from urllib.parse import quote
import traceback

# Initialize FastMCP server
mcp = FastMCP("house-forecast",host="0.0.0.0", stateless_http=True)


BASE_URL = "https://api.data.gov.my/data-catalogue"

# API request
async def api_request(url: str) -> dict[str, Any] | None:
    """Make a request to the DOSM Open API with detailed debug logging."""
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; MCP/1.0)"
    }
    async with httpx.AsyncClient(verify=False) as client:  # Note: Only for debugging
        try:
            print(f"[DEBUG] Requesting URL: {url}")
            response = await client.get(url, headers=headers, timeout=30.0, follow_redirects=True)
            response.raise_for_status()

            # Print some content to confirm format
            print("[DEBUG] Response received:")
            print(f"  - Status Code: {response.status_code}")
            print(f"  - Content-Type: {response.headers.get('content-type')}")
            print(f"  - First 300 chars of body: {response.text[:300]}")
            
            return response.json()
        
        except httpx.HTTPStatusError as e:
            print("[ERROR] HTTP status error:")
            print(f"  - Status code: {e.response.status_code}")
            print(f"  - Body: {e.response.text[:300]}")
            print(f"  - Headers: {e.response.headers}")
            print(f"  - URL: {e.request.url}")
        
        except httpx.ConnectError as e:
            print("[ERROR] Connection error:")
            print(f"  - Message: {str(e)}")
            print(f"  - URL: {url}")
        
        except Exception as e:
            print("[ERROR] General Exception:")
            traceback.print_exc()
            print(f"  - URL: {url}")
        
        return {
            "ok": False,
            "message": "API request failed, see logs for more details.",
            "url": url
        }

# MCP tool to fetch population data by state & district
@mcp.tool("population_by_state_and_district")
async def population_by_state_and_district(state: str, district: str) -> str | None:
    """Get population data for a specific state and district.
    Args:
        state (str): The state to query in lowercase.
        district (str): The district to query in lowercase.
    Returns:
        dict[str, Any] | None: Population data or None if not found.
    """
    print(f"[TOOL] Using population_by_state_and_district for state={state}, district={district}")

    state_encoded = quote(state.lower())
    district_encoded = quote(district.lower())
    
    url = f"{BASE_URL}?id=population_district&icontains={state_encoded}@state&icontains={district_encoded}@district"
    #url = f"{BASE_URL}?id=population_district&limit=3" 
    data =  await api_request(url)
    
    if not data:
        return f"No data found for state='{state}', district='{district}'"
    
    items = []
    for x in data:
        item = f"""
        Date: {x['date']}
        Sex: {x['sex']}
        Age: {x['age']}
        Ethnicity: {x['ethnicity']}
        Population: {x['population']}
        """
        items.append(item)
    
    return "\n---\n".join(items)
    
# MCP tool to fetch household income data by state & district
@mcp.tool("household_income_by_state_and_district")
async def household_income_by_state_and_district(state: str, district: str) -> str | None:
    """Get household income data for a specific state and district.
    Args:
        state (str): The state to query in lowercase.
        district (str): The district to query in lowercase.
    Returns:
        dict[str, Any] | None: Household income data or None if not found.
    """
    print(f"[TOOL] Using population_by_state_and_district for state={state}, district={district}")
    
    state_encoded = quote(state.lower())
    district_encoded = quote(district.lower())

    url = f"{BASE_URL}?id=hies_district&icontains={state_encoded}@state&icontains={district_encoded}@district"
    data = await api_request(url)

    if not data:
        return f"No data found for state='{state}', district='{district}'"
    
    items = []
    for x in data:
        item = f"""
        { x['district'] }, { x['state'] }
        Date: { x['date'] }
        Mean Income: RM { x['income_mean'] }
        Median Income: RM { x['income_median'] }
        Mean Expenditure: RM { x['expenditure_mean'] }
        Gini Coefficient: { x['gini'] }
        Poverty Rate: { x['poverty'] }%
        """
        items.append(item)
    
    return "\n---\n".join(items)

# MCP tool to fetch household and living quarters by state & district
@mcp.tool("household_and_living_quarters_by_state")
async def household_income_by_state_and_district(state: str) -> str | None:
    """Get household and living quarters by a specific state.
    Args:
        state (str): The state to query in lowercase.
    Returns:
        str | None: Household and living quarters by state or None if not found.
    """
    print(f"[TOOL] Using household_and_living_quarters_by_state for state={state}")
    
    state_encoded = quote(state.lower())

    url = f"{BASE_URL}?id=hh_profile_state&icontains={state_encoded}@state"
    data = await api_request(url)

    if not data:
        return f"No data found for state='{state}'"
    
    items = []
    for x in data:
        item = f"""
        State: { x['state'] }
        Date: { x['date'] }
        Households { x['households'] }
        Living Quarters { x['living_quarters'] }
        """
        items.append(item)
    
    return "\n---\n".join(items)

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport="streamable-http")