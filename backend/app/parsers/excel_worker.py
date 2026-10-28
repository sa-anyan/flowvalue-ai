"""Short-lived constrained parser process; uploaded code is never imported/executed."""

import json
import sys
from pathlib import Path


def main():
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
        if sys.platform == "linux":
            resource.setrlimit(
                resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024)
            )
        from app.parsers.balance import parse_excel

        result = parse_excel(Path(sys.argv[1]).read_bytes(), sys.argv[2])
        print(json.dumps({"report": result.model_dump(mode="json")}, allow_nan=False))
    except Exception as exc:  # noqa: BLE001 - untrusted workbook process boundary
        # No stack traces, local filenames or workbook content in API errors.
        print(
            json.dumps(
                {
                    "error": str(exc)[:400]
                    if isinstance(exc, ValueError)
                    else "Malformed or unsupported workbook; parsing stopped safely."
                }
            )
        )


if __name__ == "__main__":
    main()
