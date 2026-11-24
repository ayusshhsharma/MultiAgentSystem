from dotenv import load_dotenv
from agents import llm

load_dotenv()

try:
    response = llm.invoke("Reply with only: Groq is working", max_tokens=10)
    print("Groq is working")
except Exception as e:
    print(f"Error checking Groq: {e}")
