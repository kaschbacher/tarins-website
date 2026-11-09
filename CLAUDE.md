# Tarin's Website

A static personal website: plain HTML, CSS and JavaScript, with no build step. Open the `.html` files in a browser to view them.

## Git workflow

- **Always make changes on a git branch, never directly on `main`.** Before editing, create a new descriptively named branch from an up-to-date `main` (for example `git checkout main && git pull && git checkout -b climbing-video-order`).
- Get changes into `main` through a pull request on GitHub (`kaschbacher/tarins-website`). Only commit, push or merge when asked.
- GitHub rejects files over 100 MB. Re-encode large videos before committing; macOS's built-in `avconvert` works, e.g. `-p Preset1280x720`.

## Site layout

- `index.html`: reading portfolio (book grid); `bookers/` has one review page per book.
- `about.html`: about page, including the honors certificates in `honors/`.
- `climbing.html` + `climbing.js`: climbing videos (`videos/`) and the climbing-wall mini-game.
- `thailand.html`: rotating photo grid drawn from `thailand_photos/`.
- `style.css`: shared stylesheet for every page.
- `archive/`, `updated_site_files/`: old copies, not linked from the site. `backup/` is git-ignored.

## Media conventions

- Use web-friendly formats: JPEG for photos and H.264 MP4 for video. HEIC only displays in Safari.
- Size images to about 2× their displayed CSS size so they stay sharp on Retina screens without bloating the repo.
- Video file names in the HTML must match the files' upper/lower case exactly; GitHub Pages and other Linux hosts are case-sensitive.
