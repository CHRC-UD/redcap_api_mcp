# REDCap API MCP

A local, stdio-only MCP server for safely reading REDCap project metadata and bounded data previews. It has no import, update, delete, file, or dataset-export capability.

## Before you start

You need:

- A Mac or Windows computer with Python 3.11 or later. [Download Python](https://www.python.org/downloads/) if needed. On Windows, select **Add Python to PATH** during installation.
- Permission to create a REDCap API token for the project you will use. Ask your REDCap administrator if you do not have this.
- Git, only if you want to download updates with `git pull`. [Download Git](https://git-scm.com/downloads) if needed.
- Codex, Claude Desktop, or Claude Code installed on the same computer.

This tool reads data only. It cannot add, edit, delete, import, download files, or save a dataset to your computer.

## First-time installation

Open **Terminal** on a Mac or **PowerShell** on Windows. Copy one command at a time, press Enter, and wait for it to finish.

### 1. Download this repository

Choose a folder where you keep software projects, then run:

```sh
git clone https://github.com/CHRC-UD/redcap_api_mcp.git
cd redcap_api_mcp
```

If you do not have Git, select **Code** then **Download ZIP** on the GitHub page, unzip it, and open Terminal/PowerShell in the unzipped `redcap_api_mcp` folder. You will need Git later to use the update instructions below.

### 2. Create the app's private Python environment

This keeps the tool's software separate from the rest of your computer.

On a Mac:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
```

On Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install .
```

If PowerShell says that scripts are disabled, close it, open PowerShell normally (not as Administrator), and run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. Then repeat the Windows commands.

### 3. Connect your REDCap project

With the private environment still active, run:

```sh
redcap-mcp setup
```

It asks for a simple profile name, your REDCap API URL, and your API token. Paste the token only into this prompt—never into chat, email, a document, or this repository. The token and the secret used to create safe record aliases are stored in your Mac Keychain or Windows Credential Manager. The configuration file does not contain the token.

### 4. Add it to your chat app

Run one command for the app you use:

```sh
redcap-mcp configure codex
redcap-mcp configure claude-desktop
redcap-mcp configure claude-code
```

Each command creates a backup before changing the app's configuration. Quit and reopen the chat app after running it. You do not normally need to run `redcap-mcp serve` yourself—the app starts it when needed.

### Claude Science (recommended for scientific work)

Claude Science supports this project as a **Local command** connector. First complete `redcap-mcp setup` in Terminal, as described above. Then, in the Claude Science app:

1. Open **Settings** → **Connectors** → **Add connector**.
2. Choose **Local command** (not Remote).
3. Enter the name `redcap-api`.
4. For **Command**, enter the command for your computer:

   - Mac: `/full/path/to/redcap_api_mcp/.venv/bin/redcap-mcp`
   - Linux: `/full/path/to/redcap_api_mcp/.venv/bin/redcap-mcp`

5. Open **Advanced settings**. For **Arguments**, add `serve`. Do not add an API token, REDCap URL, or any environment variables.
6. Select **Add connector**. Leave every tool set to **Ask each time** unless your organization has approved a different setting.

Replace `/full/path/to` with the folder where you downloaded this repository. For example, if it is in your home folder, the Mac command could be `/Users/your-name/redcap_api_mcp/.venv/bin/redcap-mcp`.

This is a local connector: it runs on your computer and connects directly to your REDCap site. Do not choose **Remote** or paste your REDCap URL/token into the connector screen.

For **Claude Desktop**, use the `redcap-mcp configure claude-desktop` command above. For **Claude Code**, use `redcap-mcp configure claude-code`.

#### Claude Science troubleshooting: “Operation not permitted”

Claude Science runs local connectors in a sandbox. Before adding the connector, open or create the Claude Science project where you will use REDCap and grant it **Read-only** access to the folder that contains this repository (for example, `/Users/your-name/redcap_api_mcp`). You can do this by typing the folder path in the chat or selecting it with the **@** folder picker, then approving the folder-access card.

Next, remove the failed connector and add it again using the exact command path from that granted folder. If you then see a request to reach `redcap.chrc.udel.edu`, approve that specific host. Do not approve unrelated hosts. Claude Science will not be able to start a local command outside its permitted folders or contact a network host until you approve it.

## Generic instructions: add this MCP server to another supported app

Most desktop AI apps that support **local MCP servers** ask for a command and optional arguments. First install and set up this project as described above. Then add a new local/stdio MCP server with:

| Setting | Mac | Windows |
| --- | --- | --- |
| Name | `redcap-api` | `redcap-api` |
| Command | `/full/path/to/redcap_api_mcp/.venv/bin/redcap-mcp` | `C:\full\path\to\redcap_api_mcp\.venv\Scripts\redcap-mcp.exe` |
| Arguments | `serve` | `serve` |

Replace the example path with the actual folder where you downloaded the repository. Do not put your REDCap API URL or token in the app's MCP settings—the `redcap-mcp setup` command already stored them safely on your computer.

If the app asks you to edit a JSON configuration file instead, use this pattern and replace the command path:

```json
{
  "mcpServers": {
    "redcap-api": {
      "command": "/full/path/to/redcap_api_mcp/.venv/bin/redcap-mcp",
      "args": ["serve"]
    }
  }
}
```

Save the file and restart the app. If the app offers only an MCP **URL**, it supports remote MCP servers only and cannot use this local version.

## Everyday use

Ask your chat app questions such as “What forms are in this REDCap project?”, “Find fields related to age,” “Show up to 20 records with age and visit date,” or “Summarize the age field.” The app can only use the configured profiles and the read-only tools supplied by this server.

To check that a profile can still reach REDCap, open Terminal/PowerShell, activate the private environment as shown above, and run:

```sh
redcap-mcp health
```

## Updating the tool

Open Terminal/PowerShell, go back to the folder you downloaded, and activate the private environment. Then run:

On a Mac:

```sh
cd /path/to/redcap_api_mcp
source .venv/bin/activate
git pull
python -m pip install --upgrade .
```

On Windows PowerShell:

```powershell
cd C:\path\to\redcap_api_mcp
.\.venv\Scripts\Activate.ps1
git pull
python -m pip install --upgrade .
```

Replace the example path with the folder where you downloaded the repository. `git pull` downloads the latest approved changes; it does not change your REDCap token or profiles. Restart Codex or Claude after updating.

If `git pull` reports a problem, do not delete anything or paste an API token into an error report. Ask your local IT or REDCap support contact for help and include only the error message.

## Privacy defaults

Identifier-marked fields, configured denylisted fields, and sensitive REDCap system fields are removed by default. Record IDs that need to remain for row linkage are HMAC pseudonyms. To expose identifiers, an administrator must explicitly enable them for a profile and the caller must set `include_identifiers=true` on the individual request.

See `redcap-mcp --help` for profile, health, report alias, denylist, and identifier-policy commands.
