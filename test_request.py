import httpx

request = httpx.get("http://127.0.0.1:8000/scrape")
print(request.content)
