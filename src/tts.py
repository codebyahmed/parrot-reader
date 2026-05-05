import os
import re
import wave

import numpy as np
from onnxruntime import InferenceSession
from ._config import PKGDATADIR as BASE

SAMPLE_RATE = 24_000
MAX_PHONEME_LENGTH = 510


def title_from_text(text: str) -> str:
    words = text.split()[:5]
    cleaned = (re.sub(r'[^\w]', '', w) for w in words if w)
    slug = ' '.join(w for w in cleaned if w)
    return (slug[:48] or 'Speech').capitalize()

_VOCAB: dict[str, int] = {
    "$": 0, ";": 1, ":": 2, ",": 3, ".": 4, "!": 5, "?": 6,
    "—": 9, "…": 10, "\"": 11, "(": 12, ")": 13,
    "“": 14, "”": 15, " ": 16, "̃": 17,
    "ʣ": 18, "ʥ": 19, "ʦ": 20, "ʨ": 21,
    "ᵝ": 22, "ꭧ": 23, "A": 24, "I": 25, "O": 31,
    "Q": 33, "S": 35, "T": 36, "W": 39, "Y": 41, "ᵊ": 42,
    "a": 43, "b": 44, "c": 45, "d": 46, "e": 47, "f": 48,
    "h": 50, "i": 51, "j": 52, "k": 53, "l": 54, "m": 55,
    "n": 56, "o": 57, "p": 58, "q": 59, "r": 60, "s": 61,
    "t": 62, "u": 63, "v": 64, "w": 65, "x": 66, "y": 67,
    "z": 68, "ɑ": 69, "ɐ": 70, "ɒ": 71,
    "æ": 72, "β": 75, "ɔ": 76, "ɕ": 77,
    "ç": 78, "ɖ": 80, "ð": 81, "ʤ": 82,
    "ə": 83, "ɚ": 85, "ɛ": 86, "ɜ": 87,
    "ɟ": 90, "ɡ": 92, "ɥ": 99, "ɨ": 101,
    "ɪ": 102, "ʝ": 103, "ɯ": 110, "ɰ": 111,
    "ŋ": 112, "ɳ": 113, "ɲ": 114, "ɴ": 115,
    "ø": 116, "ɸ": 118, "θ": 119, "œ": 120,
    "ɹ": 123, "ɾ": 125, "ɻ": 126, "ʁ": 128,
    "ɽ": 129, "ʂ": 130, "ʃ": 131, "ʈ": 132,
    "ʧ": 133, "ʊ": 135, "ʋ": 136, "ʌ": 138,
    "ɣ": 139, "ɤ": 140, "χ": 142, "ʎ": 143,
    "ʒ": 147, "ʔ": 148, "ˈ": 156, "ˌ": 157,
    "ː": 158, "ʰ": 162, "ʲ": 164, "↓": 169,
    "→": 171, "↗": 172, "↘": 173, "ᵻ": 177,
}

_VOICE_PREFIX_G2P: dict[str, tuple[str, object]] = {
    "a": ("en",     False),
    "b": ("en",     True),
    "e": ("espeak", "es"),
    "f": ("espeak", "fr-fr"),
    "h": ("espeak", "hi"),
    "i": ("espeak", "it"),
    "j": ("ja",     None),
    "p": ("espeak", "pt-br"),
    "z": ("zh",     None),
}

_session: InferenceSession | None = None
_g2p_cache: dict[str, object] = {}
_voices_cache: dict[str, np.ndarray] = {}


def _load_session() -> InferenceSession:
    global _session
    if _session is None:
        _session = InferenceSession(os.path.join(BASE, "model.onnx"))
    return _session


def _load_g2p(voice: str):
    prefix = voice[:1]
    if prefix not in _VOICE_PREFIX_G2P:
        raise ValueError(
            f"Voice '{voice}' has unknown language prefix '{prefix}'. "
            f"Known prefixes: {sorted(_VOICE_PREFIX_G2P)}"
        )
    if prefix in _g2p_cache:
        return _g2p_cache[prefix]

    kind, arg = _VOICE_PREFIX_G2P[prefix]
    if kind == "en":
        from misaki import en, espeak
        fallback = espeak.EspeakFallback(british=bool(arg))
        g2p = en.G2P(trf=False, british=bool(arg), fallback=fallback)
    elif kind == "espeak":
        from misaki import espeak
        from misaki.espeak import EspeakG2P
        fallback = espeak.EspeakFallback(british=False)
        g2p = EspeakG2P(language=arg, fallback=fallback)
    elif kind == "ja":
        from misaki.ja import JAG2P
        g2p = JAG2P()
    elif kind == "zh":
        from misaki.zh import ZHG2P
        g2p = ZHG2P(version="1.1")
    else:
        raise RuntimeError(f"Unhandled G2P kind: {kind}")

    _g2p_cache[prefix] = g2p
    return g2p


def _load_voice(voice_name: str) -> np.ndarray:
    if voice_name not in _voices_cache:
        path = os.path.join(BASE, "voices", f"{voice_name}.bin")
        _voices_cache[voice_name] = np.fromfile(path, dtype=np.float32).reshape(-1, 1, 256)
    return _voices_cache[voice_name]


def _phonemes_to_ids(ph: str) -> list[int]:
    return [_VOCAB[ch] for ch in ph if ch in _VOCAB]


def _split_phonemes(ph: str) -> list[str]:
    parts = re.split(r"([.,!?;])", ph)
    units: list[str] = []
    i = 0
    while i < len(parts):
        seg = parts[i].strip()
        punc = parts[i + 1] if (i + 1 < len(parts) and parts[i + 1] in ".,!?;") else ""
        if seg or punc:
            units.append(seg + punc)
        i += 2 if punc else 1

    batches: list[str] = []
    current = ""

    def flush():
        nonlocal current
        if current:
            batches.append(current.strip())
            current = ""

    for unit in units:
        if not unit:
            continue
        candidate = (current + " " + unit) if current else unit
        if len(candidate) <= MAX_PHONEME_LENGTH:
            current = candidate
            continue
        flush()
        if len(unit) <= MAX_PHONEME_LENGTH:
            current = unit
            continue
        for word in unit.split(" "):
            if not word:
                continue
            cand = (current + " " + word) if current else word
            if len(cand) <= MAX_PHONEME_LENGTH:
                current = cand
            else:
                flush()
                current = word
    flush()
    return batches


def _infer(ids: list[int], voices: np.ndarray) -> np.ndarray:
    sess = _load_session()
    ref_s = voices[min(len(ids), len(voices) - 1)]
    waveform, _ = sess.run(
        None,
        {
            "input_ids": [[0, *ids, 0]],
            "style": ref_s,
            "speed": np.ones(1, dtype=np.float32),
        },
    )
    return waveform[0]


def _trim_silence(audio: np.ndarray, top_db: float = 60.0) -> np.ndarray:
    from .trim import trim
    trimmed, _ = trim(audio, top_db=top_db)
    return trimmed


def synthesize(text: str, voice: str, output_path: str, progress_callback=None) -> str:
    g2p = _load_g2p(voice)
    voices = _load_voice(voice)

    phonemes, _ = g2p(text)
    batches = _split_phonemes(phonemes)
    total = len(batches)

    waveforms: list[np.ndarray] = []
    for i, batch in enumerate(batches):
        ids = _phonemes_to_ids(batch)
        wav = _infer(ids, voices)
        wav = _trim_silence(wav)
        waveforms.append(wav)
        if progress_callback:
            progress_callback((i + 1) / total)

    audio = np.concatenate(waveforms) if waveforms else np.zeros(0, dtype=np.float32)

    output_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    audio_i16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(output_path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_i16.tobytes())

    return output_path