# REDCap API MCP

A local, stdio-only MCP server for safely reading REDCap project metadata and bounded data previews. It has no import, update, delete, file, or dataset-export capability.

## Install and set up

```sh
pip install redcap-api-mcp
redcap-mcp setup
redcap-mcp serve
```

`setup` stores API tokens and a per-profile pseudonym key in the operating-system credential store. The local configuration contains only profile names, URLs, aliases, privacy settings, and the default profile.

Use `redcap-mcp configure codex`, `redcap-mcp configure claude-desktop`, or `redcap-mcp configure claude-code` to add the server to a supported host. Configuration files are backed up before modification.

## Privacy defaults

Identifier-marked fields, configured denylisted fields, and sensitive REDCap system fields are removed by default. Record IDs that need to remain for row linkage are HMAC pseudonyms. To expose identifiers, an administrator must explicitly enable them for a profile and the caller must set `include_identifiers=true` on the individual request.

See `redcap-mcp --help` for profile, health, report alias, denylist, and identifier-policy commands.
