# zk-pipeline-doctor

[![PyPI-soon](https://img.shields.io/badge/install-pip%20install%20git+...-blue?style=flat-square)](https://github.com/Battam1111/zk-pipeline-doctor)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-passing-green?style=flat-square)](https://github.com/Battam1111/zk-pipeline-doctor/actions)
[![GitHub Action](https://img.shields.io/badge/GitHub%20Action-zk--doctor--action%20v1.1.0-purple?style=flat-square)](https://github.com/Battam1111/zk-doctor-action)
[![Cookbook](https://img.shields.io/badge/Cookbook-17%20tutorials-blueviolet?style=flat-square)](https://battam1111.github.io/midnight-zk-cookbook/)

**Multi-ecosystem ZK project health audit.** Free tier covers 6 baseline detectors across Compact (Midnight), Leo (Aleo), Noir (Aztec), Cairo (Starknet + Cairo M), and 7 Rust-based zkVMs (risc0, SP1, Plonky3, Stwo, OpenVM, Nexus, Jolt). Plus Solidity ZK-verifier detection. The Pro tier adds 4 deep cross-ecosystem detectors that go beyond surface-level health checks.

## What the free tier scores

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

# See what Pro adds
zk-doctor --explain-pro
```

Output is Markdown (default) or JSON (`--format json`); write to file with `--output report.md`. Fail CI below a score threshold with `--threshold 0.7`.

## Pro tier

The Pro tier (`$15/mo` per developer; activates on up to 5 machines per key) unlocks four deep cross-ecosystem detectors that demand multi-file analysis and ecosystem-specific knowledge:

- **`circuit_complexity`**: estimate circuit size across Plonky3 AIRs, SP1 program syscall counts, Compact circuit counts, Noir assert/loop hints, and Cairo function counts
- **`proving_system_pitfalls`**: soundness footguns by ecosystem: risc0 dev-mode leak, SP1 missing accelerated patches, Plonky3 default field/PCS, Stwo default proof config, Noir/Compact toolchain pin drift
- **`verifier_soundness`**: Solidity ZK-verifier audit checklist: `delegatecall` presence, scalar-field bounds on public inputs, G1/G2 zero-point checks, pairing-precompile gas griefing
- **`multi_file_consistency`**: proving-system version pinned consistently across `Cargo.toml`/README/CI; dev-vs-prod feature flag drift; circuit signature vs verifier arity drift; `Cargo.lock` dialect consistency

```bash
# After purchase, activate once per machine:
zk-doctor activate ZKD-XXXX-XXXX-XXXX-XXXXXX
zk-doctor license-status   # confirms tier == pro
zk-doctor /path/to/project # now runs all 10 detectors
```

The free tier still does everything it did in v0.2.x, the Pro detectors are additions, not replacements. Buy at https://buy.polar.sh/polar_cl_qmTOsuYZ6CHZJlElzrYGfnf3iXHfJfmwt5add3qGeD0 (Polar handles billing as Merchant of Record; VAT and US sales tax included; 30-day refund policy).

> Implementation drafted with AI assistance and reviewed before each release.

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
| **Free CLI** (this repo) | Open-source CLI, all 6 baseline detectors, run on your own machine, exit-code threshold gate. | $0, MIT |
| **Free GitHub Action** ([zk-doctor-action](https://github.com/Battam1111/zk-doctor-action)) | Drop-in CI integration, PR comments, diff-aware mode. | $0, MIT |
| **[ZK Cookbook Bundle](https://polar.sh/checkout/polar_c_6CqAq70gZIe8bmUOyrKMYQkLSYXS7t9aY3yxy4TFovi)** | 17 tutorials + companion code repos, offline-readable. | $15 once |
| **[Cookbook + Pro License](https://polar.sh/checkout/polar_c_aGRfgpddGyhB9LOTBSLvkBlsYJlMMo6M8muFX2rPXtk)** | Bundle + priority detector update requests + private-fork support. | $49 once |
| **zk-doctor Pro** (this) | +4 deep cross-ecosystem detectors (circuit complexity, pitfalls, verifier soundness, cross-file). | $15/mo (link TBD; see POLAR_PRODUCT_TODO.md) |
| **[$99 Pre-Flight Audit](https://polar.sh/checkout/polar_c_gXO0FivhPZEULEbuWnpznkLPFdL2Koz68AvG93YoWFb)** | We run the CLI on your repo + add narrative review + Battam1111 personal review. Delivered in 24h as HTML/Markdown report. [See sample](https://battam1111.github.io/bounty-radar-data/audits/sample.html). **Pre-flight before a $10-50k human audit; NOT a substitute.** | $99 once |
| **[Bounty Radar Hobbyist](https://polar.sh/checkout/polar_c_BbZbN6eJnZ7rwsUfT1pMsj4lTftwnfMoGdWBo0KozKU)** | Real-time push of new ZK bounties matching your filter (Telegram). | $19/mo |
| **[Bounty Radar Pro](https://polar.sh/checkout/polar_c_CKKhyOq11BHuG2AulflWkm53YU98pLdrNo22h3OlB4O)** | All Hobbyist + multi-filter + HMAC webhook + weekly digest. | $97/mo |
| **[Bounty Radar Team](https://polar.sh/checkout/polar_c_bT1FpxfzlShI3PcdHxTrHeJf8EVO1AFaWbFc90Z9mfC)** | All Pro + shared Slack/Discord + 5 seats + custom detectors. | $497/mo |

All payments via [Polar.sh](https://polar.sh) (Merchant of Record). 30-day money-back guarantee.

## Embed the "Audited by zk-doctor" badge

Drop this in any ZK project README:

```markdown
[![Audited by zk-doctor](https://battam1111.github.io/bounty-radar-data/badges/audited.svg)](https://github.com/Battam1111/zk-pipeline-doctor)
```

For per-repo dynamic score badges (shields.io endpoint), see [badges/README.md](https://github.com/Battam1111/bounty-radar-data/tree/main/badges).

## ZK ecosystem learning resources

zk-doctor scores your project; the [Midnight ZK Cookbook](https://battam1111.github.io/midnight-zk-cookbook/) teaches you how to write code that scores well. 17 EN + 4 CN tutorials with verified syntax across 5 ecosystems. Recommended starting points:

- [Compact vs Leo vs Noir vs Cairo](https://battam1111.github.io/midnight-zk-cookbook/tutorials/zk-language-comparison.html); pick the right ZK language for your problem
- [Compact contracts with Map and Merkle](https://battam1111.github.io/midnight-zk-cookbook/tutorials/289.html); Midnight's most common state pattern
- [Noir circuit basics](https://battam1111.github.io/midnight-zk-cookbook/tutorials/noir-circuit-basics.html); from zero to a working circuit with test suite
- [Risc0 zkVM in Rust](https://battam1111.github.io/midnight-zk-cookbook/tutorials/risc0-zkvm-rust.html); prove existing Rust execution without rewriting as a circuit
- [zk-doctor GitHub Action](https://battam1111.github.io/midnight-zk-cookbook/tutorials/zk-doctor-github-action.html); add automated ZK quality checks to any PR

Full index: <https://battam1111.github.io/midnight-zk-cookbook/>

## Get paid for ZK work

Once you can pass `zk-doctor` on your own repos, claiming public bounties is the natural next step. [Bounty Radar](https://battam1111.github.io/bounty-radar-data/) is a live, free feed aggregating open ZK bounties from Algora, GitHub labels, Drips Wave, Code4rena, and Bountycaster. Per-ecosystem widgets and JSON sub-feeds:

- Midnight: [widget](https://battam1111.github.io/bounty-radar-data/widget.html?ecosystem=midnight) · [JSON](https://battam1111.github.io/bounty-radar-data/midnight.json)
- Noir: [widget](https://battam1111.github.io/bounty-radar-data/widget.html?ecosystem=noir) · [JSON](https://battam1111.github.io/bounty-radar-data/noir.json)
- Aleo: [widget](https://battam1111.github.io/bounty-radar-data/widget.html?ecosystem=aleo) · [JSON](https://battam1111.github.io/bounty-radar-data/aleo.json)
- Aztec: [widget](https://battam1111.github.io/bounty-radar-data/widget.html?ecosystem=aztec) · [JSON](https://battam1111.github.io/bounty-radar-data/aztec.json)
- Cairo / Starknet: [widget](https://battam1111.github.io/bounty-radar-data/widget.html?ecosystem=cairo) · [JSON](https://battam1111.github.io/bounty-radar-data/cairo.json)
- risc0 / SP1 / Plonky3: [widget](https://battam1111.github.io/bounty-radar-data/widget.html?ecosystem=risc0) · [JSON](https://battam1111.github.io/bounty-radar-data/risc0.json)

Free tier is poll-based. Real-time Telegram push starts at $19/mo; see [pricing on the radar landing](https://battam1111.github.io/bounty-radar-data/#pricing--why-pay-if-the-feed-is-free).

## Related projects

<!-- related-projects:start -->
- [**zk-doctor-action**](https://github.com/Battam1111/zk-doctor-action); GitHub Action wrapping this CLI; diff-aware PR comments
- [**bounty-radar-data**](https://battam1111.github.io/bounty-radar-data/); Live ZK bounty feed
- [**bounty-radar-mcp**](https://github.com/Battam1111/bounty-radar-mcp); MCP server for the bounty feed
- [**midnight-zk-cookbook**](https://battam1111.github.io/midnight-zk-cookbook/); 17 ZK tutorials across 5 ecosystems
<!-- related-projects:end -->

## License

MIT
