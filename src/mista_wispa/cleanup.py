import re

from openai import OpenAI

_ALWAYS_REMOVE_FILLERS = {
    "um", "uh", "uhm", "umm", "ah", "er",
    "basically", "literally",
}

_START_ONLY_FILLERS = {
    "like", "so", "well", "right", "actually",
}

_START_ONLY_FILLER_PHRASES = [
    "you know",
    "i mean",
    "kind of",
    "sort of",
]


def rule_based_cleanup(text: str) -> str:
    if not text.strip():
        return ""

    t = text

    # Normalize whitespace
    t = re.sub(r"\s+", " ", t).strip()

    # Remove always-remove filler words, preserving trailing punctuation
    words = t.split()
    cleaned: list[str] = []
    for w in words:
        bare = w.rstrip(".,!?;:")
        trailing = w[len(bare):]  # punctuation after the word
        if bare.lower() in _ALWAYS_REMOVE_FILLERS:
            # Attach trailing punctuation to the previous word
            if trailing and cleaned:
                cleaned[-1] = cleaned[-1] + trailing
            # Otherwise just drop the filler (and its punctuation if no previous word)
        else:
            cleaned.append(w)
    words = cleaned
    t = " ".join(words)

    # Collapse duplicate commas (e.g. from "I went, um, to" -> "I went,, to")
    t = re.sub(r",\s*,", ",", t)

    # Normalize whitespace again after filler removal
    t = re.sub(r"\s+", " ", t).strip()

    # Remove start-only fillers and filler phrases from the beginning (repeatedly)
    changed = True
    while changed:
        changed = False
        stripped = t.lstrip()
        if not stripped:
            break
        # Check start-only filler phrases first
        for phrase in _START_ONLY_FILLER_PHRASES:
            pattern = re.compile(rf"^{phrase}\b\s*", re.IGNORECASE)
            m = pattern.match(stripped)
            if m:
                t = stripped[m.end():]
                changed = True
                break
        if changed:
            continue
        # Check start-only filler words
        first_word_match = re.match(r"(\S+)\s*(.*)", stripped)
        if first_word_match:
            first_word = first_word_match.group(1)
            rest = first_word_match.group(2)
            bare_first = first_word.rstrip(".,!?;:")
            if bare_first.lower() in _START_ONLY_FILLERS:
                t = rest
                changed = True

    # Normalize whitespace
    t = re.sub(r"\s+", " ", t).strip()

    # Preserve ellipses: temporarily replace them
    t = t.replace("...", "\x00ELLIPSIS\x00")

    # Fix double/triple punctuation (but not ellipses, which are now protected)
    t = re.sub(r"([.!?])[.!?]+", r"\1", t)

    # Restore ellipses
    t = t.replace("\x00ELLIPSIS\x00", "...")

    # Ensure space after sentence-ending punctuation
    # Handle ellipsis: after "..." capitalize the next letter
    t = re.sub(r"(\.{3})(\s*)([a-zA-Z])", lambda m: f"{m.group(1)} {m.group(3).upper()}", t)
    # Handle single sentence-ending punctuation
    t = re.sub(r"([.!?])(\s*)([a-zA-Z])", lambda m: f"{m.group(1)} {m.group(3).upper()}", t)

    # Capitalize first character
    if t:
        t = t[0].upper() + t[1:]

    # Clean up if everything was fillers (no alphanumeric content left)
    if not re.search(r"[a-zA-Z0-9]", t):
        return ""

    return t


_LLM_SYSTEM_PROMPT = (
    "You are a text cleanup assistant. The user will provide raw speech-to-text output. "
    "Clean it up: fix grammar, improve punctuation, format lists if detected. "
    "Preserve meaning exactly. Do not add or remove content. "
    "Return only the cleaned text, nothing else."
)


def llm_cleanup(text: str, *, server_url: str, model: str = "local-model", timeout: float = 3.0) -> str:
    if not text.strip():
        return text
    try:
        client = OpenAI(base_url=server_url, api_key="not-needed")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _LLM_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            timeout=timeout,
        )
        result = response.choices[0].message.content
        return result if result and result.strip() else text
    except Exception:
        return text
