"""Configuration, image discovery and metadata storage shared by every script."""
import json
import os
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent

DEFAULTS = {
    "images_dir": "images",
    "metadata_file": "metadata.json",
    "extensions": [".avif", ".webp", ".png", ".jpg", ".jpeg"],
    "language": "en",
    "model": "claude-haiku-5-5",
    "effort": "low",
    "max_suggestions": 8,
    "candidate_tags_limit": 80,
    "nsfw_tags": [],
    "popular_tags": [],
    "allow_delete": False,
    "categories": {},
}


def find_config(explicit: str | None = None) -> Path:
    """Explicit path, else ./config.json, else the bundled demo config."""
    if explicit:
        return Path(explicit).resolve()
    local = Path.cwd() / "config.json"
    if local.exists():
        return local.resolve()
    return (HERE / "demo" / "config.json").resolve()


class Store:
    """Paths in the config are relative to the config file. Metadata keys are
    POSIX paths relative to that same folder, e.g. "images/2024/05/cat.avif"."""

    def __init__(self, config_path: Path):
        self.config_path = Path(config_path).resolve()
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = {**DEFAULTS, **json.load(f)}
        self.root = self.config_path.parent
        self.images_dir = (self.root / self.config["images_dir"]).resolve()
        self.metadata_file = (self.root / self.config["metadata_file"]).resolve()
        self.metadata = self._load_metadata()

    # ---------- metadata ----------
    def _load_metadata(self) -> dict:
        if self.metadata_file.exists():
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save(self) -> None:
        """Atomic write: an interrupted run never leaves a half-written file."""
        tmp = self.metadata_file.with_suffix(self.metadata_file.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.metadata_file)

    def tags_of(self, key: str) -> list[str]:
        return self.metadata.get(key, {}).get("tags", [])

    def set_tags(self, key: str, tags: list[str], auto: bool = False) -> None:
        entry = self.metadata.setdefault(key, {})
        entry["tags"] = tags
        if auto:
            entry["auto"] = True
        else:
            entry.pop("auto", None)  # saved by a human: considered reviewed
        self.save()

    def forget(self, key: str) -> None:
        if self.metadata.pop(key, None) is not None:
            self.save()

    # ---------- images ----------
    def key_of(self, path: Path) -> str:
        return path.resolve().relative_to(self.root).as_posix()

    def path_of(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.images_dir):
            raise ValueError(f"outside images_dir: {key}")
        return path

    def scan(self) -> list[str]:
        exts = {e.lower() for e in self.config["extensions"]}
        return [self.key_of(p) for p in sorted(self.images_dir.rglob("*"))
                if p.is_file() and p.suffix.lower() in exts]

    def untagged(self) -> list[str]:
        return [k for k in self.scan() if not self.tags_of(k)]

    def auto_tagged(self) -> list[str]:
        return [k for k in self.scan() if self.metadata.get(k, {}).get("auto")]

    # ---------- tags ----------
    def tag_counts(self) -> Counter:
        counts = Counter()
        for entry in self.metadata.values():
            counts.update(entry.get("tags", []))
        return counts

    def all_tags(self) -> list[str]:
        """Tags already used plus tags declared in the categories."""
        tags = set(self.tag_counts())
        for cat_tags in self.config["categories"].values():
            tags.update(cat_tags)
        return sorted(tags, key=str.lower)

    def candidate_tags(self) -> list[str]:
        """Vocabulary offered to the model: declared categories, most used
        tags, and the NSFW tags so they can never be forgotten."""
        tags = set()
        for cat_tags in self.config["categories"].values():
            tags.update(cat_tags)
        limit = self.config["candidate_tags_limit"]
        tags.update(t for t, _ in self.tag_counts().most_common(limit))
        tags.update(self.config["nsfw_tags"])
        return sorted(tags, key=str.lower)

    def stats(self) -> dict:
        tagged = [e for e in self.metadata.values() if e.get("tags")]
        total = sum(len(e["tags"]) for e in tagged)
        return {
            "totalTags": len(self.tag_counts()),
            "taggedImages": len(tagged),
            "avgTags": round(total / len(tagged), 1) if tagged else 0,
        }
