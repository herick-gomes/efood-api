# Restoring the original Efood restaurant catalog

The original frontend fetched course demo data from:
`https://api-ebac.vercel.app/api/efood/restaurantes`.

This repository includes a source snapshot captured on **2026-11-26**:
`shop/fixtures/ebac_restaurantes.json` (6 restaurants, 22 products, original food photos and prices).

## What gets imported

- All six original restaurants, with their exact original names, descriptions, categories, featured flags, images and menus.
- All 22 original demo products (names, prices, descriptions, portions and image URLs).
- New products receive a starting demo stock of 30.
- **Nothing is deleted or overwritten**: existing owners, the two new restaurants, stock and order history remain unchanged.
- A dedicated merchant `efood_legacy_import` owns the imported entries and has an unusable password.
- Source rating numbers are intentionally not imported as customer reviews. The API returns zero/unrated.
- Product IDs are newly allocated by PostgreSQL; the checkout uses those database IDs.

## Safe SQL import in Neon production

1. Back up the existing Neon branch or create a recovery branch/snapshot first.
2. Open the **correct** Neon project and `neondb` SQL Editor (verify the primary branch).
3. Inspect the [SQL script](../scripts/import_ebac_catalog.sql), then paste all of it and run once.
4. The final SELECT reports each imported restaurant and its product count.
5. Confirm the public catalog now shows eight restaurants and 26 products (if no other records have been added):
   `https://efood-api-ten.vercel.app/api/v1/legacy/restaurantes/`
6. Refresh the production frontend: `https://efood-kappa-three.vercel.app/`

The SQL can be safely repeated because it uses insert-if-missing checks scoped to the import owner. It will **not** reset stock or prices after checkout.

## Local Django import alternative

```bash
python manage.py import_ebac_catalog
python manage.py import_ebac_catalog --apply
```

The first command only validates the fixture. The second imports under one database transaction.

**Notes:** This is an educational portfolio demonstration, not an actual restaurant service. The product photographs remain hosted by the source API, so they may stop working if that source changes. Source images and content should be reviewed for reuse rights before any real commercial deployment. No real ratings, payments or deliveries are represented.
