# Fleet configuration (Ansible)

Codifies the production servers' host-level configuration — the things the
July 2026 remediation established by hand — so drift becomes a weekly diff
instead of a months-later incident:

| Role | Owns |
|---|---|
| `sshd_hardening` | `/etc/ssh/sshd_config.d/00-tailnet-hardening.conf` (key-only SSH, no root passwords) |
| `firewall` | ufw policies, tailnet SSH rule, Cloudflare-only 443, the canonical `MASCOPE NAT` masquerade block |
| `docker_daemon` | `/etc/docker/daemon.json` with `iptables: false` (load-bearing — see `docs/maintaining.md`) |
| `unattended_upgrades` | unattended security updates enabled |

The monitoring box (`ops`) is deliberately **not** in the fleet group — it
runs a different network model (stock Docker + `DOCKER-USER` rules).

## One-time setup (WSL on the admin workstation)

```sh
# in WSL (Ubuntu):
sudo apt update && sudo apt install -y pipx && pipx install --include-deps ansible
# the SSH key must live inside WSL with sane permissions:
mkdir -p ~/.ssh && cp /mnt/c/Users/<you>/.ssh/id_ed25519_mascope ~/.ssh/ && chmod 600 ~/.ssh/id_ed25519_mascope
```

Create your inventory (deliberately not committed — this repo is public and
the tailnet addresses stay out of it):

```sh
cp inventory.example.yml inventory.local.yml
# fill in each server's tailnet IP (see the private fleet docs, or
# `tailscale status` on any tailnet machine)
```

## Workflow: check first, apply deliberately

**Drift check** (read-only, safe anytime; `-K` prompts once for sudo):

```sh
ansible-playbook site.yml --check --diff -K
```

**Apply** — always canary-first, then the rest:

```sh
ansible-playbook site.yml -K --limit <canary-host>   # one server first
ansible-playbook site.yml -K                         # fleet
```

## Apply-time cautions

- The `docker_daemon` role's restart handler **restarts Docker = restarts the
  Mascope stack** (~30 s outage on that server). It only fires when
  `daemon.json` actually changed, which should be never once converged — but
  treat a non-empty diff there with respect and apply per-server.
- The first-ever run is a **migration**, not a no-op: servers provisioned
  before this role carry a hand-written `MASCOPE NAT` block (removed and
  replaced by the ansible-managed block, same semantics), and the two
  oldest-provisioned servers still persist equivalent NAT rules via
  `iptables-persistent` — harmless duplication that can be retired
  separately (see the private fleet docs for which servers).
- Cloudflare ranges are fetched live at run time; rules for ranges Cloudflare
  has *withdrawn* are not auto-pruned (same behavior as
  `tooling/ufw-allow-cf.sh`) — prune manually on the rare CF delisting.

## Suggested cadence

Weekly `--check --diff` (eyeball the diff, expect empty), plus a check run
before and after any manual server surgery. A cron wrapper that alerts on
non-empty diff can come later once the fleet has converged.
