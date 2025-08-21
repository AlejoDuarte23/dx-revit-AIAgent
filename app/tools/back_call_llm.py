import instructor

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field


load_dotenv()
client = instructor.from_openai(OpenAI())

class SimpleResponse(BaseModel):
    response:str = Field(..., description="Respond to the user. Format your responses nicely")
    
def llm_back_call(assitant_message:str, tool_result: str, conversation_history: list[dict]) -> str:
    conversation_history.append({"role":"assistant", "content":assitant_message})
    conversation_history.append({"role":"user", "content":tool_result})
    
    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=conversation_history,
        response_model=SimpleResponse,
    )
    return response.response