import io
from PIL import Image
from mute_bot.services.automod import (
    find_banned_term,
    normalize_filter_text,
    preprocess_ocr,
)


def test_find_banned_term_matches_exact_leet_and_homoglyphs() -> None:
    assert find_banned_term("hitler") == "hitler"
    assert find_banned_term("h!7l3r") == "hitler"
    assert find_banned_term("rape") == "rape"
    assert find_banned_term("raped") == "rape"
    assert find_banned_term("r.a.p.e.d") == "rape"
    assert find_banned_term("k.y.s") == "kys"
    assert find_banned_term("n\u200bi\u200bg\u200bg\u200ba") == "nigga"
    assert find_banned_term("|/\\|1gg@") == "nigga"


def test_find_banned_term_avoids_false_positives() -> None:
    for safe_text in (
        "I got trapped in center beacon",
        "he scraped by with 10 HP",
        "draped in gold",
        "grape juice",
        "therapist",
        "skyscraper",
        "normal War Robots discussion",
    ):
        assert find_banned_term(safe_text) is None, f"False positive on: {safe_text}"


def test_normalize_filter_text_strips_combining_and_zero_width() -> None:
    assert normalize_filter_text("h\u0301i\u200bt") == "hit"
    assert normalize_filter_text("/\\") == "n"


def test_preprocess_ocr_upscales_small_images_to_grayscale() -> None:
    img = Image.new("RGB", (300, 150), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    processed = preprocess_ocr(buf.getvalue())
    assert processed.mode == "L"
    assert processed.size == (900, 450)
