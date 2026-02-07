# Production Deployment Guide

This guide covers deploying debate-hall-mcp in production environments, including state storage configuration, concurrency handling, security considerations, and example deployment configurations.

## Table of Contents

- [State Storage Configuration](#state-storage-configuration)
- [Concurrency Model](#concurrency-model)
- [Security Considerations](#security-considerations)
- [Secrets Management](#secrets-management)
- [Multi-Instance Deployments](#multi-instance-deployments)
- [Example Configurations](#example-configurations)
- [Monitoring and Observability](#monitoring-and-observability)
- [Troubleshooting](#troubleshooting)

---

## State Storage Configuration

### Environment Variable: `DEBATE_HALL_STATE_DIR`

The `DEBATE_HALL_STATE_DIR` environment variable controls where debate state files are stored.

**Resolution Order:**
1. `DEBATE_HALL_STATE_DIR` environment variable (if set and non-empty)
2. Project root / `debates` (auto-detected via `.git` or `pyproject.toml`)
3. `./debates` (fallback for backwards compatibility)

**Recommended Production Value:**
```bash
export DEBATE_HALL_STATE_DIR=/var/lib/debate-hall/
```

### File Format

- Each debate is stored as a JSON file: `{thread_id}.json`
- Lock files are created alongside: `{thread_id}.lock`
- File permissions: `600` for state files, `700` for directory

### Directory Setup

```bash
# Create dedicated state directory
sudo mkdir -p /var/lib/debate-hall
sudo chown $SERVICE_USER:$SERVICE_GROUP /var/lib/debate-hall
sudo chmod 700 /var/lib/debate-hall
```

---

## Concurrency Model

### File Locking

debate-hall-mcp uses exclusive file locks via the `filelock` library for cross-platform concurrency control.

**How it works:**
- Lock files are created as `{thread_id}.lock` in the state directory
- Locks are held during read and write operations
- Works on POSIX (Linux, macOS) and Windows

### Compare-and-Swap (CAS)

For race condition prevention, debate-hall-mcp implements Compare-and-Swap:

```python
# The save_debate_state_with_retry() function handles CAS automatically:
# 1. Compute SHA-256 hash of current state file
# 2. Attempt save with expected_hash parameter
# 3. On ConcurrencyError, reload state and retry
# 4. Exponential backoff between retries (default: 3 retries)
```

**CAS Error Handling:**

When concurrent modifications are detected, `ConcurrencyError` is raised with:
- `expected_hash`: The hash the caller expected
- `actual_hash`: The hash found (indicating concurrent modification)
- `thread_id`: The affected debate thread

---

## Security Considerations

### Path Traversal Protection

Thread IDs are validated before use in filesystem operations. The following patterns are rejected:
- `..` (parent directory traversal)
- `/` (absolute path injection)
- `\` (Windows path separator)

Invalid thread IDs raise `ValueError` with a clear message.

### Hash Chain Verification

Each turn in a debate is part of a SHA-256 hash chain:

1. **Link Verification** (default): Ensures `previous_hash` continuity
2. **Content Verification** (opt-in): Recomputes hashes to detect tampering

```python
# Enable content verification on load
from debate_hall_mcp.state import load_debate_state

room = load_debate_state(thread_id, state_dir, verify_content=True)
# Raises IntegrityError if content tampering detected
```

### Atomic Writes

State files use atomic write patterns:
1. Write to temporary file in same directory
2. Call `fsync()` to ensure data is flushed to disk
3. Atomically rename temp file to final location
4. On failure, original file is preserved

---

## Secrets Management

### Required Secrets

| Secret | Purpose | Required For |
|--------|---------|--------------|
| `OPENROUTER_API_KEY` | OpenRouter API access | Auto-orchestration (`run_debate`) |
| `GITHUB_TOKEN` | GitHub API access | GitHub integration tools |

### Production Patterns

**DO NOT use `.env` files in production.** Instead:

1. **Explicit Environment Variables:**
   ```bash
   export OPENROUTER_API_KEY="sk-or-..."
   export GITHUB_TOKEN="ghp_..."
   ```

2. **Secret Managers:**
   - AWS Secrets Manager
   - HashiCorp Vault
   - Kubernetes Secrets
   - Docker Swarm Secrets

3. **systemd Integration:**
   ```ini
   # Use EnvironmentFile for secrets
   EnvironmentFile=/etc/debate-hall/secrets.env
   ```

4. **Docker/Kubernetes:**
   ```yaml
   # Use secrets, not environment in compose files
   secrets:
     - openrouter_api_key
     - github_token
   ```

### GitHub Token Permissions

For GitHub integration, the token needs:
- `repo` scope (for issue/PR creation)
- `discussions` scope (for discussion sync)

---

## Multi-Instance Deployments

### Shared Filesystem

File locks work correctly on shared filesystems:
- **NFS**: Works with proper configuration
- **AWS EFS**: Fully supported
- **GlusterFS**: Supported

**Important:** Ensure the shared filesystem supports `flock()` or `fcntl()` locking.

### High Concurrency Scenarios

For deployments with >10 concurrent instances or high write contention:

1. **Current limitation:** File-based locking uses exclusive locks for all operations
2. **Enhancement:** Read/write lock separation planned in [Issue #106](https://github.com/elevanaltd/debate-hall-mcp/issues/106)
3. **Future:** Database backend for true multi-instance scaling ([Issue #106](https://github.com/elevanaltd/debate-hall-mcp/issues/106))

---

## Example Configurations

### systemd Unit File

```ini
# /etc/systemd/system/debate-hall-mcp.service
[Unit]
Description=Debate Hall MCP Server
After=network.target

[Service]
Type=simple
User=debate-hall
Group=debate-hall
WorkingDirectory=/opt/debate-hall

# State configuration
Environment=DEBATE_HALL_STATE_DIR=/var/lib/debate-hall

# Load secrets from file (recommended)
EnvironmentFile=/etc/debate-hall/secrets.env

# Run the MCP server
ExecStart=/opt/debate-hall/.venv/bin/python -m debate_hall_mcp

# Security hardening
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/var/lib/debate-hall
PrivateTmp=yes

# Restart policy
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Secrets file (`/etc/debate-hall/secrets.env`):**
```bash
# Permissions: 600, owned by root
OPENROUTER_API_KEY=sk-or-...
GITHUB_TOKEN=ghp_...
```

### Docker Compose

```yaml
# docker-compose.yml
services:
  debate-hall:
    build: .
    environment:
      - DEBATE_HALL_STATE_DIR=/data/debates
    volumes:
      - debate-data:/data/debates
    secrets:
      - openrouter_api_key
      - github_token
    restart: unless-stopped
    # Security: run as non-root
    user: "1000:1000"

volumes:
  debate-data:

secrets:
  openrouter_api_key:
    file: ./secrets/openrouter_api_key.txt
  github_token:
    file: ./secrets/github_token.txt
```

### Dockerfile

```dockerfile
FROM python:3.12-slim

# Create non-root user
RUN useradd -m -s /bin/bash debate-hall

WORKDIR /app

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev

# Copy application
COPY src/ ./src/

# Set up state directory
ENV DEBATE_HALL_STATE_DIR=/data/debates
RUN mkdir -p /data/debates && chown debate-hall:debate-hall /data/debates

# Switch to non-root user
USER debate-hall

# Run the server
CMD ["python", "-m", "debate_hall_mcp"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: debate-hall-mcp
spec:
  replicas: 1  # Single replica for file-based storage
  selector:
    matchLabels:
      app: debate-hall-mcp
  template:
    metadata:
      labels:
        app: debate-hall-mcp
    spec:
      containers:
        - name: debate-hall
          image: debate-hall-mcp:latest
          env:
            - name: DEBATE_HALL_STATE_DIR
              value: /data/debates
            - name: OPENROUTER_API_KEY
              valueFrom:
                secretKeyRef:
                  name: debate-hall-secrets
                  key: openrouter-api-key
            - name: GITHUB_TOKEN
              valueFrom:
                secretKeyRef:
                  name: debate-hall-secrets
                  key: github-token
          volumeMounts:
            - name: debate-data
              mountPath: /data/debates
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            readOnlyRootFilesystem: true
      volumes:
        - name: debate-data
          persistentVolumeClaim:
            claimName: debate-hall-pvc
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: debate-hall-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
```

---

## Monitoring and Observability

### Recommended Metrics

1. **State directory size:** Monitor disk usage
2. **Lock contention:** Track lock wait times (if using custom instrumentation)
3. **ConcurrencyError rate:** Indicates high contention scenarios
4. **Hash verification failures:** May indicate tampering or corruption

### Log Monitoring

Key log patterns to monitor:
- `ConcurrencyError`: Concurrent modification conflicts
- `IntegrityError`: Content hash verification failures
- `ValueError: Invalid thread_id`: Potential security issues

### Health Checks

```python
# Simple health check endpoint (if building HTTP wrapper)
def health_check():
    state_dir = get_state_dir()
    return {
        "status": "healthy",
        "state_dir": str(state_dir),
        "state_dir_writable": os.access(state_dir, os.W_OK),
    }
```

---

## Troubleshooting

### Common Issues

**Issue: "No such file or directory" for state file**
- Check `DEBATE_HALL_STATE_DIR` is set correctly
- Verify directory exists and has correct permissions

**Issue: ConcurrencyError after retries**
- High write contention on the same debate
- Consider reducing concurrent writers or using database backend

**Issue: IntegrityError on load**
- Content was modified outside normal operations
- Investigate source of modification
- Use backup if available

**Issue: Lock files accumulating**
- Lock files are not automatically cleaned up
- Safe to remove `.lock` files when no processes are running

### Debug Mode

For debugging state issues:
```python
from debate_hall_mcp.state import load_debate_state, verify_all_turn_content_hashes

room = load_debate_state(thread_id, state_dir)
verification = verify_all_turn_content_hashes(room.turns)
for result in verification:
    if not result["verified"]:
        print(f"Turn {result['turn_index']}: hash mismatch")
```

---

## Related Issues

- [Issue #33](https://github.com/elevanaltd/debate-hall-mcp/issues/33): State directory configuration
- [Issue #48](https://github.com/elevanaltd/debate-hall-mcp/issues/48): Concurrency control
- [Issue #105](https://github.com/elevanaltd/debate-hall-mcp/issues/105): Content hash verification
- [Issue #106](https://github.com/elevanaltd/debate-hall-mcp/issues/106): Database backend (planned)
- [Issue #149](https://github.com/elevanaltd/debate-hall-mcp/issues/149): Compare-and-Swap implementation
