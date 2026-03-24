import json
import streamlit as st
from openai import OpenAI
from database import get_memory_rules, add_memory_rule
from pydantic import BaseModel
from typing import List, Optional

# Read from Streamlit secrets
API_KEY = st.secrets.get("OPENAI_API_KEY", "")
class TaskExtraction(BaseModel):
    title: str
    description: Optional[str] = None
    task_type: Optional[str] = None
    tags: List[str] = []
    due_date: Optional[str] = None # format YYYY-MM-DD or None
    needs_clarification: bool = False
    clarification_question: Optional[str] = None

def parse_task(user_input: str) -> dict:
    if not API_KEY:
        raise ValueError("OpenAI API Key is missing. Check .streamlit/secrets.toml")
    
    client = OpenAI(api_key=API_KEY)
    
    rules = get_memory_rules()
    rules_text = "\n".join([f"- {r}" for r in rules]) if rules else "No specific rules yet."
    
    system_prompt = f"""
    You are an AI assistant that extracts task structured data from user input.
    You must classify the task type, return a title, extract any tags, and due dates (YYYY-MM-DD).
    
    Here are the user's custom rules learned from memory:
    {rules_text}
    
    If the user's input is ambiguous or you don't know how to classify it based on the rules,
    set 'needs_clarification' to true and provide a 'clarification_question' asking the user what kind of task it is.
    Otherwise, do your best to extract the fields.
    """
    
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini", # using mini for speed and cost-efficiency
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ],
        response_format=TaskExtraction
    )
    
    return completion.choices[0].message.parsed.model_dump()
