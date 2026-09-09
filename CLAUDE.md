# discord-bump-bot

Automated DISBOARD `/bump` sender for two Discord servers, run entirely on GitHub Actions.
This is the backend for **BumpPilot** (bumppilot.xyz), a paid bump-service — see `Ssiemka/bumppilot`
for the sales site. Paying customers now depend on this repo staying reliable.

## Architecture

- `bump.py` — single-run script. Reads config from env vars, waits out DISBOARD's 2h cooldown if
  needed (by checking the channel's message history for DISBOARD's last post), then sends the
  `/bump` interaction directly against Discord's private API using a **user account token**
  (not a bot token — this is a self-bot).
- `.github/workflows/bump-gotryl.yml` and `bump-complx.yml` — one workflow per server. Each sets
  `GUILD_ID`, `CHANNEL_ID`, `SERVER_NAME` and runs `python bump.py`.
- `.github/workflows/keepalive.yml` — commits a timestamp file every 10 days so the repo never
  hits 60 days of inactivity (see Known failure modes below).
- **Trigger**: cron-job.org calls the GitHub API to fire `workflow_dispatch` on each bump workflow
  every 2 hours. **This is the only trigger** — the workflows do not have a `schedule:` block
  (removed 2026-09-09, see below). If cron-job.org is down, no bumps happen; there is no fallback.

## Server IDs

| Server | Guild ID | Channel ID |
|---|---|---|
| Gotryl | 1490990573388300399 | 1496869622195032295 |
| ComplxCulture | 1267422282134061129 | 1367544832360317020 |

## Secrets

`DISCORD_TOKEN` is a GitHub Actions secret (repo Settings → Secrets). **Never print, log, or
commit it** — this repo is public. `bump.py` reads it only from `os.environ`.

## Known failure modes

- **GitHub disables scheduled workflows after 60 days of repo inactivity.** This previously broke
  the bot (Aug 2026): the disabled workflow made cron-job.org's dispatch calls fail, and
  cron-job.org auto-disabled its own jobs after enough HTTP errors. Fixed by `keepalive.yml`.
  If the bot goes silent again, check keepalive is still running and cron-job.org's jobs are
  still enabled — both can be silently disabled independently.
- **Double-trigger bug (fixed 2026-09-09).** Both workflows used to have a `schedule:` cron
  *and* cron-job.org calling `workflow_dispatch`, firing independently every ~2h each. This
  caused overlapping runs roughly every 1–1.5h instead of 2h, which collided with DISBOARD's
  cooldown and caused ~1 in 3 runs to fail — and doubled how often the account hit Discord's API,
  raising ban risk. Fixed by removing `schedule:` and keeping `workflow_dispatch:` as the sole
  trigger. **Do not re-add a `schedule:` block without also handling cooldown collisions**, or
  this bug returns.
- **No per-request timeout on the old `aiohttp.ClientSession`** meant a stalled Discord API call
  could hang a job for hours with no error (GitHub Actions' default job timeout is 6h). Fixed by
  setting `ClientTimeout(total=60)` on the session (2026-09-09). Job-level `timeout-minutes: 130`
  is also set as a backstop — kept above `COOLDOWN_SECS` (~120.5 min) so it never kills a
  legitimate cooldown wait.

## Timing

Bumps fire at a fixed `COOLDOWN_SECS` (2h0m30s) after the previous one — deterministic, no
jitter, by explicit owner choice (2026-09-09) after being told a perfectly regular interval is
itself a bot fingerprint and increases ban exposure. A jittered version (random 1–10 min delay
after cooldown clears) was shipped and then reverted same-day at the owner's request — see git
history around commits `48886fb` / this one if reconsidering.

## Ban risk — read before changing anything that increases exposure

This automates a **Discord user account** to call `/bump`, which violates both Discord's and
DISBOARD's Terms of Service. It works today because request timing and headers mimic a real
client closely enough. Paying BumpPilot customers are now exposed to this risk on their servers.
Before suggesting anything that increases exposure (faster cadence, more parallel requests,
skipping the cooldown check, reusing tokens across more servers, etc.), flag the risk explicitly
and let the human decide — don't just implement it.

## Related

- `Ssiemka/bumppilot` — the sales site (GitHub Pages, bumppilot.xyz), Stripe Payment Links,
  Web3Forms order delivery.
