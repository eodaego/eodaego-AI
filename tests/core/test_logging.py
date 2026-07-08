import logging

from app.core.logging import configure_logging


def test_configure_logging_sets_expected_format_and_level():
    configure_logging()

    root_logger = logging.getLogger()

    assert root_logger.level == logging.INFO
    assert root_logger.handlers
    formatter = root_logger.handlers[0].formatter
    assert formatter is not None
    assert formatter._fmt == "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
