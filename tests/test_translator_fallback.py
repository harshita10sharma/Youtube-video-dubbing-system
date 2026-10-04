import sys
import types

import src.translator as translator


class FakeGoogle:
    def __init__(self, source, target):
        pass

    def translate(self, text):
        return "EN:" + text


def test_indic_failure_falls_back_to_google(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    broken = types.ModuleType("src.indic_translator")

    class BrokenIndic:
        def __init__(self):
            raise ImportError("cannot import name 'PreTrainedTokenizerBase'")

    broken.IndicTranslator = BrokenIndic
    monkeypatch.setitem(sys.modules, "src.indic_translator", broken)
    monkeypatch.setattr(translator, "GoogleTranslator", FakeGoogle)

    segments = [{"start": 0.0, "end": 2.0, "text": "namaste"}]

    result = translator.translate_segments(segments, "hi")

    assert result[0]["translated"] == "EN:namaste"
    assert result[0]["start"] == 0.0 and result[0]["end"] == 2.0
