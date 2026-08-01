#!/usr/bin/env bash
#
# Cloudflare config for the Slop Audit web tool, as code.
#
# Unlike the canonical thinair apply-cdn-config.sh (which owns a whole zone and
# PUTs the entire ruleset), this tool lives on a SUBDOMAIN of an existing shared
# zone (slopaudit.org, which already fronts the marketing site). So this script
# is deliberately non-destructive:
#   - it upserts ONE proxied CNAME for the subdomain (never touches apex/www),
#   - it MERGES its cache + rate-limit rules into the zone's existing rulesets,
#     keyed by description, so re-runs converge and the marketing site's own
#     rules are left untouched.
#
# All of this tool's rules are scoped to `http.host eq "$FQDN"`, so they can only
# affect the subdomain.
#
# Usage:
#   export CF_API_TOKEN=...     # Zone:Read, DNS:Edit, Cache Rules:Edit, and
#                               #   "Account > Zone WAF:Edit" for the rate-limit rule
#   export DOMAIN=slopaudit.org
#   export SUBDOMAIN=audit                       # -> audit.slopaudit.org
#   export RENDER_ORIGIN=slop-audit-web.onrender.com
#   ./cloudflare/apply-audit-cdn.sh

set -euo pipefail

: "${CF_API_TOKEN:?Set CF_API_TOKEN (Zone:Read, DNS:Edit, Cache Rules:Edit, WAF:Edit)}"
: "${DOMAIN:?Set DOMAIN, e.g. slopaudit.org}"
: "${SUBDOMAIN:?Set SUBDOMAIN, e.g. audit}"
: "${RENDER_ORIGIN:?Set RENDER_ORIGIN, e.g. slop-audit-web.onrender.com}"

FQDN="$SUBDOMAIN.$DOMAIN"
API="https://api.cloudflare.com/client/v4"
command -v jq >/dev/null || { echo "jq is required"; exit 1; }

cf() {
  local method="$1" path="$2" body="${3:-}"
  local args=(-sS -X "$method" "$API$path"
    -H "Authorization: Bearer $CF_API_TOKEN"
    -H "Content-Type: application/json")
  [[ -n "$body" ]] && args+=(--data "$body")
  curl "${args[@]}"
}
ok() { jq -e '.success' >/dev/null 2>&1; }

echo "==> Resolving zone for $DOMAIN"
ZONE_ID="$(cf GET "/zones?name=$DOMAIN" | jq -r '.result[0].id // empty')"
[[ -n "$ZONE_ID" ]] || { echo "    Zone for $DOMAIN not found on this account. Create it first."; exit 1; }
echo "    Zone $ZONE_ID"

# --- DNS: one proxied CNAME for the subdomain -------------------------------
echo "==> DNS: $FQDN -> $RENDER_ORIGIN (proxied)"
EXISTING="$(cf GET "/zones/$ZONE_ID/dns_records?type=CNAME&name=$FQDN" | jq -r '.result[0].id // empty')"
PAYLOAD="$(jq -n --arg n "$FQDN" --arg c "$RENDER_ORIGIN" \
  '{type:"CNAME", name:$n, content:$c, proxied:true, ttl:1}')"
if [[ -n "$EXISTING" ]]; then
  cf PUT "/zones/$ZONE_ID/dns_records/$EXISTING" "$PAYLOAD" | ok && echo "    updated"
else
  cf POST "/zones/$ZONE_ID/dns_records" "$PAYLOAD" | ok && echo "    created"
fi

# --- Merge a rule into a phase entrypoint, non-destructively -----------------
# Drops any prior rule with the same description (idempotent re-run), then
# appends ours LAST so a host-scoped rule wins over any zone-wide default.
merge_rule() {
  local phase="$1" rule="$2" desc
  desc="$(echo "$rule" | jq -r '.description')"
  local current
  current="$(cf GET "/zones/$ZONE_ID/rulesets/phases/$phase/entrypoint" | jq -c '.result.rules // []')"
  local merged
  merged="$(jq -cn --argjson cur "$current" --argjson r "$rule" --arg d "$desc" \
    '{rules: ([$cur[] | select(.description != $d)] + [$r])}')"
  cf PUT "/zones/$ZONE_ID/rulesets/phases/$phase/entrypoint" "$merged" | ok \
    && echo "    ok: $desc" \
    || { echo "    ! failed: $desc"; cf PUT "/zones/$ZONE_ID/rulesets/phases/$phase/entrypoint" "$merged" | jq '.errors'; }
}

# --- Cache: respect the origin's Cache-Control on this host ------------------
# The origin sends `max-age=3600` on a scorecard and `no-store` on every error,
# so respect_origin caches good results for an hour at the edge and never caches
# an error. Repeat audits of the same repo are served from cache; the origin
# only works on a miss.
echo "==> Cache rule (respect origin) for $FQDN"
merge_rule "http_request_cache_settings" "$(jq -n --arg h "$FQDN" '{
  description: ("slop-audit-web: cache on " + $h + " (respect origin)"),
  expression: ("(http.host eq \"" + $h + "\")"),
  action: "set_cache_settings",
  action_parameters: {
    cache: true,
    edge_ttl:    { mode: "respect_origin" },
    browser_ttl: { mode: "respect_origin" }
  }
}')"

# --- Rate limit: block bursts on /audit at the edge -------------------------
# Edge backstop in front of the app's own per-IP limiter. A cache HIT does not
# count against this, so only cache MISSES (real origin work) are limited.
echo "==> Rate-limit rule for $FQDN/audit"
merge_rule "http_ratelimit" "$(jq -n --arg h "$FQDN" '{
  description: ("slop-audit-web: rate-limit /audit on " + $h),
  expression: ("(http.host eq \"" + $h + "\" and starts_with(http.request.uri.path, \"/audit\"))"),
  action: "block",
  ratelimit: {
    characteristics: ["ip.src"],
    period: 60,
    requests_per_period: 20,
    mitigation_timeout: 60
  }
}')"

echo
echo "Done. Verify once DNS has propagated:"
echo "  # first hit is a MISS, second the same URL should be a HIT:"
echo "  curl -sI \"https://$FQDN/audit?url=openhonest/slop-audit\" | grep -i cf-cache-status"
echo "  curl -sI \"https://$FQDN/audit?url=openhonest/slop-audit\" | grep -i cf-cache-status"
