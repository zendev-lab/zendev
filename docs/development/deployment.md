# Deploy the documentation

The documentation is a static Zensical site deployed as Cloudflare Workers
Static Assets. `wrangler.toml` is the deployment source of truth: it publishes
the generated `site/` directory as the `zendev-docs` Worker and attaches the
`docs.zendev.zrr.dev` custom domain.

Cloudflare Workers Builds owns production and preview deployment. GitHub Actions
only validates the documentation; it does not store Cloudflare credentials or
deploy the site.

## Validate without deploying

Build the site and run Wrangler's local deployment checks:

```shell
just docs-build
npx --yes wrangler@4.128.0 deploy --dry-run
```

The dry run does not require Cloudflare credentials and does not upload assets.

## Configure Workers Builds once

Create or select the `zendev-docs` Worker in the Cloudflare account that owns
the active `zrr.dev` zone. Connect its **Settings > Builds** Git integration to
the `zendev-lab/zendev` repository. The Cloudflare Workers and Pages GitHub App
must have access to that organization and repository.

Use these build settings:

| Setting | Value |
| --- | --- |
| Production branch | `main` |
| Root directory | Leave empty (repository root) |
| Build variable | `SKIP_DEPENDENCY_INSTALL=1` |
| Build command | `pipx run --spec uv==0.12.1 uv run --locked --group docs zensical build --clean --strict` |
| Deploy command | `npx --yes wrangler@4.128.0 deploy --strict` |
| Non-production branch deploy command | `npx --yes wrangler@4.128.0 versions upload` |

Enable non-production branch builds when pull requests should receive preview
versions. Cloudflare reports the result back to GitHub as a
`Workers Builds: zendev-docs` check.

Workers Builds creates and retains its deployment token on the Cloudflare side;
the GitHub repository does not need `CLOUDFLARE_API_TOKEN` or
`CLOUDFLARE_ACCOUNT_ID` secrets.

The first production build creates the `docs.zendev.zrr.dev` custom-domain DNS
record and its certificate. The zone must already be active in Cloudflare, and
the hostname must not have an existing CNAME record.
