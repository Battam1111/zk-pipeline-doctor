# zk-pipeline-doctor

> Diagnose ZK circuit projects (Aleo, Noir, Compact, Cairo, Risc0) for common health issues.

Born from authoring the [Midnight ZK Cookbook](https://battam1111.github.io/midnight-zk-cookbook/) and noticing 80% of ZK projects share the same gaps: stale toolchain, missing tests, no CI, hard-coded secrets, untested edge cases.

`zk-doctor` walks a project directory and emits a markdown report scoring each dimension 1-10 plus concrete fixes.

## Install

```bash
pipx install zk-pipeline-doctor
# or
pip install --user zk-pipeline-doctor
```

## Use

```bash
# Diagnose the project in the current directory
zk-doctor .

# Or any path
zk-doctor /path/to/midnight-project

# JSON output for CI integration
zk-doctor . --format json

# Save report to a file
zk-doctor . --output report.md

# Exit nonzero if score < threshold (useful in CI)
zk-doctor . --threshold 7
```

## Detected dimensions

| Dimension | What we check |
|---|---|
| Language detection | Compact, Leo, Noir, Cairo, Rust+risc0 — auto-detected via file extensions and config files |
| Toolchain freshness | `cargo`/`leo`/`nargo`/`compact-cli` version against published latest |
| Test presence | Existence and roughly-counted size of `tests/`, `test/`, `*_test.*`, `*.spec.*` files |
| CI configuration | `.github/workflows/*.yml`, presence of CI for tests, builds, releases |
| Documentation | `README.md`, examples, inline comments density |
| Security hygiene | Hard-coded private keys, `TODO` markers near critical paths, `.gitignore` coverage |
| Reproducibility | Lockfiles present (`Cargo.lock`, `package-lock.json`, etc.); toolchain pins |

## Example output

```
# zk-doctor report

Overall score: 6.2/10

| Dimension | Score | Notes |
|---|---|---|
| Language | 10/10 | Detected: Compact (12 files) |
| Tests    | 4/10  | No tests/ directory; 0 *_test.* files |
| CI       | 0/10  | No .github/workflows/ |
```

## CI use

`zk-doctor` exits with code 0 if overall score >= threshold, 1 otherwise:

```yaml
- name: ZK health check
  run: |
    pipx install zk-pipeline-doctor
    zk-doctor . --threshold 7
```

## License

MIT — see `LICENSE`.

## Related

Sibling to the [ZK Cookbook](https://battam1111.github.io/midnight-zk-cookbook/), a multi-ecosystem tutorial site covering Midnight, Aleo, Noir, and friends.

## Contributing

Bug reports and detector additions welcome. Each detector is a small Python module in `src/zk_doctor/detectors/` — add one for your favorite ZK ecosystem in ~50 LOC.
