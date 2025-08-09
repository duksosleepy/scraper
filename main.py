import logging
import logging.config
import random
import sqlite3

import httpx
import uvicorn
from bs4 import BeautifulSoup
from fastapi import FastAPI
from pydantic import BaseModel

con = sqlite3.connect("crawl.db")
cur = con.cursor()


class ColoredFormatter(logging.Formatter):
    """Add colors to log levels"""

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
        "": {
            "level": "INFO",
            "handlers": ["default"],
            "propagate": False,
        },
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

head = {"User-Agent": random.choice(user_agent_list)}

client = httpx.AsyncClient()


@app.post("/scrape")
async def scrape(request: ScrapeRequest):
    response = await client.get(request.url, headers=head)
    log.info("Send request sucessfully !!!!")
    soup = BeautifulSoup(response.text, "html.parser")
    try:
        cur = con.cursor()
        res = cur.execute(
            "SELECT * FROM storage WHERE domain = ?",
            (request.url),
        )
        if res.fetchone():
            return {"status": 200, "content": res.fetchone()[1]}
        else:
            cur = con.cursor()
            cur.execute(
                "INSERT INTO storage(domain, content) VALUES (?, ?);",
                (request.url, soup.prettify()),
            )
            con.commit()

    except Exception as e:
        log.error(e)
    return {"status": 200, "content": soup.prettify()}


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
