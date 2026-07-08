---
name: insecure-defaults
description: Audit a codebase for insecure default configurations, fail-open security patterns, hardcoded credentials, and weak crypto. Use when performing a security audit, reviewing config or environment variable handling, or scanning before a release.
---

Finds **fail-open** vulnerabilities: places where missing or weak configuration causes the application to run insecurely rather than refusing to start.

This is distinct from `pr-review` -- that skill reviews a diff for a specific PR. This skill performs a standalone scan across the codebase.

## Fail-open vs fail-secure

The core distinction:

- **Fail-open (bad):** Missing config causes the app to run with a weak or empty value. `SECRET = os.environ.get("SECRET_KEY") or "default"` -- the app starts and uses `"default"` as the secret.
- **Fail-secure (safe):** Missing config causes the app to crash at startup. `SECRET = os.environ["SECRET_KEY"]` -- the app refuses to run without the variable.

Fail-secure patterns are not findings. Before reporting, trace whether the app actually crashes or silently uses the fallback.

## Workflow

### Phase 1: Discover project shape

Read the repo structure to understand the language(s), framework(s), and where configuration is consumed:

- Identify config loading files (e.g., `config/`, `src/config.ts`, `settings.py`, `internal/config/`)
- Identify env var access patterns used in the codebase
- Note which directories to exclude: `test/`, `spec/`, `__tests__/`, `*.example`, `*.template`, `*.sample`, docs, README

This shapes which search patterns to run in Phase 2.

### Phase 2: Search for insecure patterns

Run the scanner script against the target directory:

```bash
scan-insecure-defaults [TARGET_DIR]
```

The script runs all pattern categories below in one pass, excludes test/dist directories, and labels output by section. `TARGET_DIR` defaults to `.`.

The categories covered by the scanner:

- **Fallback secrets** -- env var reads with a non-empty string default
- **Hardcoded credentials** -- literal secrets assigned in source
- **Fail-open auth flags** -- boolean security config defaulting to `false`
- **Weak crypto** -- MD5, SHA1, RC4, DES used in cryptographic contexts
- **Permissive access** -- CORS wildcards, `chmod 777`
- **Debug in production** -- verbose/debug flags defaulting to enabled
- **TLS skip verify** -- `rejectUnauthorized: false`, `InsecureSkipVerify: true`

### Phase 3: Verify each match

For each match, answer these questions before writing a finding:

1. **Is this production-reachable code?** (Not a test fixture, not a `.example` file, not a dev-only script)
2. **Does the app start and run with the fallback?** Trace from the match to where the value is used. If the app crashes on startup without the env var, this is fail-secure -- skip it.
3. **Is there an override at the deployment layer?** Check for a `docker-compose.yml`, Helm values, or CI env vars that always provide the real value. If an override always exists, note it but still flag the code-level vulnerability -- it remains a risk if the override is ever missed.
4. **What is the blast radius?** Is the value used in auth, signing, encryption, or access control? Scope determines severity.

### Phase 4: Report findings

For each confirmed finding, report:

- **Location**: file and line number
- **Pattern**: the specific code that is fail-open
- **Verification**: what happens when the env var is missing (traced code path)
- **Impact**: what an attacker gains by exploiting the default
- **Fix**: the fail-secure alternative

Example:

```
Finding: JWT secret falls back to hardcoded value
Location: src/auth/jwt.ts:12
Pattern: const secret = process.env.JWT_SECRET || "insecure-default";
Verification: App starts without JWT_SECRET; secret passed to jwt.sign() at line 34
Impact: Attacker forges valid JWTs using "insecure-default", bypassing auth
Fix: Throw at startup if JWT_SECRET is not set
```

## Scope exclusions

Do not report findings in:
- Files under `test/`, `spec/`, `__tests__/`, or similar test directories
- Files ending in `.example`, `.template`, `.sample`
- `README.md` or files under `docs/`
- Dev-only `docker-compose.yml` files not used in production deployments
- Build-time configuration that is replaced before the binary runs

When in doubt, trace whether the code path executes in production.

## Rationalizations to reject

- **"It's just a development default"** -- If the code path is reachable in production, it is a finding. Dev defaults ship.
- **"The production config always overrides it"** -- The code-level risk remains if the override is ever absent. Note the mitigation, but still report.
- **"This would never run without proper config"** -- Verify this by tracing the startup path. Many apps fail silently rather than crashing.
- **"It's behind authentication"** -- A compromised session or confused-deputy attack still exploits the weak default.
