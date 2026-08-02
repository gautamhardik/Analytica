#!/bin/sh
set -e

DB="brazilian_ecommerce_dw"
DUMP="/init/dump_brazilian_ecommerce_dw.sql"
PASS="$MYSQL_ROOT_PASSWORD"

if [ ! -f "$DUMP" ]; then
  echo "[seed] No SQL dump found at $DUMP - skipping import."
  exit 0
fi

echo "[seed] Importing DW dump (FK checks disabled, redundant view/segment INSERTs stripped)..."
# The dump creates tables with FK references before their referenced tables exist,
# so import with FOREIGN_KEY_CHECKS disabled. It also contains redundant INSERT
# statements targeting the vw_customer_persona VIEW (which cannot be inserted
# into) and stale v1.0 INSERTs for customer_segment_ml (rebuilt by the
# segmentation trainer) - strip those blocks.
awk '
  /^INSERT INTO `customer_segment_ml`/{skip=1}
  /^INSERT INTO `vw_customer_persona`/{skip=1}
  skip && /;$/ {skip=0; next}
  skip {next}
  {print}
' "$DUMP" | mysql -uroot -p"$PASS" --init-command="SET FOREIGN_KEY_CHECKS=0" "$DB"

echo "[seed] DW dump imported."
