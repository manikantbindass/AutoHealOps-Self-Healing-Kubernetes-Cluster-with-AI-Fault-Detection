# Vercel public demo

Public URL: **https://autohealops.vercel.app**. Vercel project `autohealops`, root `frontend`, Node 22; deployment status verified READY.

The Vercel build publishes an explicitly labelled, interactive **browser-only simulation**. It does not run the Kubernetes control plane, a trained AI model, FastAPI, MongoDB or WebSockets. Each visitor has a separate, bounded browser session; no credentials or infrastructure are connected. The application never silently substitutes this mode after an API error.

`npm run build` remains the regular backend-connected application. `npm run build:demo` uses the committed non-secret `.env.showcase` flag and emits `build-public/`. Vercel's project root is `frontend`, with `frontend/vercel.json` providing the SPA deep-link rewrite and response headers. The root config intentionally has no backend rewrite: public mode performs no API or WebSocket calls.

The public demo supports all eight views, changing synthetic telemetry every five seconds, fault injection, clearly labelled rule-based detections, incident triage, approvals, pause/resume, simulated restart/scale outcomes and audit history. Before/after metrics are simulated. Recovery cooldown is 30 seconds in the public showcase; the actual backend default remains 300 seconds. The hourly limit is ten simulated operations per browser session. Closing the session clears its state; reloading preserves history and resets healing to paused. These browser controls are demonstration logic, not security boundaries for real infrastructure.

Forecasts and trained ML are explicitly unavailable on the public demo. Use the native or Compose workflow for those services. A continuously running, privately secured backend is required to deploy the actual control plane; Vercel static hosting does not host the collector or a live Kubernetes cluster.

Validation: browser-demo tests exercise provenance, approval/pause, idempotency, input boundaries, deduplication and reset. Browser E2E inspects the deployed app without API mocks, asserts no API/WebSocket traffic, exercises the demo recovery flow and deep links, and checks mobile width.


## Publish updates

From the repository root, use the authenticated Vercel CLI in the same project scope:

```powershell
vercel link --project autohealops --scope manikantkai-9844s-projects
vercel deploy --prod --scope manikantkai-9844s-projects
```

The root `.vercelignore` uploads frontend sources only and excludes dependencies, generated builds and private `.env`. GitHub Actions validates both the normal backend-connected build and the public-demo build; publishing is a deliberate Vercel deployment, not an implicit promise that every push automatically goes live.

## Automatic simulation

Settings now offers Autonomous recovery. Save it, resume healing, then inject a fault. Three browser samples trigger an automatic simulated recovery without per-action approval; the related incident resolves. Manual mode, emergency pause, cooldown and action budgets remain available. Reloading pauses healing and restores manual policy. This never connects to infrastructure. See [live autonomous runbooks](autonomous-recovery.md) for the separately configured backend.
