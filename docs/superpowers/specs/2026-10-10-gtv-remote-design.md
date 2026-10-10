# Google TV Virtual Remote — Design

Date: 2026-10-10

## Goal
A macOS menu-bar app that replaces a broken Bluetooth remote for a Google TV. It talks to the TV over the local network using the Android TV Remote protocol (v2), so no Bluetooth is needed. Personal daily use; get to a working remote quickly.

## Assumptions
- Mac and TV are on the same Wi-Fi/LAN.
- The TV shows a 6-digit pairing code once; afterwards the saved certificate authenticates the Mac.

## Non-goals (v1)
Phone/web access, app launching, voice, global hotkeys (need Accessibility permission).

## Approach
Python core using `androidtvremote2` (handles mDNS discovery, pairing, TLS certs, key and text commands) plus a `rumps` menu-bar UI with a floating remote window.

## Architecture
Two units:
- `tv_client` — the only code touching the network/protocol library.
- `app` — UI and keyboard input; never imports the protocol library directly (so tests can use a fake client).

`tv_client` runs on a background asyncio loop. The UI (AppKit main thread) sends commands via a thread-safe queue.

## `tv_client` interface
- `discover() -> list[Tv]` — mDNS (`_androidtvremote2._tcp`), manual-IP fallback.
- `pair(tv, code_provider)` — TV shows a 6-digit code; app prompts for it. Cert/key stored in `~/.config/gtv-remote/` with `0600` permissions.
- `connect()` — auto-reconnect with backoff. Status: `disconnected | connecting | ready | needs_pairing`.
- `send(key)` — `Key` enum: UP, DOWN, LEFT, RIGHT, OK, BACK, HOME, VOL_UP, VOL_DOWN, MUTE, POWER, PLAY_PAUSE, etc.
- `send_text(str)` — types into the TV's focused text field.

## UI
- Menu-bar icon, colour reflects connection status.
- Click opens a floating remote: D-pad with OK in the centre; Back/Home/Power row; volume and mute; play/pause; text field + Send.
- Menu items: Change TV, Re-pair, Quit.

## Keyboard (when remote window is focused)
Arrows = D-pad, Enter = OK, Esc/Backspace = Back, H = Home, +/- = volume, M = mute, Space = play/pause, Cmd+P = power.

## Error handling
- TV asleep/off: show "TV unreachable", retry quietly with backoff; Power sends wake.
- IP change: rediscover by saved device name/ID.
- Cert rejected: status `needs_pairing`, offer re-pair.
- Key sent while disconnected: dropped, status flashed. Keys are never queued (a stale OK could trigger something unwanted).

## Testing
- Unit tests: key map, status state machine, backoff — using a fake client.
- Manual checklist against the real TV: pair, send each key, text input, reconnect after TV sleep, re-pair after cert deletion.

## Storage
`~/.config/gtv-remote/` — certificate, key, saved TV (name/ID/last IP).
