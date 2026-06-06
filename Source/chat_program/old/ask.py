from ddgs import DDGS
from openai import OpenAI
import trafilatura


MAX_RESULTS = 6
MAX_PAGES_TO_FETCH = 3
MAX_TEXT_PER_SOURCE = 800


client = OpenAI(
    base_url="http://127.0.0.1:1234/v1",
    api_key="lm-studio",
)


def search_web(query):
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=MAX_RESULTS))


def extract_evidence(results):
    evidence = []

    for result in results[:MAX_PAGES_TO_FETCH]:
        title = result.get("title")
        url = result.get("href")

        print(f"Fetching: {title}")

        downloaded = trafilatura.fetch_url(url)

        if downloaded is None:
            print("  Could not download page.")
            continue

        text = trafilatura.extract(downloaded)

        if text is None:
            print("  Could not extract readable text.")
            continue

        evidence.append(
            {
                "title": title,
                "url": url,
                "text": text,
            }
        )

    return evidence


def build_prompt(question, evidence):
    sources_text = ""

    for number, source in enumerate(evidence, start=1):
        sources_text += f"""
Source {number}
Title: {source["title"]}
URL: {source["url"]}
Text:
{source["text"][:MAX_TEXT_PER_SOURCE]}
"""

    return f"""
You are answering a user question using web evidence collected by a Python program.

User question:
{question}

Evidence:
{sources_text}

Instructions:
- Answer only using the evidence above.
- If the evidence does not support an answer, say that the evidence I found is not enough.
- Do not pretend you verified anything that is not supported by the evidence.
- Include a short "Sources" section listing the URLs you used.
"""


def ask_model(question, evidence):
    prompt = build_prompt(question, evidence)

    response = client.chat.completions.create(
        model="local-model",
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    return response.choices[0].message.content


question = input("Ask a question: ")

print()
print("Searching the web...")
results = search_web(question)

if not results:
    print("No search results found.")
else:
    print(f"Found {len(results)} result(s).")
    print()
    print("Extracting evidence...")
    evidence = extract_evidence(results)

    if not evidence:
        print("Could not extract readable evidence from the search results.")
    else:
        print()
        print(f"Extracted evidence from {len(evidence)} page(s).")
        print("Asking local model...")
        print()

        answer = ask_model(question, evidence)

        print("Answer:")
        print(answer)