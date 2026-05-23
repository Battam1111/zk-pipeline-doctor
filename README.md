# zk-pipeline-doctor

[![PyPI-soon](https://img.shields.io/badge/install-pip%20install%20git+...-blue?style=flat-square)](https://github.com/Battam1111/zk-pipeline-doctor)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-21%20passing-green?style=flat-square)](https://github.com/Battam1111/zk-pipeline-doctor/actions)
[![GitHub Action](https://img.shields.io/badge/GitHub%20Action-zk--doctor--action%20v1.1.0-purple?style=flat-square)](https://github.com/Battam1111/zk-doctor-action)
[![Cookbook](https://img.shields.io/badge/Cookbook-17%20tutorials-blueviolet?style=flat-square)](https://battam1111.github.io/midnight-zk-cookbook/)

**Multi-ecosystem ZK project health audit.** 8 detectors across Compact (Midnight), Leo (Aleo), Noir (Aztec), Cairo (Starknet + Cairo M), and 7 Rust-based zkVMs (risc0, SP1, Plonky3, Stwo, OpenVM, Nexus, Jolt). Plus Solidity ZK-verifier detection.

## What it scores

Six dimensions on a 0-10 scale; weighted overall:

| Detector | What it checks |
|---|---|
| `language` | Detects which ZK language(s) + Rust zkVMs are present. Validates toolchain config. |
| `tests` | Test files present, test:source ratio, framework conventions |
| `ci` | `.github/workflows/`, matrix coverage, key signals |
| `docs` | README sections, CONTRIBUTING, examples/, inline doc-comments |
| `security` | Secrets in tree, sensitive-file patterns, dependency pinning |
| `reproducibility` | Lockfiles, fixed toolchain versions, deterministic build hints |

## Install + run

```bash
# Install from GitHub (PyPI publication pending)
pip install git+https://github.com/Battam1111/zk-pipeline-doctor.git@main

# Or with uv (recommended)
uvx --from git+https://github.com/Battam1111/zk-pipeline-doctor.git zk-doctor /path/to/your/project

# See pricing for paid offerings
zk-doctor --upgrade-info
```

Output is Markdown (default) or JSON (`--format json`); write to file with `--output report.md`. Fail CI below a score threshold with `--threshold 0.7`.

## Use it in GitHub Actions

```yaml
- uses: Battam1111/zk-doctor-action@v1
  with:
    threshold: '0.7'
    output: 'zk-doctor-report.md'
    comment-on-pr: 'true'
    comment-mode: 'diff'        # 'full' | 'diff' | 'none'
    fail-on-regression: 'true'  # fail CI if PR drops score >0.1
```

See [Battam1111/zk-doctor-action](https://github.com/Battam1111/zk-doctor-action).

## Tiered offerings

| Tier | What you get | Price |
|---|---|---|
| **Free CLI** (this repo) | Open-source CLI, all 8 detectors, run on your own machine, exit-code threshold gate. | $0, MIT |
| **Free GitHub Action** ([zk-doctor-action](https://github.com/Battam1111/zk-doctor-action)) | Drop-in CI integration, PR comments, diff-aware mode. | $0, MIT |
| **[ZK Cookbook Bundle](https://polar.sh/checkout/polar_c_6CqAq70gZIe8bmUOyrKMYQkLSYXS7t9aY3yxy4TFovi)** | 17 tutorials + companion code repos, offline-readable. | $15 once |
| **[Cookbook + Pro License](https://polar.sh/checkout/polar_c_aGRfgpddGyhB9LOTBSLvkBlsYJlMMo6M8muFX2rPXtk)** | Bundle + priority detector update requests + private-fork support. | $49 once |
| **[$99 Pre-Flight Audit](https://polar.sh/checkout/polar_c_gXO0FivhPZEULEbuWnpznkLPFdL2Koz68AvG93YoWFb)** | We run the CLI on your repo + add narrative review + Battam1111 personal review. Delivered in 24h as HTML/Markdown report. [See sample](https://battam1111.github.io/bounty-radar-data/audits/sample.html). **Pre-flight before a $10-50k human audit; NOT a substitute.** | $99 once |
| **[Bounty Radar Hobbyist](https://polar.sh/checkout/polar_c_BbZbN6eJnZ7rwsUfT1pMsj4lTftwnfMoGdWBo0KozKU)** | Real-time push of new ZK bounties matching your filter (Telegram). | $19/mo |
| **[Bounty Radar Pro](https://polar.sh/checkout/polar_c_CKKhyOq11BHuG2AulflWkm53YU98pLdrNo22h3OlB4O)** | All Hobbyist + multi-filter + HMAC webhook + weekly digest. | $97/mo |
| **[Bounty Radar Team](https://polar.sh/checkout/polar_c_bT1FpxfzlShI3PcdHxTrHeJf8EVO1AFaWbFc90Z9mfC)** | All Pro + shared Slack/Discord + 5 seats + custom detectors. | $497/mo |

All payments via [Polar.sh](https://polar.sh) (Merchant of Record). 14-day money-back guarantee.

## Embed the "Audited by zk-doctor" badge

Drop this in any ZK project README:

```markdown
[![Audited by zk-doctor](https://battam1111.github.io/bounty-radar-data/badges/audited.svg)](https://github.com/Battam1111/zk-pipeline-doctor)
```

For per-repo dynamic score badges (shields.io endpoint), see [badges/README.md](https://github.com/Battam1111/bounty-radar-data/tree/main/badges).

## Related projects

<!-- related-projects:start -->
- [**zk-doctor-action**](https://github.com/Battam1111/zk-doctor-action); GitHub Action wrapping this CLI; diff-aware PR comments
- [**bounty-radar-data**](https://battam1111.github.io/bounty-radar-data/); Live ZK bounty feed
- [**bounty-radar-mcp**](https://github.com/Battam1111/bounty-radar-mcp); MCP server for the bounty feed
- [**midnight-zk-cookbook**](https://battam1111.github.io/midnight-zk-cookbook/); 17 ZK tutorials across 5 ecosystems
<!-- related-projects:end -->

## License

MIT
