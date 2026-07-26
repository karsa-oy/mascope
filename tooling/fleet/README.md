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

## Sudo passwords: the vault (recommended)

The fleet has **no NOPASSWD sudo** and each server has its **own** sudo
password, so a single `-K` prompt cannot drive a whole-fleet run. Ansible Vault
solves this: store the per-host passwords once in an encrypted file, then unlock
them all with one prompt.

```sh
# Create the encrypted vault (you set a vault password; then paste each
# server's `karsa` sudo password from your password manager). Structure is in
# group_vars/fleet/vault.yml.example.
ansible-vault create group_vars/fleet/vault.yml
# Later edits:
ansible-vault edit group_vars/fleet/vault.yml
```

The real `vault.yml` is **gitignored** — never commit it, even encrypted (this
repo is public). Keep a copy of the vault password in your password manager;
losing it means recreating the vault, not a lockout (the servers are unchanged).

## Workflow: check first, apply deliberately

**Drift check** (read-only, safe anytime). With the vault, one vault-password
prompt covers the whole fleet:

```sh
ansible-playbook site.yml --check --diff --ask-vault-pass
```

**Apply** — always canary-first, then the rest:

```sh
ansible-playbook site.yml --ask-vault-pass --limit <canary-host>   # one server first
ansible-playbook site.yml --ask-vault-pass                         # fleet
```

*No vault?* Drop `--ask-vault-pass`, add `-K`, and always `--limit <host>` so
the single sudo prompt matches exactly one server:

```sh
ansible-playbook site.yml --check --diff -K --limit <host>
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
