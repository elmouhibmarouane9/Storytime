# Deploying MIM to Hugging Face Spaces (free, permanent URL)

Hugging Face gives you a permanent `https://<user>-<space>.hf.space` address on the free
tier. The container disk is **ephemeral**, so pair it with the GitHub storage backend —
then the book lives in your repo and the Space is just the UI.

## 1. Create the Space

1. huggingface.co → **New → Space**
2. Name it `mim`, SDK **Streamlit**, hardware **CPU basic (free)**, visibility **Private**
3. Create

## 2. Add the README frontmatter

HF identifies a Space by YAML frontmatter at the very top of `README.md`. Prepend this to
your copy of `README.md`:

```yaml
---
title: MIM Ops Console
emoji: ◆
colorFrom: yellow
colorTo: gray
sdk: streamlit
sdk_version: 1.40.0
app_file: streamlit_app.py
pinned: false
---
```

## 3. Push the code

```bash
git remote add space https://huggingface.co/spaces/<your-user>/mim
git push space arena/01a10c7b-storytime:main
```

(HF builds from `main` in the Space repo, whatever your local branch is called.)

## 4. Set the secrets

Space → **Settings → Variables and secrets** — add these as *secrets*:

| Name | Value |
|---|---|
| `MIM_ACCESS_CODE` | `openssl rand -hex 12` |
| `GITHUB_TOKEN` | a fine-grained token with **Contents: read/write** on your data repo only |
| `MIM_DATA_REPO` | `your-user/mim-book` (a **private** repo, created empty) |

The Space restarts and pulls the book from that repo. Every save in the console becomes a
commit in `mim-book` — your data, your history, your restore points.

## 5. Everyday use

- **URL:** `https://<your-user>-mim.hf.space` — permanent, HTTPS, shareable.
- **Book:** `github.com/your-user/mim-book` — plain JSON, diffable, restorable.
- **Updates:** `git push space arena/01a10c7b-storytime:main` rebuilds the Space.
- **Offline copy:** Settings → Book → Export.

Free Spaces sleep after inactivity and wake on the next request — expect a few seconds of
cold start. The book is unaffected either way, because it is not on the Space's disk.
