"""Web interface to tag a folder of images, with optional AI suggestions.

    python tagger.py                      # untagged images (./config.json, else the demo)
    python tagger.py --review             # images tagged by auto_tag.py, to check them
    python tagger.py --config my.json --port 5001
"""
import argparse
import shutil
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from flask import Flask, abort, jsonify, redirect, request, send_file, send_from_directory

from store import Store, find_config
from suggest import suggest_tags

WEB_DIR = Path(__file__).parent / "web"

app = Flask(__name__, static_folder=None)
store: Store
queue: list[str] = []
state = {"index": 0, "last_tags": [], "review": False}


def current_key() -> str | None:
    return queue[state["index"]] if state["index"] < len(queue) else None


# ---------- static ----------
# The interface lives under /web/ so its relative links work the same
# here and on GitHub Pages.
@app.route("/")
def root():
    return redirect("/web/")


@app.route("/web/")
@app.route("/web/<path:name>")
def web_file(name="index.html"):
    return send_from_directory(WEB_DIR, name)


@app.route("/img/<path:key>")
def image(key):
    try:
        return send_file(store.path_of(key))
    except (ValueError, FileNotFoundError):
        abort(404)


# ---------- api ----------
@app.route("/api/config")
def get_config():
    c = store.config
    return jsonify({
        "language": c["language"],
        "categories": c["categories"],
        "categoryLabels": c.get("category_labels", {}),
        "nsfwTags": c["nsfw_tags"],
        "popularTags": c["popular_tags"],
        "allowDelete": c["allow_delete"],
        "review": state["review"],
        "demo": False,
    })


@app.route("/api/stats")
def get_stats():
    return jsonify(store.stats())


@app.route("/api/tags")
def get_tags():
    return jsonify({"tags": store.all_tags()})


@app.route("/api/current")
def get_current():
    key = current_key()
    if key is None:
        return jsonify({"done": True, "total": len(queue)})
    return jsonify({"key": key, "index": state["index"], "total": len(queue),
                    "tags": store.tags_of(key)})


@app.route("/api/save", methods=["POST"])
def save():
    key = current_key()
    tags = [t for t in (request.json or {}).get("tags", []) if t]
    if key is None or not tags:
        return jsonify({"success": False})
    store.set_tags(key, tags)
    state["last_tags"] = tags
    print(f"💾 {key} -> {' '.join(tags)}")
    state["index"] += 1
    return jsonify({"success": True})


@app.route("/api/skip", methods=["POST"])
def skip():
    if state["index"] < len(queue):
        state["index"] += 1
    return jsonify({"success": True})


@app.route("/api/back", methods=["POST"])
def back():
    if state["index"] > 0:
        state["index"] -= 1
    return jsonify({"success": True})


@app.route("/api/last-tags")
def last_tags():
    return jsonify({"tags": state["last_tags"]})


@app.route("/api/suggest", methods=["POST"])
def suggest():
    key = current_key()
    if key is None:
        return jsonify({"tags": []})
    try:
        tags = suggest_tags(anthropic.Anthropic(), store.path_of(key), store.candidate_tags(), store.config)
    except anthropic.AuthenticationError:
        return jsonify({"tags": [], "error": "auth"}), 401
    except anthropic.APIError as e:
        print(f"❌ Claude API error: {e}")
        return jsonify({"tags": [], "error": "api"}), 502
    print(f"✨ {key} -> {' '.join(tags)}")
    return jsonify({"tags": tags})


@app.route("/api/delete", methods=["POST"])
def delete():
    """Moves the file to <config folder>/.trash/ (never a hard delete)."""
    key = current_key()
    if not store.config["allow_delete"] or key is None:
        return jsonify({"success": False}), 403
    src = store.path_of(key)
    dest = store.root / ".trash" / key
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(src, dest)
    store.forget(key)
    queue.pop(state["index"])
    print(f"🗑️  {key} moved to {dest}")
    return jsonify({"success": True})


def main() -> None:
    global store, queue
    parser = argparse.ArgumentParser(description="Image tagging web interface")
    parser.add_argument("--config", help="path to config.json (default: ./config.json, else the demo)")
    parser.add_argument("--review", action="store_true", help="review images tagged by auto_tag.py")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    config_path = find_config(args.config)
    load_dotenv(config_path.parent / ".env")
    load_dotenv(Path(__file__).parent / ".env")
    store = Store(config_path)
    state["review"] = args.review
    queue = store.auto_tagged() if args.review else store.untagged()

    print(f"⚙️  Config: {config_path}")
    print(f"🖼️  {len(queue)} image(s) to {'review' if args.review else 'tag'}")
    print(f"\n🌐 http://localhost:{args.port}\n")
    app.run(port=args.port)


if __name__ == "__main__":
    main()
