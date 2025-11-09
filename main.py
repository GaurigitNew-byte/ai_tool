from fastapi import FastAPI
from ai_visibility import service_extractor
import asyncio
from pydantic import BaseModel
import time
from ai_visibility.extractor2 import extract_services_only
app = FastAPI()

class RequestBody(BaseModel):
    url : str
@app.post("/extract_services/")
async def extract_services_endpoint(data : RequestBody):
    result = await service_extractor.extract_services_only(data.url)
    return result



@app.post("/analyze_website/")
async def analyze_website(url: str):
    start = time.time()

    services_data, domain = await extract_services_only(url)

    print(f"[ TOTAL TIME ] {time.time() - start:.2f}s")

    return {
        "site": {"domain": domain},
        "services": services_data.get("services", []),
    }