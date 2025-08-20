import functools
import hashlib
import logging
import logging.config
import random
import sqlite3
import time
import uuid

import httpx
import uvicorn
from bs4 import BeautifulSoup
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

rate_limit_store = {}
api_key = {
    "b42cbdb211f7065513e40f2dbd373025609c17ef03823887e51183274813d38e": "00010203-0405-0607-0809-0a0b0c0d0e0f"
}
MAX_REQUESTS = 5
TIME_WINDOW = 60

# --- Database setup ---
con = sqlite3.connect("crawl.db", check_same_thread=False)
con.execute("pragma journal_mode=wal")
cur = con.cursor()


class ColoredFormatter(logging.Formatter):
    grey = "\x1b[38;5;240m"
    yellow = "\x1b[33m"
    red = "\x1b[31m"
    bold_red = "\x1b[31;1m"
    green = "\x1b[32m"
    reset = "\x1b[0m"

    COLORS = {
        "DEBUG": grey,
        "INFO": green,
        "WARNING": yellow,
        "ERROR": red,
        "CRITICAL": bold_red,
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.reset)
        record.levelname = f"{log_color}{record.levelname}{self.reset}"
        record.msg = f"{log_color}{record.msg}{self.reset}"
        return super().format(record)


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "colored": {
            "()": ColoredFormatter,
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "default": {
            "level": "INFO",
            "formatter": "colored",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "": {"level": "INFO", "handlers": ["default"], "propagate": False},
        "uvicorn.error": {
            "level": "INFO",
            "handlers": ["default"],
            "propagate": False,
        },
        "uvicorn.access": {
            "level": "INFO",
            "handlers": ["default"],
            "propagate": False,
        },
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
log = logging.getLogger(__name__)

# --- FastAPI app ---
app = FastAPI(
    title="Scraper Server",
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

head = {"User-Agent": random.choice(user_agent_list)}
client = httpx.AsyncClient()


@app.middleware("http")
async def rate_limiter(request: Request, call_next):
    client_ip = request.client.host
    now = time.time()

    request_times = rate_limit_store.get(client_ip, [])
    request_times = [t for t in request_times if now - t < TIME_WINDOW]

    if len(request_times) >= MAX_REQUESTS:
        # Return proper JSONResponse with 429 status code
        return JSONResponse(
            status_code=429,
            content={"status": 429, "error": "Too many requests, please wait."},
        )

    request_times.append(now)
    rate_limit_store[client_ip] = request_times

    client_ip = request.client.host or "unknown"
    user_agent = request.headers.get("User-Agent", "unknown")
    language = request.headers.get("Accept-Language")
    raw_fingerprint = f"{client_ip}:{user_agent}:{language}"
    device_id = hashlib.sha256(raw_fingerprint.encode()).hexdigest()
    log.info(device_id)
    if device_id not in api_key:
        api_key[device_id] = uuid.UUID("{00010203-0405-0607-0809-0a0b0c0d0e0f}")

    x_api_token = request.headers.get("X-API-TOKEN")

    if not x_api_token:
        return JSONResponse(
            status_code=401,
            content={"status": 401, "error": "Missing X-API-TOKEN header"},
        )
    if x_api_token != api_key[device_id]:
        return JSONResponse(
            status_code=403,
            content={"status": 403, "error": "Invalid X-API-TOKEN"},
        )
    log.info(f"Received X-API-TOKEN: {x_api_token}")

    return await call_next(request)


@functools.lru_cache
@app.post("/scrape")
async def scrape(request: ScrapeRequest):
    response = await client.get(request.url, headers=head)
    log.info("Send request successfully!")
    soup = BeautifulSoup(response.text, "html.parser")
    try:
        res = cur.execute(
            "SELECT * FROM storage WHERE domain = ?", (request.url,)
        )
        row = res.fetchone()
        if row:
            return {"status": 200, "content": row[1]}
        else:
            cur.execute(
                "INSERT INTO storage(domain, content) VALUES (?, ?);",
                (request.url, soup.prettify()),
            )
            con.commit()
            return {"status": 200, "content": soup.prettify()}
    except Exception as e:
        log.error(f"Database error: {e}")
        return {"status": 500, "error": str(e)}


def main():
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_config=LOGGING_CONFIG,
    )


if __name__ == "__main__":
    main()
