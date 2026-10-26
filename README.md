# Sim Tac Toe

A browser-playable Unity WebGL game with a lightweight, static page wrapper.

Live site: https://tictactoe.salsaparapizza.com/

## Page design

The Paper Play wrapper uses warm paper colors, a serif title, an inset game frame,
and the game's red cross and turquoise ring. It includes a responsive layout,
a loading indicator, keyboard focus states, and a fullscreen button.

The compiled Unity files under `Build/` are unchanged. Keep the Unity configuration's
company and product names unchanged to preserve its browser storage identity.
The repository contains a built game, not the original Unity editor project.
Small-screen layout support does not imply touch support inside the compiled game.

Search metadata includes a title, description, canonical URL, crawler directives,
a sitemap, and `VideoGame` JSON-LD. Open Graph and Twitter card tags reference
an actual game screenshot. Metadata does not guarantee search indexing or ranking.

## Local preview and tests

Serve the project with Python:

```bash
python3 -m http.server 8765 --bind 127.0.0.1
```

Open http://127.0.0.1:8765/ in a WebGL 2 browser.

Run the dependency-free wrapper and metadata tests:

```bash
node --test tests/game.test.mjs
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

Browser acceptance checks must also confirm Unity startup, fullscreen entry and
exit, responsive layout, and the absence of page errors. Node tests simulate the
Unity API; they do not test gameplay.

## Publish from nuke

Commit the verified changes first. Then run:

```bash
python3 scripts/publish.py
newsite --check tictactoe
```

The script requires a clean checkout. It exports only committed `index.html`,
`favicon.ico`, `robots.txt`, `sitemap.xml`, `Build/`, and `TemplateData/` assets.
It creates a separate release under `~/.local/share/newsite/releases/tictactoe/`
and applies that path through `newsite`. Repository files, tests, scripts, and
untracked files are not published. Prior release directories remain available.
An identical existing release can be reapplied safely; modified releases are refused.

If an edge check fails, inspect `newsite --check tictactoe`. Do not assume that a
failed health check reverted the routing. For rollback, set `root` in
`~/sites/tictactoe/site.json` to a verified previous release and apply that manifest:

```bash
newsite --manifest ~/sites/tictactoe/site.json
```

## Asset sources

`TemplateData/favicon.svg` is the editable X/O icon. PNG, ICO, and Apple touch
exports use the same geometry. To regenerate icons and the social card, install
Pillow in a development environment and supply an actual 960×600 game screenshot:

```bash
python3 scripts/generate_assets.py --game-image /path/to/game.png
```

Runtime serving needs no Python packages, Node dependencies, or font services.
Self-hosted FreeSerif and Lato fonts include their copyright and license notices
under `TemplateData/fonts/`. Browsers load small Latin WOFF2 subsets; the original
TTF files remain available for regeneration. FreeSerif uses the GNU GPL with the Special
Font Exception; Lato uses the SIL Open Font License. Upstream FreeSerif sources:
https://www.gnu.org/software/freefont/ and https://ftp.gnu.org/gnu/freefont/.
