import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from IndicTransToolkit.processor import IndicProcessor


MODEL_NAME = "ai4bharat/indictrans2-indic-en-dist-200M"

INDIC_LANGUAGE_CODES = {
    "as": "asm_Beng",
    "bn": "ben_Beng",
    "brx": "brx_Deva",
    "doi": "doi_Deva",
    "gom": "gom_Deva",
    "gu": "guj_Gujr",
    "hi": "hin_Deva",
    "kn": "kan_Knda",
    "ks": "kas_Arab",
    "mai": "mai_Deva",
    "ml": "mal_Mlym",
    "mr": "mar_Deva",
    "mni": "mni_Mtei",
    "ne": "npi_Deva",
    "or": "ory_Orya",
    "pa": "pan_Guru",
    "sa": "san_Deva",
    "sat": "sat_Olck",
    "sd": "snd_Arab",
    "ta": "tam_Taml",
    "te": "tel_Telu",
    "ur": "urd_Arab",
}


class IndicTranslator:
    """
    IndicTrans2-based translator for supported Indian languages.

    Whisper language codes such as 'hi', 'ta', and 'bn'
    are mapped to the corresponding IndicTrans2 language codes.
    """

    def __init__(self, model_name=MODEL_NAME, device=None):
        self.model_name = model_name

        self.device = device or (
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        self.processor = IndicProcessor(inference=True)

        self.tokenizer = None
        self.model = None

    def _load_model(self):
        """Load the IndicTrans2 model only when translation is needed."""

        if self.model is not None:
            return

        print(f"Loading IndicTrans2 model on {self.device}...")

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            trust_remote_code=True
        )

        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            self.model_name,
            trust_remote_code=True
        ).to(self.device)

        self.model.eval()

        print("IndicTrans2 model loaded successfully.")

    def translate_batch(
        self,
        texts,
        source_language,
        target_language="eng_Latn",
    ):
        """
        Translate a batch of text segments into English.

        Parameters
        ----------
        texts : list[str]
            Source-language texts.

        source_language : str
            Whisper language code, e.g. 'hi', 'ta', 'bn'.

        target_language : str
            IndicTrans2 target language code.
            Defaults to English ('eng_Latn').

        Returns
        -------
        list[str]
            Translated English texts.
        """

        if source_language not in INDIC_LANGUAGE_CODES:
            raise ValueError(
                f"Unsupported Indic language: {source_language}"
            )

        self._load_model()

        src_lang = INDIC_LANGUAGE_CODES[source_language]

        batch = self.processor.preprocess_batch(
            texts,
            src_lang=src_lang,
            tgt_lang=target_language,
        )

        inputs = self.tokenizer(
            batch,
            padding=True,
            truncation=True,
            return_tensors="pt",
        ).to(self.device)

        with torch.no_grad():
            generated_tokens = self.model.generate(
                **inputs,
                num_beams=5,
                num_return_sequences=1,
                max_length=256,
            )

        generated_text = self.tokenizer.batch_decode(
            generated_tokens,
            skip_special_tokens=True,
        )

        translations = self.processor.postprocess_batch(
            generated_text,
            lang=target_language,
        )

        return translations

    def translate_segments(
        self,
        segments,
        source_language,
        batch_size=8,
    ):
        """
        Translate timestamped transcript segments.

        Each segment must contain:
            start
            end
            text

        The returned segment keeps the original timestamps and
        adds a 'translated' field.
        """

        if source_language not in INDIC_LANGUAGE_CODES:
            raise ValueError(
                f"Unsupported Indic language: {source_language}"
            )

        translated_segments = []

        for start in range(0, len(segments), batch_size):

            batch_segments = segments[
                start:start + batch_size
            ]

            texts = [
                segment["text"].strip()
                for segment in batch_segments
            ]

            translations = self.translate_batch(
                texts,
                source_language,
            )

            for segment, translation in zip(
                batch_segments,
                translations,
            ):
                result = dict(segment)
                result["translated"] = translation
                translated_segments.append(result)

            print(
                f"Translated "
                f"{min(start + batch_size, len(segments))}/"
                f"{len(segments)} segments"
            )

        return translated_segments


def is_indic_language(language):
    """Return True if the Whisper language is supported by IndicTrans2."""

    return language in INDIC_LANGUAGE_CODES