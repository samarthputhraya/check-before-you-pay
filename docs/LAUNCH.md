# Launch checklist (Fri 30 Oct, morning)

Do these in order before the creators post.

## 1. Start the numbers from zero (5 min)
`/stats` currently counts our own testing. Clear it once, right before launch, so every number we pitch is real:

```bash
gcloud compute ssh cbyp-web --zone us-central1-a --command "
  sudo docker stop app &&
  sudo mkdir -p /opt/cbyp/data/backups &&
  for f in /opt/cbyp/data/app.db*; do sudo mv \$f /opt/cbyp/data/backups/pre-launch-\$(basename \$f); done &&
  sudo docker start app && sleep 5 && sudo docker exec app python -m seed.load"
```

- The old file is kept in `backups/` and never deleted.
- `seed.load` puts back the labelled sample ring (`/c/chk_sample02`). Sample checks never count in `/stats`.
- **Check it worked:**
  - https://34-45-129-243.sslip.io/stats shows "No checks yet";
  - https://34-45-129-243.sslip.io/api/health returns `"ok":true`.

## 2. Prime the demo (2 min)
On the demo phone, run the pitch's message 1 once (`docs/pitch.md`, section 3), so the second message has an earlier check to link to. After this, use only test IDs that start with `u_test`.

## 3. Share the link
- **The link:** https://34-45-129-243.sslip.io
- **The QR code:** [`docs/qr-live.png`](qr-live.png). It carries `?ref=u_qr_poster`, so visits from posters and slides show up as `ref_visit` events with that ref.
- **For creators:** one line plus the link: "Got a stock-tip or 'guaranteed returns' message? Check it before you pay, in your language."
  - Suggest they record a check of a real message they've received, with names cropped out.
  - Then the quiz: https://34-45-129-243.sslip.io/quiz.

## 4. Watch it during the day
- **Live numbers:** `/stats`, which refreshes every 30 s.
- **Downtime alert:** Google Cloud checks `/api/health` every 5 minutes from Asia, the US and Europe. If it fails from 2 or more regions for 10 minutes, Samarth gets an email. That's uptime check `cbyp-health` and alert policy "Check Before You Pay is down".
- **Measured headroom (29 Oct, 23:20):**
  - 30 simultaneous cached checks: all succeeded, at 1.3 s typical.
  - 12 simultaneous fresh checks in 5 languages: all complete, at 3.2 s typical and 3.5 s at worst.
- **Health:** `/api/health`. If `llm` says `down`, the Gemini quota or key is the first suspect.
- **Logs:** `gcloud compute ssh cbyp-web --zone us-central1-a --command "sudo docker logs --tail 100 app"`. They never contain message text.
- **Backups** run every hour to `/opt/cbyp/data/backups/`, which keeps the latest 48. For an off-machine copy:

  ```bash
  curl -H "Authorization: Bearer $ADMIN_TOKEN" https://34-45-129-243.sslip.io/api/admin/export -o backup.db
  ```

  The admin token is in `.env.railway`. Keep `backup.db` private, and never commit it.

## 5. Redeploy after a fix
Merge into `main`, then run `bash deploy/gce/deploy.sh`. It takes about 4 minutes and the site is down for about 10 seconds of it. Avoid deploying in the middle of a creator's live session.
