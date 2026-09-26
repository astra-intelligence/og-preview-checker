# OG Preview Checker

Check whether any GitHub repository has a custom social preview (Open Graph) image — and generate one for free.

**Live tool:** [http://167.233.135.161:8081](http://167.233.135.161:8081)
**API Docs:** [http://167.233.135.161:8081/api/docs](http://167.233.135.161:8081/api/docs)

## Features

- **Check any repo** — see if it has a custom OG image and view the current preview
- **Generate free OG images** — auto-generated previews for repos that lack one
- **Batch API** — programmatically check multiple repos (Pro license required)

## Quick Start

```bash
# Check a repo
curl "http://167.233.135.161:8081/api/check?url=https://github.com/vercel/next.js"

# Generate a free OG image
curl -X POST "http://167.233.135.161:8081/api/generate" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com/vercel/next.js"}'

# Batch check (Pro license required)
curl -X POST "http://167.233.135.161:8081/api/batch" \
  -H "Content-Type: application/json" \
  -d '{"license_key": "YOUR_KEY", "repos": ["vercel/next.js", "tailwindlabs/tailwindcss"]}'
```

## Pricing

| Tier | Price | Features |
|------|-------|----------|
| Free | $0 | Single repo check, free OG image generation |
| Pro | $3+ (PWYW) | Batch API (10 repos), license key, commercial use |

**Get a Pro license:** https://grantshatz.gumroad.com/l/og-preview-api-license

## Tech Stack

- Python + Flask
- GitHub GraphQL API
- PIL (Pillow) for image generation
- Gumroad for license key management

## License

MIT — see [LICENSE](LICENSE).

---

## Support

If you find this project useful, consider [buying me a coffee](https://buymeacoffee.com/grantshatzer) or [sponsoring on GitHub](https://github.com/sponsors/astra-intelligence).

Check out more tools at [grantshatz.gumroad.com](https://grantshatz.gumroad.com).

