from openai import OpenAI


client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio",
)

response = client.chat.completions.create(
    model="local-model",
    messages=[
        {
            "role": "user",
            "content": "Say hello in one sentence.",
        }
    ],
)

print(response.choices[0].message.content)