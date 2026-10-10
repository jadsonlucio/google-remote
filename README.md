# gtv-remote

Menu-bar virtual remote for Google TV. Uses the Android TV Remote protocol v2 over Wi-Fi (no Bluetooth).

## Run
```bash
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/python -m gtv_remote
```
A 📺 icon appears in the menu bar. On first launch it searches for TVs, then asks for the 6-character code the TV shows. macOS may ask for Local Network permission: allow it.

Icon: 📺 connected · 📺… connecting · 📺✕ unreachable (retrying) · 📺? needs pairing.

## Keyboard (remote window focused)
Arrows = D-pad · Return = OK · Esc/Backspace = Back · H = Home · S = Settings · +/- = volume · M = mute · Space = play/pause · ⌘P = power

## Files
Certificate, key and saved TV live in `~/.config/gtv-remote/` (override with `GTV_REMOTE_HOME`). Delete that folder to start over.

## Tests
```bash
.venv/bin/pytest
```

## Manual checklist (real TV)
- [ ] Find TV, pair with the code
- [ ] Every button works; keyboard shortcuts work
- [ ] Text input reaches a TV search field
- [ ] Put TV to sleep and wake it: status goes ✕ then back to connected
- [ ] Delete `cert.pem`/`key.pem`: app asks to re-pair
- [ ] Brightness ☀ keys: note whether the projector reacts (experimental). If not, use ⚙ Settings + D-pad.
