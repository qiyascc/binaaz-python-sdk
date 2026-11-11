# Changelog

## 0.1.0

- Sync `BinaAz` and async `AsyncBinaAz`
- Sign in with email and password, or with an SMS code through the login service bina.az uses
- The session is a plain cookie string you can save and pass back; Cloudflare cookies are never kept
- Create, update, delete, prolong, read and list listings, with cursor pages and a helper that reads every page
- Listing model with the bina.az rules: 4 to 30 photos, floor not above the building, daily rent only for rentals
- Refused listings raise `ItemError` with the bina.az status (`RESTRICTED`, `UNVERIFIED`, `INVALID`, `FAILURE`, `LOCKED`)
- Paid services and paying for a listing need `confirm=True`
- Photo upload from bytes, paths or files, and rotation
- Catalog: categories, cities, regions, townships and landmarks
- Writes are never resent after an ambiguous failure; reads retry with backoff; 429 waits for `Retry-After`
- The SMS login service is retried when it answers without a known error, and says when more than one SMS may arrive
- Cloudflare challenge pages raise `BlockedError`
- goodconf settings, endpoint paths and messages are configurable
