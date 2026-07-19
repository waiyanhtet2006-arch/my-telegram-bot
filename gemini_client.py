import os
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

def get_ai_response(history, system_prompt):
    # Combine system prompt with the history list
    messages = [{"role": "system", "content": system_prompt}] + history

    completion = client.chat.completions.create(
        model="google/gemini-2.5-flash",
        messages=messages,
        temperature=0.8,
        max_tokens=2048,
    )
    return completion.choices[0].message.content
