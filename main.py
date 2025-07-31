import logging
import random
import sys

import httpx
import uvicorn
from bs4 import BeautifulSoup
from fastapi import FastAPI
from pydantic import BaseModel

log = logging.getLogger(__name__)
log.info(uvicorn.Config.asgi_version)
log.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler(sys.stdout)
log_formatter = logging.Formatter(
    "%(asctime)s [%(processName)s: %(process)d] [%(threadName)s: %(thread)d] [%(levelname)s] %(name)s: %(message)s"
)
stream_handler.setFormatter(log_formatter)
log.addHandler(stream_handler)

app = FastAPI(
    title="Scaper Server",
    description="API for crawl website",
    version="0.1.0",
)


class ScrapeRequest(BaseModel):
    url: str
    time: int


user_agent_list = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_4_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1",
    "Mozilla/4.0 (compatible; MSIE 9.0; Windows NT 6.1)",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36 Edg/87.0.664.75",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.18363",
]

head = {
    "User-Agent": user_agent_list[random.randint(0, len(user_agent_list) - 1)]
}

client = httpx.AsyncClient()


@app.post("/scrape")
async def scrape(request: ScrapeRequest):
    # data = await request.json()
    # url = data["url"]
    response = await client.get(request.url, headers=head)
    log.info("Send request sucessfully !!!!")
    soup = BeautifulSoup(response.text)
    return {"content": soup.prettify()}


def main():
    uvicorn.run(
        "main:app", host="127.0.0.1", port=8000, reload=True, log_config=log
    )


if __name__ == "__main__":
    main()
