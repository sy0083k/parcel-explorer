import logging


def configure_logging() -> None:
    """Configure a minimal shared logging format for API diagnostics."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] [req:%(request_id)s] %(message)s",
    )


class RequestIdFilter(logging.Filter):
    """Attach request id on log records so formatters can safely reference it."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True
