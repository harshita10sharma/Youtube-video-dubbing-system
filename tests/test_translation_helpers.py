import sys

from src.languages import INDIC_LANGUAGE_CODES, is_indic_language
from src.translator import merge_short_segments


def seg(start, end, text):
    return {"start": start, "end": end, "text": text}


def test_close_segments_are_merged():
    out = merge_short_segments([seg(0, 2, "a"), seg(2.3, 4, "b")])
    assert out == [seg(0, 4, "a b")]


def test_large_gap_prevents_merge():
    assert len(merge_short_segments([seg(0, 2, "a"), seg(5, 6, "b")])) == 2


def test_max_duration_prevents_merge():
    assert len(merge_short_segments([seg(0, 8, "a"), seg(8.1, 14, "b")])) == 2


def test_empty_input():
    assert merge_short_segments([]) == []


def test_input_not_mutated():
    original = [seg(0, 2, "a"), seg(2.1, 3, "b")]
    merge_short_segments(original)
    assert original[0]["text"] == "a"


def test_indic_language_detection():
    assert is_indic_language("hi") and is_indic_language("ta")
    assert not is_indic_language("en") and not is_indic_language("fr")
    assert INDIC_LANGUAGE_CODES["hi"] == "hin_Deva"


def test_checking_language_does_not_load_torch_stack():
    # Importing translator/languages must not pull in IndicTrans2.
    assert "src.indic_translator" not in sys.modules
