import logging

import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)


def main() -> None:
    uvicorn.run(
        "argus.main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
