#!/bin/bash
# Boot script for the Check Before You Pay VM (Debian 12, e2-micro, us-central1). Runs on every boot and on each
# deploy, and is safe to rerun: it pulls the image named in instance metadata and restarts the app behind Caddy.
set -euo pipefail
md() { curl -fs -H 'Metadata-Flavor: Google' "http://metadata.google.internal/computeMetadata/v1/instance/attributes/$1"; }

# 1 GB of RAM is tight for the build-free app plus Caddy; swap keeps a spike from killing it.
if ! swapon --show | grep -q /swapfile; then
  [ -f /swapfile ] || { fallocate -l 1G /swapfile; chmod 600 /swapfile; mkswap /swapfile; }
  swapon /swapfile
  grep -q /swapfile /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi
command -v docker >/dev/null || { apt-get update -q; apt-get install -y -q docker.io; }
systemctl enable --now docker

IMAGE=$(md image)
HOST=$(md site-host)
mkdir -p /opt/cbyp/data
cat > /opt/cbyp/Caddyfile <<EOF
$HOST {
	encode gzip
	header Strict-Transport-Security "max-age=31536000"
	reverse_proxy app:8000
}
EOF

# The app's secrets arrive separately with gcloud compute scp, never through metadata.
for _ in $(seq 1 120); do [ -f /opt/cbyp/app.env ] && break; sleep 5; done
chmod 600 /opt/cbyp/app.env

gcloud auth print-access-token | docker login -u oauth2accesstoken --password-stdin https://us-central1-docker.pkg.dev
docker pull "$IMAGE"
docker network inspect cbyp >/dev/null 2>&1 || docker network create cbyp
docker rm -f app caddy >/dev/null 2>&1 || true
# The SQLite file lives in /opt/cbyp/data on the boot disk, so it survives restarts and redeploys.
docker run -d --name app --network cbyp --restart always --env-file /opt/cbyp/app.env \
  -v /opt/cbyp/data:/data "$IMAGE"
docker run -d --name caddy --network cbyp --restart always -p 80:80 -p 443:443 \
  -v /opt/cbyp/Caddyfile:/etc/caddy/Caddyfile:ro -v caddy_data:/data -v caddy_config:/config caddy:2.8
docker image prune -f >/dev/null

# Hourly online backup of the SQLite file (SQLite's backup API, so it's consistent while the app writes). Keeps 48.
command -v cron >/dev/null || { apt-get update -q; apt-get install -y -q cron; }
cat > /etc/cron.hourly/cbyp-backup <<'EOF'
#!/bin/sh
docker exec app python -c "
import os, pathlib, sqlite3, time
src = pathlib.Path(os.environ.get('SQLITE_PATH', '/data/app.db'))
out = pathlib.Path('/data/backups'); out.mkdir(exist_ok=True)
final = out / time.strftime('app-%Y%m%d-%H%M.db'); tmp = final.with_suffix('.tmp')
s = sqlite3.connect(f'file:{src}?mode=ro', uri=True); t = sqlite3.connect(tmp)
s.backup(t); t.close(); s.close(); os.replace(tmp, final)
" || logger -t cbyp-backup "backup failed"
rm -f /opt/cbyp/data/backups/*.tmp
ls -1t /opt/cbyp/data/backups/app-*.db 2>/dev/null | tail -n +49 | xargs -r rm -f
EOF
chmod 755 /etc/cron.hourly/cbyp-backup
systemctl enable --now cron
