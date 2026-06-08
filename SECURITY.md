# Security Policy

## Data Storage

Meeting Notes AI stores user data locally. By default, meeting outputs are written to `outputs/` and personal app data is written to `C:\Users\<you>\.meeting-notes-ai`.

Do not commit local outputs, todo files, config files, virtual environments, or build artifacts. The repository `.gitignore` excludes these paths.

## Startup Behavior

The app can create a user-level Windows Startup command file only when the user clicks `Enable Startup`. It does not install a Windows service and does not require administrator permission.

## Optional Encryption

Daily todo storage can be protected with a passphrase from the UI. The encrypted file is stored as `daily_todos.enc` in the local app data folder. Forgetting the passphrase means the encrypted todos cannot be recovered.

## Reporting Issues

If this project is later published, report security issues privately through the repository owner rather than opening a public issue with sensitive logs or transcripts.

