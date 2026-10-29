# Listen backend handoff

Rishabh: request `GET /api/check/{check_id}/audio` when Listen is tapped and play
the `audio/mpeg` response. Show loading while it loads; a JSON 503 with
`error.code: audio_unavailable` means show a retry option. A 404 means the check
does not exist. No frontend files are changed in this PR.

The speech is the masked public headline, explanation and first next step in
their stored language. Gemini auto-detects the language of that text. It uses
the existing discovered TTS model (`GEMINI_TTS_MODEL`, when set, must be in the
available model list), with the prebuilt Kore voice. No source message, signal
quote, transcript or URL is included. The wrapper validates WAV or explicitly
typed little-endian PCM and ffmpeg converts it to mono MP3. Docker already
installs ffmpeg; local development needs it on PATH. Audio too long to fit is
rejected rather than cutting off advice.

SQLite stores the successful MP3 per check and content digest, on the existing
persistent volume. A fixed set of locks prevents duplicate synthesis in the
documented single-worker deployment. Provider failures are not cached and can
be retried. Multiple workers would need a distributed generation lease.
Provider timeout: 8 seconds; MP3 encoding: 5 seconds; complete request budget: 14 seconds including queue
wait. Failed conversion or storage returns the same plain 503, without logging
provider details. Audio adds at most about 480 KB per generated check; monitor
the persistent volume as usage grows.

## Acceptance still needed after deployment

On Android Chrome, create Hindi and Tamil checks using `u_test` IDs. Play each
verdict, confirm all three pieces are spoken naturally in the chosen language,
and time the first play. Reload and replay to verify the cache. Have native
speakers check pronunciation. Record device, time, check IDs and result; offline
codec tests do not establish provider quality or phone playback.

References: [Google Gen AI Python speech API](https://googleapis.github.io/python-genai/)
and [Google speech formats](https://ai.google.dev/gemini-api/docs/speech-generation).
ffmpeg options were checked against the installed `ffmpeg -h full` help.
