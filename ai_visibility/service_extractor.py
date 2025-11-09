import os
import httpx
import tldextract
import json
import re
import time
import asyncio
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = os.getenv("MODEL_FAST", "openai/gpt-4o-mini")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# ✅ Persistent HTTP session = major speed improvement
client = httpx.AsyncClient(timeout=20)

def fix_json(raw_text):
    """Fix model JSON including truncated JSON."""
    if not raw_text:
        return {"error": "Empty response from model"}

    cleaned = raw_text.replace("```json", "").replace("```", "").strip()

    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        cleaned = match.group(0)

    cleaned = cleaned.replace("'", '"')
    cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)

    # Auto close missing brackets
    cleaned += "}" * (cleaned.count("{") - cleaned.count("}"))
    cleaned += "]" * (cleaned.count("[") - cleaned.count("]"))

    try:
        return json.loads(cleaned)
    except:
        return {"error": "JSON parse failed", "raw": cleaned}


# ------------------------------------
# ✅ PHASE 1 — Extract Services (FAST)
# ------------------------------------
async def extract_services_only(url: str):
    start = time.time()

    d = tldextract.extract(url)
    domain = f"{d.domain}.{d.suffix}"

    prompt = f"""
Analyze this business and return ONLY real services.

URL: {url}
Domain: {domain}

Return ONLY JSON:
{{
  "services": [
    {{"name": "string", "description": "string", "confidence": 0.0}}
  ]
}}

Rules:
- No competitors.
- No citations.
- No markdown.
"""

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Return ONLY JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.15,
        "max_tokens": 350
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    r = await client.post(OPENROUTER_URL, headers=headers, json=payload)
    content = r.json()["choices"][0]["message"]["content"]

    services = fix_json(content)

    print(f"[ SERVICES PHASE ] {time.time() - start:.2f} sec")
    return services, domain


# ----------------------------------------------------------
# ✅ PHASE 2 — Fetch Competitors PER SERVICE (RUN PARALLEL)
# ----------------------------------------------------------
async def fetch_competitors_for_service(service_name, domain):
    prompt = f"""
Find real global and domestic competitors for this service:

Service: "{service_name}"
Domain Industry Context: {domain}

Return ONLY JSON:
{{
  "service": "{service_name}",
  "global": [
    {{"name": "string", "domain": "string"}}
  ],
  "domestic": [
    {{"name": "string", "domain": "string", "country": "string"}}
  ]
}}
"""

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 350
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    r = await client.post(OPENROUTER_URL, headers=headers, json=payload)
    content = r.json()["choices"][0]["message"]["content"]
    return fix_json(content)


async def extract_competitors_parallel(services, domain):
    start = time.time()

    tasks = [fetch_competitors_for_service(s["name"], domain) for s in services]
    results = await asyncio.gather(*tasks)

    print(f"[ COMPETITORS PHASE ] {time.time() - start:.2f} sec")
    return results


# ---------------------------------------
# ✅ MAIN FUNCTION — Combined Execution
# ---------------------------------------
async def analyze_website(url: str):
    total_start = time.time()

    services_data, domain = await extract_services_only(url)

    competitors_data = await extract_competitors_parallel(
        services_data.get("services", []),
        domain
    )

    total_time = time.time() - total_start
    print(f"\n[ TOTAL PROCESSING TIME ] {total_time:.2f} sec\n")

    return {
        "site": {"domain": domain},
        "services": services_data.get("services", []),
        "competitors": competitors_data
    }
