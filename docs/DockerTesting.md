Building and testing with Docker (short guide)

This project supports running the FastAPI app and the test suite inside Docker containers.

Build with a GitHub token (used when requirements.txt contains private git dependencies)

1. Export your GitHub Personal Access Token in PowerShell (temporary):

```powershell
# Replace with your token (do not commit)
$env:GITHUB_TOKEN = 'ghp_...'
```

2. Build images with Docker Compose (Compose v2):

```powershell
# from the repository root
docker compose build
```

3. Start the API (foreground):

```powershell
docker compose up
```

Or detached:

```powershell
docker compose up -d
```

Run the test service

The repository includes a short-lived `test` service that runs `pytest` inside the same image.

```powershell
docker compose run --rm test
```

Cleanup token

After the build/run, remove the token from your session:

```powershell
Remove-Item Env:\GITHUB_TOKEN
```

Notes

- If you prefer to avoid passing a token, you can edit or remove the private git dependency from `requirements.txt` (not recommended if tests depend on it).
- If pip fails compiling native extensions, consider adjusting the `Dockerfile` to include additional system packages or using a wheelhouse.
- The API listens on port 8000 inside the container and is mapped to the same port on the host by default.

Troubleshooting

- If you see "could not read Username for 'https://github.com'" during pip install, confirm `GITHUB_TOKEN` is exported in the shell you use to run `docker compose build`.
- If the build step takes long, it may be downloading many packages or building wheels; consider using a faster network or prebuilding wheels.
