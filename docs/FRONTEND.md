# Contract with the Efood React client

The original Efood frontend was inspected before implementing the adapter. Its `Restaurant` and `Dish` types use Portuguese field names (`titulo`, `cardapio`, `preco`, etc.). `/api/v1/legacy/restaurantes/` returns that read-only shape, without pagination, while `/api/v1/restaurants/` exposes the native paginated API.

There are no real ratings in the demo dataset. The compatibility field `avaliacao` is always zero (unrated), not a fabricated review score. Stockless, unavailable and archived products are omitted; closed restaurants are omitted from the legacy catalog.

The old EBAC checkout accepted client prices and card fields. This API intentionally does not copy that write contract. The new client sends product IDs, quantities and delivery details, with a Bearer access token and UUID Idempotency-Key. Card and price fields are rejected.

The integration branch `feat/own-api-integration` in `herick-gomes/Efood` includes:

- Catalog requests to the compatibility adapter.
- An in-memory JWT client with refresh rotation and logout.
- Customer sign-in/registration at checkout.
- Explicitly simulated checkout without card inputs.
- A stable key for retrying the same checkout intent while the cart component remains mounted.
- The confirmed server total in the confirmation screen.
- A separate cart-storage namespace, avoiding collisions with old EBAC product IDs.
- Client and component tests for token handling, no card payload, login errors and retry keys.

A page reload requires logging in again and does not preserve checkout idempotency intent. This limitation is documented; production clients would need a durable checkout-intent design. The cart still supports one unit per product and mixed-restaurant carts are rejected by the backend.

Frontend changes are prepared for review, not merged into the published site. Deploy the API, configure the exact CORS origin and frontend environment URL, and exercise the complete flow in a real browser before merging.
