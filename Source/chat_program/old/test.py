from ddgs import DDGS
import trafilatura


MAX_RESULTS = 12
MAX_PAGES_TO_FETCH = 6
PREVIEW_LENGTH = 1000


query = input("Search query: ")

with DDGS() as ddgs:
    results = list(ddgs.text(query, max_results=MAX_RESULTS))

if not results:
    print("No results found.")
else:
    print()
    print("Search results:")

    for number, result in enumerate(results, start=1):
        print()
        print(f"Result {number}")
        print("Title:", result.get("title"))
        print("URL:", result.get("href"))
        print("Summary:", result.get("body"))

    print()
    print("Fetching pages and extracting readable text...")

    evidence = []

    for result in results[:MAX_PAGES_TO_FETCH]:
        title = result.get("title")
        url = result.get("href")

        print()
        print("=" * 60)
        print("Source title:", title)
        print("Source URL:", url)

        downloaded = trafilatura.fetch_url(url)

        if downloaded is None:
            print("Status: could not download this page.")
            continue

        text = trafilatura.extract(downloaded)

        if text is None:
            print("Status: could not extract readable text from this page.")
            continue

        source = {
            "title": title,
            "url": url,            "text": text,
        }

        evidence.append(source)

        print("Status: extracted readable text.")
        print()
        print("Evidence preview:")
        print(source["text"][:PREVIEW_LENGTH])

    print()
    print("=" * 60)
    print(f"Finished. Extracted evidence from {len(evidence)} page(s).")
           