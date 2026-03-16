import pytest
from trashclaw import extract_xml_tags

def test_extract_xml_tags():
    text = "Here is some text <test>inside tags</test> and outside."
    assert extract_xml_tags(text, "test") == "inside tags"

def test_extract_xml_tags_missing():
    text = "No tags here."
    assert extract_xml_tags(text, "test") == ""

def test_extract_xml_tags_multiline():
    text = "<test>\nline 1\nline 2\n</test>"
    assert extract_xml_tags(text, "test") == "line 1\nline 2"