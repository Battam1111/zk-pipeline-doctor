# Polar product TODO: zk-doctor Pro

This file documents the one-time setup needed to publish the **zk-doctor Pro**
subscription product on Polar so the v0.3.0 license framework actually pays out.
The framework code (`src/zk_doctor/license.py` + the `@pro_only` decorator) is
already wired against Polar's customer-portal validation API; it just needs a
real product + license-key benefit on the org side.

---

## What you (the operator) need to do

You have two paths. **Dashboard is the safe path; API is the fast path.**

### Path A — Dashboard (recommended, takes ~5 minutes)

1. Open https://polar.sh/dashboard/Battam1111/benefits and click **+ New Benefit**.
2. Pick type **License Keys**.
3. Configure:
   - **Name**: `zk-doctor Pro License`
   - **Prefix**: `ZKD` (so keys look like `ZKD-XXXX-XXXX-...`)
   - **Expires after**: leave unset (license lives as long as the subscription)
   - **Activation limit**: `5` (lets one buyer use up to 5 machines; deters key sharing without being adversarial to small teams)
   - **Usage limit**: leave unset
4. Save.
5. Open https://polar.sh/dashboard/Battam1111/products and click **+ New Product**.
6. Configure:
   - **Name**: `zk-doctor Pro`
   - **Description** (copy block below)
   - **Price**: `$15/mo` recurring (Polar will surface the appropriate subscription cadence selector)
   - **Benefits**: attach the `zk-doctor Pro License` benefit you created in step 3.
7. Save.
8. Polar gives you a checkout URL like `https://polar.sh/checkout/polar_c_XXXX...`. Paste it into the README (replacing the placeholder under "Pro tier").
9. Make a test purchase yourself (Polar supports a test mode). Take the key you receive, run `zk-doctor activate <key>` on this mac, confirm it caches as `pro`.

### Path B — One API call (faster if you trust the inputs)

If you'd rather not click through the dashboard, the entire setup is two API calls. You'll need `POLAR_TOKEN` from `~/bounty-agent/secrets/polar.json` (`d['token']`).

```bash
POLAR_TOKEN="$(python3 -c 'import json; print(json.load(open("/Users/chenyanyun/bounty-agent/secrets/polar.json"))["token"])')"
ORG_ID="b23fe650-4bde-4d68-983a-67f93e39224f"

# 1. Create the license-key benefit
BENEFIT=$(curl -sS -X POST "https://api.polar.sh/v1/benefits/" \
  -H "Authorization: Bearer $POLAR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "organization_id": "'"$ORG_ID"'",
    "type": "license_keys",
    "description": "zk-doctor Pro License key",
    "properties": {
      "prefix": "ZKD",
      "activations": {"enable_customer_admin": true, "limit": 5},
      "expires": null,
      "limit_usage": null
    }
  }')
echo "$BENEFIT"
BENEFIT_ID=$(echo "$BENEFIT" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 2. Create the subscription product and attach the benefit
curl -sS -X POST "https://api.polar.sh/v1/products/" \
  -H "Authorization: Bearer $POLAR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "organization_id": "'"$ORG_ID"'",
    "name": "zk-doctor Pro",
    "description": "Per-developer subscription unlocking the 4 deep cross-ecosystem detectors in zk-pipeline-doctor: circuit_complexity, proving_system_pitfalls, verifier_soundness, multi_file_consistency. Polar license-key benefit; activates on up to 5 machines.",
    "recurring_interval": "month",
    "prices": [{"amount_type": "fixed", "price_amount": 1500, "price_currency": "usd"}],
    "benefits": ["'"$BENEFIT_ID"'"]
  }'
```

The product response will include a `checkout_url`; paste it into the README.

---

## Suggested product copy

**Name**: `zk-doctor Pro`

**Tagline**: Cross-ecosystem deep audit for serious ZK projects.

**Description**:

> zk-doctor Pro adds 4 deep cross-ecosystem detectors on top of the free 6-detector CLI:
>
> - **circuit_complexity** — estimate circuit size across Plonky3 AIRs, SP1 program syscall counts, Compact circuit counts, Noir assert/loop hints, and Cairo function counts
> - **proving_system_pitfalls** — soundness footguns by ecosystem: risc0 dev-mode leak, SP1 missing patches, Plonky3 default field/PCS, Stwo default proof config, Noir/Compact toolchain pin drift
> - **verifier_soundness** — Solidity ZK-verifier audit checklist: delegatecall presence, scalar-field bounds on public inputs, G1/G2 zero-point checks, pairing-precompile gas griefing, malleability
> - **multi_file_consistency** — proving-system version pinned consistently across Cargo.toml/README/CI; dev-vs-prod feature flag drift; circuit signature vs verifier arity drift; Cargo.lock dialect consistency
>
> Free tier (which everyone keeps forever) still covers language detection, tests, CI, docs, security hygiene, and reproducibility — the basics. Pro is the layer above.
>
> $15/mo per developer. Activates on up to 5 machines per license. Polar handles billing as Merchant of Record (handles VAT/sales tax). 14-day money-back guarantee.

**Price**: `$15.00 USD / month` (one tier; team / enterprise can be added later if there's signal).

**Benefits attached**: `zk-doctor Pro License` (license-key type with `ZKD` prefix, 5 activations).

---

## Reasoning behind the numbers

- **$15/mo**: matches Bounty Radar Hobbyist ($19/mo), is below the friction threshold where buyers ask their boss; positions as "I'll expense this on a corporate card without thinking". A team/seat-pricing tier can come after we see a few individual sales.
- **5 activations per key**: enough for a typical dev's laptop + work mac + CI runner + spare; tight enough that key-sharing across an entire team will trip the limit.
- **No usage limit**: the doctor is read-only and runs in <5 seconds; metering it would be friction without revenue.
- **No expiration on key**: license lifetime == subscription lifetime, which Polar already handles by revoking the key when the subscription cancels.

---

## After you publish

1. Replace the `Pro` placeholder URL in `README.md` (currently `https://polar.sh/Battam1111/zk-doctor-pro`) with the real checkout link Polar returns.
2. Also update `src/zk_doctor/pro.py` `UPGRADE_URL` constant (same URL).
3. Smoke test: buy the product yourself (Polar test mode → Stripe test card → real key issued), run `zk-doctor activate <key>` and confirm `zk-doctor license-status` reports `pro`.
4. Push the v0.3.0 tag.
5. Announce in the cookbook landing + Bluesky.

If the API call returns an error, `polar.json` has all credentials already; the only thing this code did not do for you is decide the product name + price + activation limit, because that's a positioning call.
