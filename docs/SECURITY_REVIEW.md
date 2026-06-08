# Security Review

Date: 2026-05-30

## Threat Model Summary

Meeting Notes AI is a local-first desktop app. Primary sensitive data includes:

- meeting transcripts and summaries,
- daily todo/history content,
- local configuration,
- optional local AI/Ollama settings.

Primary trust boundaries:

- microphone/loopback audio input,
- local filesystem output folders,
- optional localhost Ollama endpoint,
- optional user-level Windows Startup shortcut.

## Security Controls Present

- No paid cloud API key is required for normal operation.
- Meeting outputs are local files, not uploaded by the app.
- Optional todo encryption uses passphrase-derived Fernet encryption with PBKDF2-HMAC-SHA256 and a random salt.
- Startup behavior is user-level only and does not install a privileged Windows service.
- `.gitignore` excludes generated outputs, local config/secrets, virtual environments, and build artifacts.
- Launch wrapper catches startup failures and shows a user-visible error instead of failing silently.

## Secret Scan

The source tree was scanned for common secret patterns including API keys, bearer tokens, GitHub PATs, OpenAI keys, private keys, authorization headers, and `HF_TOKEN`.

Result: no credential values found. The only public-scope matches were `.gitignore` rules that intentionally exclude local secret/config folders.

Excluded from the scan:

- `.venv`,
- `outputs*`,
- `ouputrs`,
- `__pycache__`,
- `build`,
- `dist`.

## Findings

No high-risk security findings were identified in the current local-app threat model.

## Residual Risks

- If users publish real `outputs/` files, transcripts may contain private meeting content.
- If users forget the todo encryption passphrase, encrypted todos cannot be recovered.
- Unsigned executables may trigger Windows SmartScreen warnings.
- Ollama, if enabled, receives meeting text over localhost. This is local, but users should still treat installed local models/services as trusted software.

## Recommendations Before Public GitHub Release

- Review `LICENSE` and `THIRD_PARTY_NOTICES.md` before public release.
- Keep sample outputs synthetic only.
- Do not commit generated installer binaries unless using GitHub Releases intentionally.
- Consider adding GitHub secret scanning and Dependabot after publishing.
- Consider a reproducible release workflow later if distributing binaries to other users.
