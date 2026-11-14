"""Ask Claude which tags of your own vocabulary fit an image."""
import base64
from io import BytesIO
from pathlib import Path

import anthropic
from PIL import Image

try:
    import pillow_avif  # noqa: F401  (AVIF support for Pillow < 11.2)
except ImportError:
    pass

MAX_SIDE = 1568  # larger images are downscaled by the API anyway, this saves upload


def encode_image(path: Path) -> str:
    with Image.open(path) as img:
        img = img.convert("RGB")
        img.thumbnail((MAX_SIDE, MAX_SIDE))
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=85)
    return base64.standard_b64encode(buf.getvalue()).decode("utf-8")


def build_prompt(candidates: list[str], nsfw_tags: list[str], max_tags: int) -> str:
    prompt = (
        "Look at this image carefully. Choose only the most relevant tags "
        f"from this exact list: {', '.join(candidates)}\n\n"
    )
    if nsfw_tags:
        prompt += (
            "If the image shows nudity, lingerie or sexual content, you MUST include "
            f"the matching tag among: {', '.join(nsfw_tags)}.\n\n"
        )
    prompt += (
        "Reply with only the matching tags separated by spaces, no explanation. "
        f"Max {max_tags} tags. Only use tags from the list."
    )
    return prompt


def suggest_tags(client: anthropic.Anthropic, path: Path, candidates: list[str], config: dict) -> list[str]:
    """Returns tags from `candidates` only, spelled as in `candidates`.
    An empty list means no usable answer (refusal, empty reply)."""
    kwargs = {}
    if config.get("effort"):
        kwargs["output_config"] = {"effort": config["effort"]}

    message = client.messages.create(
        model=config["model"],
        max_tokens=1024,  # room for adaptive thinking on top of a short answer
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                             "data": encode_image(path)}},
                {"type": "text", "text": build_prompt(candidates, config["nsfw_tags"],
                                                      config["max_suggestions"])},
            ],
        }],
        **kwargs,
    )

    if message.stop_reason == "refusal":
        return []
    text = " ".join(b.text for b in message.content if b.type == "text")

    allowed = {t.lower(): t for t in candidates}
    tags = []
    for word in text.replace(",", " ").split():
        tag = allowed.get(word.strip().lower())
        if tag and tag not in tags:
            tags.append(tag)
    return tags[: config["max_suggestions"]]
