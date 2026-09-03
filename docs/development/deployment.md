# Deploy the documentation

The documentation is a static Zensical site deployed as Cloudflare Workers
Static Assets. `wrangler.toml` is the deployment source of truth: it publishes
the generated `site/` directory as the `zendev-docs` Worker and attaches the
`docs.zendev.zrr.dev` custom domain.

## Validate without deploying

Build the site and run Wrangler's local deployment checks:

```shell
just docs-build
npx --yes wrangler@4.128.0 deploy --dry-run
```

The dry run does not require Cloudflare credentials and does not upload assets.

## Configure GitHub once

Create a Cloudflare API token with the **Edit Cloudflare Workers** template,
restricted to the account and `zrr.dev` zone used by the site. Then add the
account ID and token as GitHub Actions secrets:

```shell
gh secret set CLOUDFLARE_ACCOUNT_ID --repo zendev-lab/zendev
gh secret set CLOUDFLARE_API_TOKEN --repo zendev-lab/zendev
```

The first deployment creates the Worker and the `docs.zendev.zrr.dev` custom-domain
DNS record. The zone must already be active in Cloudflare, and the hostname must
not have an existing CNAME record.

Run the workflow manually for the first deployment:

```shell
gh workflow run cd-documentation.yml --repo zendev-lab/zendev
```

After the deployment and public URL are verified, enable automatic deployment
for future pushes to `main`:

```shell
gh variable set CLOUDFLARE_DEPLOY_ENABLED --body true --repo zendev-lab/zendev
```

Until that variable is set, pushes to `main` skip the deployment job. Manual
dispatch remains available for setup and recovery.
