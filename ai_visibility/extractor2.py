# core/services/extract_services.py
import tldextract
import json, re
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from .llm import llm

service_prompt = PromptTemplate.from_template("""
Analyze this business website and return ONLY real offered services.

URL: {url}
Domain Context: {domain}

Return ONLY in JSON:
{{
  "services": [
    {{"name": "string", "description": "string", "confidence": 0.0}}
  ]
}}
""")

service_chain = service_prompt | llm | StrOutputParser()

def _fix_json(raw):
    raw = raw.replace("```json", "").replace("```", "").strip()
    raw = raw.replace("'", '"')
    raw = re.sub(r",(\s*[}\]])", r"\1", raw)
    try:
        return json.loads(raw)
    except:
        return {"error": "json_parse_failed", "raw": raw}

async def extract_services_only(url: str):
    d = tldextract.extract(url)
    domain = f"{d.domain}.{d.suffix}"
    response = await service_chain.ainvoke({"url": url, "domain": domain})
    return _fix_json(response), domain
