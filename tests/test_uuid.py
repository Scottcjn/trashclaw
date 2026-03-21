import pytest
import re
from plugins.uuid_generator import run as uuid_run

def test_uuid4():
    result = uuid_run(version=4, count=1)
    assert re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", result)

def test_uuid1():
    result = uuid_run(version=1, count=1)
    assert "-" in result
    assert result[14] == '1'

def test_uuid3():
    result = uuid_run(version=3, count=1, namespace="dns", name="example.com")
    assert result == "9073926b-929f-31c2-abc9-fad77ae3e8eb"

def test_uuid5():
    result = uuid_run(version=5, count=1, namespace="dns", name="example.com")
    assert result == "cfbff0d1-9375-5685-968c-48ce8b15ae17"

def test_count():
    result = uuid_run(version=4, count=3)
    lines = result.split("\n")
    assert len(lines) == 3

def test_invalid_namespace():
    result = uuid_run(version=3, count=1, namespace="invalid", name="test")
    assert "Error:" in result

def test_missing_name():
    result = uuid_run(version=5, count=1, namespace="dns", name="")
    assert "Error:" in result
