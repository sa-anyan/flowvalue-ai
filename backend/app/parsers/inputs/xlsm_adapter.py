"""Compatibility entry point for the single stream-centred workbook engine."""
from app.parsers.workbook_pipeline import parse_workbook


def parse_xlsm(content: bytes, filename: str, *, loaded=None):
    return parse_workbook(content, filename, loaded=loaded)
