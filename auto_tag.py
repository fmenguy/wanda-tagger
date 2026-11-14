"""Tag every untagged image in one go with Claude, no interface needed.

    python auto_tag.py                    # all untagged images
    python auto_tag.py --dry-run          # print suggestions, write nothing
    python auto_tag.py --only 2024/05     # a sub-folder of images_dir
    python auto_tag.py --limit 10         # stop after 10 images

Each image tagged here gets "auto": true in the metadata file. Check them
afterwards with `python tagger.py --review`: saving an image there clears the flag.
"""
import argparse
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from store import Store, find_config
from suggest import suggest_tags


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch AI tagging of untagged images")
    parser.add_argument("--config", help="path to config.json (default: ./config.json, else the demo)")
    parser.add_argument("--dry-run", action="store_true", help="print suggestions, write nothing")
    parser.add_argument("--only", help="limit to a sub-folder of images_dir, e.g. 2024/05")
    parser.add_argument("--limit", type=int, help="maximum number of images")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    config_path = find_config(args.config)
    load_dotenv(config_path.parent / ".env")
    load_dotenv(Path(__file__).parent / ".env")
    store = Store(config_path)

    todo = store.untagged()
    if args.only:
        prefix = store.key_of(store.images_dir / args.only) + "/"
        todo = [k for k in todo if k.startswith(prefix)]
    if args.limit:
        todo = todo[: args.limit]

    print(f"⚙️  Config: {config_path}")
    print(f"🆕 {len(todo)} image(s) to tag" + (" (dry run)" if args.dry_run else ""))
    if not todo:
        return

    client = anthropic.Anthropic()
    candidates = store.candidate_tags()
    nsfw = {t.lower() for t in store.config["nsfw_tags"]}
    done, failed, flagged = 0, [], 0

    for i, key in enumerate(todo, 1):
        name = Path(key).name
        try:
            tags = suggest_tags(client, store.path_of(key), candidates, store.config)
        except anthropic.AuthenticationError:
            sys.exit("❌ No valid Anthropic credentials. Set ANTHROPIC_API_KEY in .env")
        except anthropic.APIError as e:
            print(f"❌ [{i}/{len(todo)}] {name}: API error ({e})")
            failed.append(key)
            continue

        if not tags:
            print(f"⚠️  [{i}/{len(todo)}] {name}: no suggestion, left untagged")
            failed.append(key)
            continue

        is_nsfw = any(t.lower() in nsfw for t in tags)
        flagged += is_nsfw
        print(f"🏷️  [{i}/{len(todo)}] {name} -> {' '.join(tags)}{' 🔞' if is_nsfw else ''}")
        if not args.dry_run:
            store.set_tags(key, tags, auto=True)  # saved after each image, safe to interrupt
        done += 1

    print(f"\n✅ {done} tagged, {len(failed)} failed")
    if flagged:
        print(f"🔞 {flagged} flagged NSFW")
    if failed:
        print("👉 Failed images stay untagged: tag them by hand with `python tagger.py`")
    if done and not args.dry_run:
        print("👉 Review the results: python tagger.py --review")


if __name__ == "__main__":
    main()
