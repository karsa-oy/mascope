# Hosting & deployment

How to run Mascope, from a one-machine trial to a shared production deployment.

## Managed hosting by Karsa

The simplest option is to let Karsa host Mascope for you - no servers, updates,
backups, or TLS to manage. Contact [sales@karsa.fi](mailto:sales@karsa.fi) for a
quote.

## Self-hosting

Mascope ships as Docker images on GHCR, orchestrated with Docker Compose.

### Local trial (one machine)

Run the HTTP release stack on `localhost` - no TLS, no build, just pull and run.
See [Getting started](user/getting-started/index.md). The web UI is served at
`http://localhost:8080`; loopback is a browser secure context, so everything
(including clipboard) works over plain HTTP.

### Shared / LAN / production (HTTPS)

For a deployment reached over the network by multiple users, serve over
**HTTPS**. This is not just good practice: browsers only treat `localhost` as a
secure context over plain HTTP, so over a LAN address features like clipboard
access require HTTPS.

1. **Prerequisites:** Docker + Docker Compose on a host your users can reach.
2. **Secrets** (in `.runtime/secrets/`): `postgres_password.txt`,
   `jwt_secret_key.txt`, `server_owner_secret_key.txt`, plus a TLS certificate
   (`mascope.app.pem` / `mascope.app.key`).
3. **TLS** - pick the option that fits your audience:
   - **Self-signed** (`mascope cert gen`): works immediately; each user clicks
     through a one-time browser warning. Fine for a small, trusted team. Make
     sure the certificate's SAN matches the hostname/IP people use.
   - **Internal CA** (e.g. [mkcert](https://github.com/FiloSottile/mkcert) or an
     org CA): warning-free on the LAN; install the CA certificate on client
     machines once, then issue a certificate for the server's hostname.
   - **Real certificate** via a domain + Let's Encrypt **DNS-01** (a reverse
     proxy such as Caddy or Traefik automates issuance/renewal): trusted, no
     warnings, no client setup. Needs a DNS name you control; DNS-01 does not
     require exposing the server to the internet.
4. **Start:** `mascope prod up` (uses `docker-compose.yaml`). The `db_init`
   container creates the database and applies migrations before the app starts.
5. **Persistence:** state lives under `.runtime/` (PostgreSQL data and the
   filestore). Back these up; see the database section of the developer guide.
6. **Upgrades:** pull a newer image and `mascope prod up` again - `db_init`
   applies pending migrations on start (taking a pre-migration backup first).

For the full operations reference (runtime, database tuning, backups, env sync,
deployment internals), see the
[developer guide](dev/developer_guide.md).
