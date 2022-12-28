### Mascope build/deploy infrastructure

Mascope build/deploy configurations are stored in .env files from corresponding folders.

The .envs are in git and keep values for supposed target systems (ips, ports, vagrant dir mounts).

All the packages can be re-built/re-deployed from updated sources or .envs by corresponding build.cmd/deploy.cmd scripts.

After installed, mascope persistently keeps its config in resulting .env files:
 - win.dev: in the project root;
 - linux: in $HOME/.local/bin/.env
and they are re-written after each reinstall. These .envs matter for mascope re-start.

In the current frontend design, corresponding .env (ip, port) is also used at build step (generating static web server code) - 
so after updating environment, bundle mascope rebuild/redeploy is advisable via corresponding script.

For debug purposes one may need to modify .env values. To avoid git complaints, parallel .debug_env files are introduced. 
Their values override those from corresponding .env. They are git-ignored.
