import os
import dotenv
from langchain_openai import ChatOpenAI
dotenv.load_dotenv()

llm = ChatOpenAI(
    openai_api_key=os.getenv("OPENROUTER_API_KEY"),
    model=os.getenv("MODEL_FAST"),
    openai_api_base="https://openrouter.ai/api/v1/",
    temperature=0.2,
    max_tokens =1500,
)