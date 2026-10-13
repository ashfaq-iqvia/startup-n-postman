# startup

Local helper scripts. Install Python dependencies with:

```bash
pip install -r requirements.txt
```

## Postman API key

These scripts call the Postman API and need a key:

- `paste-to-postman.py`
- `create-postman-collection.py`
- `list-postman-collections.py`

The key is read in this order:

1. The `POSTMAN_API_KEY` environment variable.
2. The first line of `pm-api-key.txt` in this folder.

Create the file with only the key on the first line:

```text
PMAK-your-postman-api-key
```

`pm-api-key.txt` is gitignored. Generate a key in Postman under **Settings → API keys**.

To set the environment variable for your Windows user instead:

```powershell
[System.Environment]::SetEnvironmentVariable("POSTMAN_API_KEY", "PMAK-your-postman-api-key", "User")
```

Open a new terminal after setting it so the scripts can see the variable.

The other scripts in this folder do not use that key. AWS scripts expect an existing AWS CLI profile named `devCluster`.
