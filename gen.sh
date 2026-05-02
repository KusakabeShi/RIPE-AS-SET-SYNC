#!/bin/bash
set -e
cd "$(dirname "$0")"

DAYS="${1:-365000}"
MNT="${2:-RIPE-MNT}"

echo "Generating X.509 cert valid for $DAYS days, mnt-by: $MNT"

openssl req -x509 -days "$DAYS" -newkey rsa:4096 -sha384 \
  -subj "/C=TW/CN=ripe-asset-automation" \
  -keyout client-key.pem -nodes -out client-cert.pem 2>/dev/null

cp client-cert.pem GITHUB_SECRET_RIPE_CLIENT_CERT.txt
cp client-key.pem GITHUB_SECRET_RIPE_CLIENT_KEY.txt

# Generate RIPE DB key-cert RPSL object
{
  echo "key-cert:        AUTO-1"
  while IFS= read -r line; do
    echo "certif:          $line"
  done < client-cert.pem
  echo "mnt-by:          $MNT"
  echo "source:          RIPE"
} > ripe-key-cert-object.txt

echo ""
openssl x509 -in client-cert.pem -noout -subject -dates
echo ""
echo "Files generated:"
echo "  client-cert.pem / client-key.pem        - X.509 cert & key"
echo "  GITHUB_SECRET_RIPE_CLIENT_CERT.txt      - GitHub Secret: RIPE_CLIENT_CERT"
echo "  GITHUB_SECRET_RIPE_CLIENT_KEY.txt       - GitHub Secret: RIPE_CLIENT_KEY"
echo "  ripe-key-cert-object.txt                - Paste into RIPE DB to create key-cert"
echo ""
echo "Next steps:"
echo "  1. Create key-cert in RIPE DB with ripe-key-cert-object.txt"
echo "  2. Add 'auth: X509-nnn' to $MNT"
echo "  3. Update GitHub Secrets: RIPE_CLIENT_CERT and RIPE_CLIENT_KEY"
