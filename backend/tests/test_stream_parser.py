import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.parsers.stream_parser import StreamTable, parse_csv, parse_json

client = TestClient(app)
ROW = {"stream_id": "S1", "mass_flow_kg_h": 120, "temperature_c": 25,
       "pressure_bar_abs": 1.2, "phase": " Liquid "}
HEADER = "stream_id,mass_flow_kg_h,temperature_c,pressure_bar_abs,phase\n"


def test_json_csv_equivalent():
    csv_table = parse_csv((HEADER + "S1,120,25,1.2,Liquid\n").encode())
    assert csv_table == parse_json({"streams": [ROW]})
    assert isinstance(csv_table, StreamTable)


@pytest.mark.parametrize("field,value", [("mass_flow_kg_h", -1), ("pressure_bar_abs", 0),
    ("temperature_c", -274), ("phase", "unknown"), ("mass_flow_kg_h", "NaN"),
    ("stream_id", " ")])
def test_invalid_json(field, value):
    response = client.post("/api/streams/parse/json", json={"streams": [ROW | {field: value}]})
    assert response.status_code == 422


def test_duplicate_streams():
    assert client.post("/api/streams/parse/json", json={"streams": [ROW, ROW]}).status_code == 422


@pytest.mark.parametrize("content", [b"", b"stream_id,phase\nS1,liquid", b"\xff", HEADER.encode(),
    (HEADER + "S1,1,2,3,liquid,extra").encode(),
    (HEADER + "S1,-1,25,1,liquid").encode()])
def test_bad_csv_returns_422(content):
    response = client.post("/api/streams/parse/csv", files={"file": ("streams.csv", content)})
    assert response.status_code == 422


def test_csv_upload():
    content = b"\xef\xbb\xbf" + (HEADER + "S1,120,25,1.2,liquid").encode()
    response = client.post("/api/streams/parse/csv", files={"file": ("streams.csv", content)})
    assert response.status_code == 200
    assert response.json()["streams"][0]["mass_flow_kg_h"] == 120


def test_upload_limit():
    response = client.post("/api/streams/parse/csv", files={"file": ("big.csv", b"x" * (5 * 1024 * 1024 + 1))})
    assert response.status_code == 413


def test_stream_endpoints_normalize_across_csv_and_json():
    headers = HEADER.rstrip("\n") + ",source_unit,destination_unit\n"
    csv = parse_csv((headers + "S1,120,25,1.2,Liquid,  , E1 \n").encode())
    data = parse_json({"streams": [ROW | {"source_unit": None, "destination_unit": "E1"}]})
    assert csv == data
    assert csv.streams[0].source_unit is None
    assert csv.streams[0].destination_unit == "E1"
