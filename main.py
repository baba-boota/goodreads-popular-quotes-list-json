import aiohttp
from bs4 import BeautifulSoup
import json
import asyncio

sem = asyncio.Semaphore(25)

async def fetch_url_data(url, sess):
    for attempt in range(3):
        try:
            res = await sess.get(url)
            data = await res.text()
            print(f"Fetched | {url}")
            return (url, data)
        except Exception as e:
            if attempt == 2:
                print(f"Timed out | {url} | {e}")


async def limited_fetch(url, sess):
    async with sem:
        return await fetch_url_data(url, sess)


def parser(res):

    soup = BeautifulSoup(res, "html.parser")
    div = soup.select("div.quoteText")
    quotes = []

    for item in div:
        quote = ""
        for x in item.descendants:
            if "―" in x.get_text(strip=True):
                break
            if x.name == "br":
                quote += "\n"
            quote += x.get_text(strip=True)
        
        quote = quote.strip().strip("“").strip("”")
        author = item.find("span", class_="authorOrTitle").get_text(strip=True)
        book_tag = item.find("a", class_="authorOrTitle")
        book = book_tag.get_text(strip=True) if book_tag else None

        # if len(quote) > 150:
        #     continue

        quotes.append({
            "quote": quote,
            "author": author.strip(","),
            "book": book if book is not None else None
        })
    return quotes


async def main():
    sess = aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(5),
        cookie_jar=aiohttp.DummyCookieJar()
    )
    tasks = [limited_fetch(f"https://www.goodreads.com/quotes?page={x}", sess) for x in range(1, 101)]
    all_pages = await asyncio.gather(*tasks)
    all_pages = [p for p in all_pages if p is not None]
    await sess.close()

    all_quotes = []
    for _, page in all_pages:
        parsed_quotes = parser(page)
        all_quotes.extend(parsed_quotes)

    with open("quotes.json", "w", encoding="utf-8") as file:
        json.dump(all_quotes, file, indent=4, ensure_ascii=False)
    
    print(f"{len(all_quotes)} quotes have been written to 'quotes.json'")

asyncio.run(main())
