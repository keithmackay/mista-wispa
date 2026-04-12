import re

_FILLER_WORDS = {
    "um", "uh", "uhm", "umm", "ah", "er",
    "like", "basically", "literally", "actually",
    "so", "well", "right",
}

_FILLER_PHRASES = [
    "you know",
    "i mean",
    "kind of",
    "sort of",
]


def rule_based_cleanup(text: str) -> str:
    if not text.strip():
        return ""

    t = text

    # Remove filler phrases (case-insensitive)
    for phrase in _FILLER_PHRASES:
        t = re.sub(rf"\b{phrase}\b", "", t, flags=re.IGNORECASE)

    # Remove filler words (case-insensitive, whole words only)
    words = t.split()
    words = [w for w in words if w.strip(".,!?;:").lower() not in _FILLER_WORDS]
    t = " ".join(words)

    # Normalize whitespace
    t = re.sub(r"\s+", " ", t).strip()

    # Fix double/triple punctuation
    t = re.sub(r"([.!?])[.!?]+", r"\1", t)

    # Ensure space after sentence-ending punctuation
    t = re.sub(r"([.!?])(\s*)([a-zA-Z])", lambda m: f"{m.group(1)} {m.group(3).upper()}", t)

    # Capitalize first character
    if t:
        t = t[0].upper() + t[1:]

    # Clean up if everything was fillers (no alphanumeric content left)
    if not re.search(r"[a-zA-Z0-9]", t):
        return ""

    return t
