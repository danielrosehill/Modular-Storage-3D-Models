"""Publish the staged `models/` tree to Sketchfab and file it under a collection.

    export SKETCHFAB_API_TOKEN=...
    python3 scripts/upload_sketchfab.py --dry-run     # show what would go up
    python3 scripts/upload_sketchfab.py               # actually publish

Reads each `models/<CODE>/upload.json` written by stage_models.py and POSTs the
matching GLB. Results land in `models/uploads.json` as code -> uid/url, which is
what makes this safe to re-run: a code already recorded there is skipped rather
than uploaded a second time. That file is also the input for the README table,
so the published links are never transcribed by hand.

API notes, verified 2026-07-25 against api.sketchfab.com/v3:

- Auth is `Authorization: Token <token>`, not Bearer.
- Upload is multipart/form-data to POST /v3/models. `tags` is a repeated field,
  so it goes in as a list of (key, value) pairs rather than one joined string.
- A 201 means the file was accepted, NOT that the model is ready - processing is
  asynchronous. Poll GET /v3/models/{uid} until `status.processing` leaves
  PENDING/PROCESSING. A model still processing has no working thumbnail yet.
- `private` requires a paid plan. On a basic account everything published here is
  public the moment it finishes processing.
- Adding to a collection is POST /v3/collections/{uid}/models with a JSON body
  {"models": [uid, ...]}, and it only works once the model exists.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parent.parent
MODELS = REPO / "models"
LEDGER = MODELS / "uploads.json"

API = "https://api.sketchfab.com/v3"
COLLECTION_UID = "e206fcdf09b2497fa9219ac8d46f5163"      # "Industrial Storage"

POLL_INTERVAL = 5
POLL_LIMIT = 60          # 5 minutes; these are ~100 KB files, so this is slack


def auth_headers(token):
    return {"Authorization": f"Token {token}"}


def load_ledger():
    if LEDGER.exists():
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    return {}


def save_ledger(ledger):
    LEDGER.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")


def upload_one(token, code, payload, glb):
    """POST one GLB. Returns the new model uid."""
    data = [
        ("name", payload["name"]),
        ("description", payload["description"]),
        ("license", payload["license"]),
        ("isPublished", "true"),
    ]
    data += [("tags", t) for t in payload["tags"]]

    with glb.open("rb") as fh:
        resp = requests.post(
            f"{API}/models",
            headers=auth_headers(token),
            data=data,
            files={"modelFile": (glb.name, fh, "model/gltf-binary")},
            timeout=180,
        )

    if resp.status_code != 201:
        raise RuntimeError(
            f"{code}: upload returned HTTP {resp.status_code}: {resp.text[:400]}")

    uid = resp.json().get("uid")
    if not uid:
        raise RuntimeError(f"{code}: 201 but no uid in response: {resp.text[:400]}")

    return uid


def wait_processed(token, uid):
    """Block until Sketchfab finishes processing. Returns the final status."""
    for _ in range(POLL_LIMIT):
        resp = requests.get(f"{API}/models/{uid}", headers=auth_headers(token),
                            timeout=60)
        if resp.status_code == 200:
            status = (resp.json().get("status") or {}).get("processing")
            if status not in ("PENDING", "PROCESSING"):
                return status
        time.sleep(POLL_INTERVAL)
    return "TIMEOUT"


def make_downloadable(token, code, uid):
    """Downloadable is the point of a free CC BY asset, and on a Basic plan a model
    published NON-downloadable spends one of the 10 monthly upload credits.

    Verified 2026-11-18: the upload POST ignores isDownloadable, and a PATCH sent
    straight after the 201 is lost for some models (9 of 21 reverted to False) -
    processing overwrites it. So PATCH only once processing has finished, and read
    it back with an AUTHENTICATED GET; the anonymous GET is cached and lags.
    """
    for _ in range(3):
        requests.patch(f"{API}/models/{uid}", headers=auth_headers(token),
                       json={"isDownloadable": True}, timeout=60)
        time.sleep(2)
        got = requests.get(f"{API}/models/{uid}", headers=auth_headers(token),
                           timeout=60).json().get("isDownloadable")
        if got:
            return True
    print(f"  {code}: still not downloadable after 3 PATCHes")
    return False


COLLECTION_BATCH = 24   # API rejects more per request (HTTP 400, 2026-11-18)


def add_to_collection(token, uids):
    results = []
    for i in range(0, len(uids), COLLECTION_BATCH):
        resp = requests.post(
            f"{API}/collections/{COLLECTION_UID}/models",
            headers={**auth_headers(token), "Content-Type": "application/json"},
            data=json.dumps({"models": uids[i:i + COLLECTION_BATCH]}),
            timeout=60,
        )
        results.append(f"{resp.status_code} {resp.text[:200]}")
    return "; ".join(results)


def refresh_ledger(token):
    """Pull the canonical URLs and thumbnails back out of the API.

    The upload response only carries the uid, and `https://sketchfab.com/3d-models/
    <uid>` does resolve - but the URL Sketchfab actually publishes is slugged,
    `.../euro-stacking-container-600-x-400-x-230-mm-<uid>`. That is the one worth
    putting in the README, so it is read back rather than constructed.
    """
    ledger = load_ledger()
    for code, entry in sorted(ledger.items()):
        resp = requests.get(f"{API}/models/{entry['uid']}",
                            headers=auth_headers(token), timeout=60)
        if resp.status_code != 200:
            print(f"  {code}: HTTP {resp.status_code}, left as-is")
            continue
        body = resp.json()
        entry["url"] = body.get("viewerUrl", entry["url"])
        entry["embed"] = body.get("embedUrl", entry.get("embed"))
        entry["status"] = (body.get("status") or {}).get("processing", "?")
        thumbs = (body.get("thumbnails") or {}).get("images") or []
        if thumbs:
            widest = max(thumbs, key=lambda t: t.get("width", 0))
            entry["thumbnail"] = widest["url"]
        print(f"  {code:9s} {entry['status']:10s} {entry['url']}")
    save_ledger(ledger)
    print(f"\nrefreshed {len(ledger)} entries in {LEDGER.relative_to(REPO)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", help="comma-separated codes, e.g. EU6423,PB1")
    ap.add_argument("--refresh", action="store_true",
                    help="re-read every uid in the ledger and update its URLs")
    args = ap.parse_args()

    token = os.environ.get("SKETCHFAB_API_TOKEN")
    if not token and not args.dry_run:
        sys.exit("SKETCHFAB_API_TOKEN is not set")

    if args.refresh:
        refresh_ledger(token)
        return

    wanted = set(args.only.split(",")) if args.only else None
    ledger = load_ledger()

    folders = sorted(p for p in MODELS.iterdir()
                     if p.is_dir() and (p / "upload.json").exists())

    todo = []
    for folder in folders:
        code = folder.name
        if wanted and code not in wanted:
            continue
        if code in ledger:
            print(f"  skip {code}: already uploaded as {ledger[code]['uid']}")
            continue
        todo.append((code, folder))

    if not todo:
        print("nothing to upload")
        return

    print(f"\n{len(todo)} model(s) to publish, licence "
          f"{json.loads((todo[0][1] / 'upload.json').read_text())['license']}, "
          f"public, into collection {COLLECTION_UID}\n")

    for code, folder in todo:
        payload = json.loads((folder / "upload.json").read_text(encoding="utf-8"))
        glb = folder / f"{code}.glb"
        size_kb = glb.stat().st_size / 1024
        print(f"  {code:9s} {payload['name'][:44]:46s} {size_kb:6.1f} KB "
              f"{len(payload['tags'])} tags")
        if args.dry_run:
            continue

        uid = upload_one(token, code, payload, glb)
        status = wait_processed(token, uid)
        make_downloadable(token, code, uid)
        url = f"https://sketchfab.com/3d-models/{uid}"
        ledger[code] = {
            "uid": uid,
            "url": url,
            "embed": f"https://sketchfab.com/models/{uid}/embed",
            "name": payload["name"],
            "status": status,
        }
        save_ledger(ledger)
        print(f"             -> {uid}  {status}")

    if args.dry_run:
        print("\ndry run, nothing uploaded")
        return

    uids = [v["uid"] for v in ledger.values()]
    print(f"\ncollection add: {add_to_collection(token, uids)}")
    print(f"ledger written to {LEDGER.relative_to(REPO)}")


if __name__ == "__main__":
    main()
