# Vendored static assets

GitHubMonitor serves browser assets from this directory so the UI can run without a CDN dependency.

Chart.js is pinned to version 4.5.1. The expected file is:

```text
static/chart.umd.min.js
```

Source:

```text
https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js
```

The Chart.js license is retained in `LICENSE.Chart.js`.
