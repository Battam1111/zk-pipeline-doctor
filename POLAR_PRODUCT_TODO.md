# Polar product setup: zk-doctor Pro ($15/mo)

Ready-to-paste guide for publishing **zk-doctor Pro** as a Polar subscription product.
The framework code (`src/zk_doctor/license.py` + the `@pro_only` decorator) is already
wired against Polar's customer-portal validation API. This document gives you the
exact JSON payloads and curl commands needed to mint the product.

You will execute three curl calls in sequence:

1. Create the **license-keys benefit** (returns a benefit ID).
2. Create the **subscription product** and attach the benefit (returns a product ID + checkout URL).
3. **Verify** the product is live by reading it back.

Total elapsed time, assuming `POLAR_TOKEN` is exported, is about 30 seconds.

---

## Prerequisites

```bash
# Export the token without writing it to disk anywhere readable.
export POLAR_TOKEN="$(python3 -c 'import json; print(json.load(open("/Users/chenyanyun/bounty-agent/secrets/polar.json"))["token"])')"
export ORG_ID="b23fe650-4bde-4d68-983a-67f93e39224f"

# Sanity check (should print the org slug, not the token).
curl -sS "https://api.polar.sh/v1/organizations/$ORG_ID" \
  -H "Authorization: Bearer $POLAR_TOKEN" \
  | python3 -c 'import sys, json; d=json.load(sys.stdin); print("org:", d.get("slug"))'
```

Expected output: `org: battam1111`.

---

## Step 1: Create the license-keys benefit

This benefit is what the buyer actually receives at checkout: a key starting with
`ZKD-` that activates the Pro detectors on up to 5 machines for the life of the subscription.

```bash
BENEFIT_RESPONSE=$(curl -sS -X POST "https://api.polar.sh/v1/benefits/" \
  -H "Authorization: Bearer $POLAR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "organization_id": "'"$ORG_ID"'",
    "type": "license_keys",
    "description": "zk-doctor Pro License",
    "properties": {
      "prefix": "ZKD",
      "activations": {"enable_customer_admin": true, "limit": 5},
      "expires": null,
      "limit_usage": null
    }
  }')

echo "$BENEFIT_RESPONSE"
export BENEFIT_ID=$(echo "$BENEFIT_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "BENEFIT_ID=$BENEFIT_ID"
```

**Benefit description** (this is what the buyer sees in their Polar dashboard
under "Active benefits"):

> Activates the four Pro detectors in zk-doctor (`circuit_complexity`,
> `proving_system_pitfalls`, `verifier_soundness`, `multi_file_consistency`)
> across up to 5 machines. License lifetime matches your subscription;
> Polar revokes the key automatically if the subscription cancels.

**Properties recap**:
- `prefix`: `ZKD` (so keys look like `ZKD-XXXX-XXXX-XXXX-XXXXXX`)
- `activations.limit`: 5 (one developer's laptop, work machine, CI runner, and a spare or two)
- `expires`: null (key lives as long as the subscription)
- `limit_usage`: null (the CLI is read-only and runs in under 5 seconds; metering would be friction without revenue)

---

## Step 2: Create the subscription product

This call mints the product itself, sets the price tiers (monthly $15, annual $144), and attaches the benefit from step 1.

```bash
PRODUCT_RESPONSE=$(curl -sS -X POST "https://api.polar.sh/v1/products/" \
  -H "Authorization: Bearer $POLAR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "organization_id": "'"$ORG_ID"'",
    "name": "zk-doctor Pro",
    "description": "Cross-ecosystem deep audit for serious ZK projects. Four Pro detectors that go beyond surface-level health checks: circuit complexity estimation, proving-system soundness pitfalls, Solidity verifier audit, and multi-file consistency.\n\nIf you ship to mainnet, you already know that ZK bugs are silent. A free linter catches missing tests and unpinned toolchains; it does not catch a Plonky3 default field choice that turns out to be unsound for your trace, a SP1 build that quietly drops the accelerated patches and runs 50x slower, a Solidity verifier missing scalar-field bounds checks on public inputs, or a Cargo.toml that pins risc0-zkvm 1.0 while your README and CI still reference 0.21. These are the bugs that survive code review and end up in retrospectives.\n\nzk-doctor Pro reads your repo end-to-end and flags 4 classes of problem that take a senior auditor an hour to spot manually. circuit_complexity estimates circuit size across Plonky3 AIRs, SP1 program syscall counts, Compact circuit counts, Noir assert/loop hints, and Cairo function counts so you know whether to profile. proving_system_pitfalls flags risc0 dev-mode leaks, missing SP1 patches, Plonky3 trivial defaults, Stwo proof-config defaults, and Noir/Compact toolchain pin drift. verifier_soundness scans Solidity ZK verifiers for delegatecall presence, scalar-field bounds on public inputs, G1/G2 zero-point guards, pairing-precompile gas griefing, and missing reentrancy guards. multi_file_consistency catches proving-system version drift across Cargo.toml, README, and CI, plus dev-vs-prod feature flag drift, circuit-arity vs verifier-arity drift, and Cargo.lock dialect drift.\n\nBuilt for solo ZK developers who want a second pair of eyes before pushing to mainnet, small audit teams who want a consistent pre-review pass on every client repo, and any project planning a paid audit who wants to land cheap fixes in-house first. Polar handles billing as Merchant of Record (VAT and US sales tax included). 30-day refund policy, no questions asked.\n\nWhat is included:\n- circuit_complexity detector: estimates circuit size across Plonky3 AIRs, SP1 syscall counts, Compact circuits, Noir asserts and loop bounds, and Cairo function counts\n- proving_system_pitfalls detector: risc0 dev-mode leak, SP1 missing accelerated patches, Plonky3 default field/PCS, Stwo default proof config, Noir/Compact toolchain pin drift\n- verifier_soundness detector: Solidity ZK-verifier audit including delegatecall scan, scalar-field bounds, G1/G2 zero-point guards, pairing-precompile gas griefing, reentrancy guard checks\n- multi_file_consistency detector: proving-system version drift across Cargo.toml, README, and CI; dev-vs-prod feature flag drift; circuit signature vs verifier arity drift; Cargo.lock dialect consistency\n- License-key activation across up to 5 machines (one dev laptop + work machine + CI runner + spare)\n- Same-day detector updates as new ZK frameworks emerge (subscribers get new detector versions via `pip install -U`)\n- Priority issue triage on GitHub for Pro subscribers\n- 30-day refund policy",
    "recurring_interval": "month",
    "prices": [
      {"amount_type": "fixed", "price_amount": 1500, "price_currency": "usd"}
    ],
    "benefits": ["'"$BENEFIT_ID"'"]
  }')

echo "$PRODUCT_RESPONSE"
export PRODUCT_ID=$(echo "$PRODUCT_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "PRODUCT_ID=$PRODUCT_ID"
```

### Optional: add an annual price tier at 20% off ($144/yr = $12/mo)

Polar products support multiple price tiers on the same product. If you want to
offer an annual option, run this after the monthly product is created:

```bash
curl -sS -X PATCH "https://api.polar.sh/v1/products/$PRODUCT_ID" \
  -H "Authorization: Bearer $POLAR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prices": [
      {"amount_type": "fixed", "price_amount": 1500, "price_currency": "usd", "recurring_interval": "month"},
      {"amount_type": "fixed", "price_amount": 14400, "price_currency": "usd", "recurring_interval": "year"}
    ]
  }'
```

Note: confirm Polar's current API allows mixed-interval price arrays on one product.
If it does not (some Polar versions require one interval per product), keep the
monthly tier as the primary product and either skip annual or mint a separate
"zk-doctor Pro (annual)" product cross-linked from the monthly one.

### Tagline, in case Polar prompts for one separately

`Cross-ecosystem deep audit for serious ZK projects.`

### Buyer-facing summary, formatted

These 8 bullets are pulled out of the description for any UI that takes a
short feature list separately (e.g., a "What's included" sidebar):

1. **`circuit_complexity`** detector: estimates circuit size across Plonky3 AIRs, SP1 syscalls, Compact circuits, Noir asserts and loops, and Cairo functions
2. **`proving_system_pitfalls`** detector: risc0 dev-mode leak, SP1 missing accelerated patches, Plonky3 default field/PCS, Stwo default proof config, Noir/Compact toolchain pin drift
3. **`verifier_soundness`** detector: Solidity ZK-verifier audit including delegatecall, scalar-field bounds, G1/G2 zero-point guards, pairing-precompile gas griefing, reentrancy
4. **`multi_file_consistency`** detector: proving-system version drift across Cargo.toml, README, and CI; dev-vs-prod feature flag drift; circuit signature vs verifier arity drift; Cargo.lock dialect consistency
5. License-key activation across up to **5 machines** (laptop + work machine + CI + spare)
6. **Same-day detector updates** as new ZK frameworks emerge (delivered via `pip install -U`)
7. **Priority issue triage** on GitHub for Pro subscribers
8. **30-day refund** policy

---

## Step 3: Verify the product is live

After both calls succeed, read the product back to confirm Polar persisted it and to capture the public checkout URL.

```bash
curl -sS "https://api.polar.sh/v1/products/$PRODUCT_ID" \
  -H "Authorization: Bearer $POLAR_TOKEN" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('name:        ', d.get('name'))
print('id:          ', d.get('id'))
print('is_archived: ', d.get('is_archived'))
print('benefits:    ', [b.get('id') for b in d.get('benefits', [])])
for p in d.get('prices', []):
    amt = p.get('price_amount', 0) / 100
    cur = p.get('price_currency', 'usd').upper()
    interval = p.get('recurring_interval') or d.get('recurring_interval', '?')
    print(f'price:        {amt:.2f} {cur} / {interval}')
print()
print('Public storefront URL:')
print(f'  https://polar.sh/battam1111/zk-doctor-pro')
print()
print('Direct checkout URL (use this in README + landing pages):')
print(f'  https://buy.polar.sh/{d.get(\"id\")}')
"
```

If `is_archived` is `false` and you see one price line and one benefit ID, you're live.

The checkout URL pattern `https://buy.polar.sh/{product_id}` is what Polar prints for paid products. Confirm by clicking it in a private window. If Polar returns a different canonical URL in the product response (`checkout_url` field), use that one instead.

---

## Post-launch checklist

After Polar returns a live product:

1. **Verify the storefront** at https://polar.sh/Battam1111/zk-doctor-pro (or whatever slug Polar assigns). Confirm the price, description, and "Activate License" benefit are all visible.

2. **End-to-end license test**:
   ```bash
   # Buy with a test card (use Polar's test mode if enabled, otherwise real $15)
   # 1. Click the checkout URL.
   # 2. Pay with 4242 4242 4242 4242 (Stripe test card) or a real card.
   # 3. Polar sends a confirmation email with the ZKD-... key.
   # 4. Run on this Mac:
   zk-doctor activate ZKD-XXXX-XXXX-XXXX-XXXXXX
   zk-doctor license-status   # should print: tier=pro
   # 5. Run zk-doctor on any ZK repo and confirm all 10 detectors run
   #    (instead of 6 free + 4 locked).
   zk-doctor /path/to/some/zk-repo | grep -E "(circuit_complexity|proving_system_pitfalls|verifier_soundness|multi_file_consistency)"
   ```
   If you see real scores instead of `Locked.` next to each of those four detector names, the loop works.

3. **Update `~/zk-pipeline-doctor/README.md`** "Pro tier" link from the current placeholder to the real product URL Polar returned. Update the same constant in `src/zk_doctor/pro.py` (`UPGRADE_URL`).

4. **Cookbook CTAs (low priority, can defer)**: in `~/midnight-zk-cookbook`, add a "If your project is heading to mainnet, run `zk-doctor` Pro" line to the end of each tutorial's "Next steps" block. Existing free-tier CTAs already point at the CLI; this just adds the Pro upsell once.

5. **Tag and announce** (optional, can defer until after a few sales): push the v0.3.0 tag publicly, write a Bluesky thread about what Pro catches that free does not.

---

## Marketing positioning (use later in landing pages, Bluesky, HN, etc.; NOT for the Polar product itself)

This section is reference copy you can lift into a launch thread, a landing-page hero, or a HN Show post. Do not paste it into Polar.

### Elevator pitch (one paragraph)

zk-doctor Pro is a $15/month subscription that runs a senior ZK auditor's checklist over your repo in under a second. The free CLI already covers tests, CI, docs, secrets, and toolchain pinning across Compact, Leo, Noir, Cairo, and seven Rust zkVMs. Pro adds the four checks an auditor would actually flag in a paid review: circuit-complexity estimation, proving-system soundness pitfalls, Solidity verifier audit, and multi-file consistency. It catches the bugs that survive code review, the kind that show up in retrospectives after mainnet.

### Why now (3 bullets)

- **The ZK ecosystem is fragmenting fast.** Plonky3, SP1, risc0, Stwo, OpenVM, Nexus, Jolt, Noir, Cairo M, Compact, Leo. No two share the same footguns. A Plonky3 trace-width bug is invisible to a Noir linter, and vice versa. A single tool that knows all of them has real leverage.
- **Audit cost is rising and demand outstrips supply.** A full ZK audit runs $20-100k and books out months in advance. Catching cheap bugs in-house first means fewer audit cycles and a lower retainer; Pro pays for itself if it surfaces one missed pin.
- **Multi-file analysis is the new frontier.** The first-generation ZK linters (free, syntax-level) covered low-hanging fruit. The next layer is cross-file: did your Cargo.toml, your CI, your README, and your Solidity verifier all agree on the same proving-system version and the same public-input arity? That layer is what Pro lives in.

### Example PR comment (showing what Pro catches that free does not)

Free tier on a typical SP1 repo says:

```
language: 10 (SP1 detected, Rust toolchain pinned)
tests: 8 (good coverage, missing CI matrix)
ci: 9 (.github/workflows/ci.yml present)
docs: 7 (README has Quick Start, no CONTRIBUTING)
security: 10 (no secrets, gitignore healthy)
reproducibility: 9 (Cargo.lock committed, rust-toolchain.toml present)

Overall: 8.8 / 10
```

Pro tier on the same repo adds:

```
circuit_complexity: 8 (sp1_syscall_uses=47, plonky3_airs=0; moderate complexity, profile recommended)
proving_system_pitfalls: 6 (2 findings)
  - SP1 project: no [patch.crates-io] section in any Cargo.toml; you'll miss Succinct's
    accelerated sha2 / k256 / ed25519 / tiny-keccak patches (10-100x performance hit)
  - SP1: no host-side verify() call found; verify you're actually checking proofs

verifier_soundness: N/A (no Solidity verifiers in repo)

multi_file_consistency: 6 (2 findings)
  - sp1-zkvm pinned to ["3.0.0", "3.1.0"] across Cargo.toml files; workspace should use one version
  - RISC0_DEV_MODE=1 set in 2 places (ci/bench.sh, .env.example); verify neither reaches production CI

Overall: 7.8 / 10 (Pro)
```

The first block is what free already catches. The second block is the one a buyer wakes up to: two concrete fixes their reviewer would have asked about, before they pushed the branch.

---

## Reasoning behind the numbers (internal notes, not buyer-facing)

- **$15/mo** sits below the friction threshold where buyers ask their boss; positions as "I'll expense this on a corporate card without thinking". Annual at $144 keeps the math clean (12 months at $12/mo equivalent, 20% off).
- **5 activations** is enough for one developer's typical setup (laptop, work machine, CI runner, spare) and tight enough to deter team-wide key sharing without being adversarial to small audit teams.
- **No usage limit** because the CLI is read-only and metering would create friction without revenue.
- **No key expiration** because Polar already revokes keys when subscriptions cancel; double-expiry is just extra confusion.
- **30-day refund** is one notch above the 14-day default. Higher cancellation cost up front is offset by lower-friction sales: buyers don't second-guess a $15 trial.
