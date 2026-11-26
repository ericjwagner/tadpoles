
# Tadpoles weekly photo sync
Uploads your child's photos from Tadpoles to Google Photos every week via
GitHub Actions. 

If this saves you time, buy me a coffee ☕

![Test](https://github.com/ericjwagner/tadpoles/actions/workflows/test.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.12-blue.svg)
[![Sponsor](https://img.shields.io/badge/sponsor-☕%20buy%20me%20a%20coffee-ff69b4?style=flat)](https://github.com/sponsors/ericjwagner)


<img width="1280" height="640" alt="social-preview" src="https://github.com/user-attachments/assets/7183dc15-b417-4c5f-bf8b-16e3bdbe53e1" />

## Why

My kid's daycare posts photos to [Tadpoles](https://www.tadpoles.com/) daily, but there's no way to bulk-export
just my kid's solo photos — the app makes you download one at a time, and
warns you before downloading any photo with other kids in it. This automates
the whole thing: pull the week's photos, keep only the ones where my kid is
the only one in frame, and land them in Google Photos without me touching
anything.

Tadpoles has no first-party API. This uses the unofficial mobile-app API
reverse-engineered by the community (e.g.
[tylerhall/tadpoles-api](https://github.com/tylerhall/tadpoles-api)).

> **Disclaimer:** This talks to a private, undocumented Tadpoles API endpoint
> that isn't officially supported. It could change or break at any time
> without notice, and using it is not endorsed by Tadpoles or Teaching
> Strategies (Tadpoles' owner). Use at your own risk.

## Setup

### Tadpoles

In repo Settings → Secrets and variables → Actions, add secrets:
- `TADPOLES_EMAIL` — your Tadpoles login email
- `TADPOLES_PASSWORD` — your **Tadpoles-specific** password (not Google/Apple sign-in;
  create one from the Tadpoles app/site if you normally log in another way)

Add a repo variable (Settings → Secrets and variables → Actions → Variables tab)
`TADPOLES_CHILD_NAME` — must exactly match how your child's name appears in
Tadpoles' `member_display` field.

### Google Photos

Use a Google Cloud project in **Personal mode**. Google says Personal mode apps
"are not subject to the OAuth user cap or 7-day test user token expiration",
so the refresh token doesn't need weekly rotation. An existing External
project can't be switched to Personal mode, so this needs a new project.

1. Signed in with the Google account whose Photos library gets the uploads,
   open the [Personal mode onboarding page](https://console.cloud.google.com/auth/overview/personal).
   Create or pick a project, set **Application type** to **Desktop app**,
   accept the terms, and click **Continue**. Copy the client ID and client
   secret. Google shows the full secret only once.
2. In the [API Library](https://console.cloud.google.com/apis/library) for
   that project, make sure the **Photos Library API** is enabled.
3. Get a refresh token with `get_google_token.py` (run it yourself, never in CI):
   - **Computer:** `pip install requests`, then `python get_google_token.py`.
     Enter the client ID and secret when asked. Approve access in the browser
     tab it opens.
   - **Phone:** on github.com, open this repo, tap **Code** → **Codespaces** →
     **Create codespace on master**. In the codespace terminal run
     `pip install requests && python get_google_token.py` (paste mode turns on
     automatically). Tap the printed link and approve access. Google then
     opens a `127.0.0.1` page that won't load. Copy that page's full address
     and paste it into the terminal. Delete the codespace when you're done.
4. Set three repo secrets: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`,
   `GOOGLE_REFRESH_TOKEN`.

Keep the old project until a sync with the new secrets works. If it fails,
put the old three secrets back.

<details>
<summary>Older setup: External + Testing project (token expires every 7 days)</summary>

With the OAuth consent screen set to **External** + **Testing**, Google
expires the refresh token 7 days after consent. Re-run `get_google_token.py`
and update `GOOGLE_REFRESH_TOKEN` every week.

</details>

The workflow runs every Sunday at 13:00 UTC, or trigger it manually from the
Actions tab ("Run workflow").

GitHub disables scheduled workflows in public repos after 60 days without
repository activity. `.github/workflows/keepalive.yml` runs every Wednesday:
it re-enables the sync workflow through the API and, only if the default
branch has had no commit for 40 days, pushes a one-line marker commit to
`.github/keepalive`. It never runs the sync, so it is safe to trigger by hand.

## Multi-child photo filtering

The Tadpoles app shows a confirmation prompt before downloading a photo that has
other kids tagged in it, but that's a client-side UI check — the events API has
no documented field naming which children are tagged in a photo. Instead, every
downloaded image is run through an offline face detector (OpenCV's YuNet model,
downloaded to `data/` on first use): photos with exactly one detected face are
uploaded, photos with more than one face are dropped. Videos aren't filtered
this way and are always uploaded.

This is verified by `test_face_filter.py` against real one-face/two-face fixture
photos, run automatically on every push by `.github/workflows/test.yml`.

## Avoiding duplicates

Uploaded attachment keys are tracked in `uploaded_keys.txt`, persisted between
runs via a GitHub Actions cache (not committed to the repo). The sync window is
8 days even though the cron is weekly, so a 1-day overlap is expected —
`uploaded_keys.txt` is what prevents re-uploading anything from that overlap.

## Local run

```
pip install -r requirements.txt
TADPOLES_EMAIL=you@example.com TADPOLES_PASSWORD=... \
GOOGLE_CLIENT_ID=... GOOGLE_CLIENT_SECRET=... GOOGLE_REFRESH_TOKEN=... \
python tadpole_sync.py
```

## Running tests

```
pip install -r requirements-dev.txt
pytest -v
```

## Known limitations

- Face detection can miss real faces at odd angles or in low light, which
  means the occasional solo photo gets skipped as if it had zero faces. See
  [Multi-child photo filtering](#multi-child-photo-filtering).
- With an External + Testing Google project, the refresh token expires every
  7 days. A Personal mode project avoids this. See the Google Photos setup
  section above.
- Only matches on a single child name (`TADPOLES_CHILD_NAME`); doesn't
  support syncing photos for multiple kids in one run.
- Depends on Tadpoles' undocumented API staying stable — see the disclaimer
  above.

## License

[MIT](LICENSE)
