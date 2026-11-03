"""Canonical compressed workbook and multipart upload bounds (bytes)."""
MAX_WORKBOOK_BYTES = 20 * 1024 * 1024
MAX_UPLOAD_REQUEST_BYTES = 21 * 1024 * 1024  # workbook + multipart/context overhead
MAX_OTHER_REQUEST_BYTES = 5 * 1024 * 1024
