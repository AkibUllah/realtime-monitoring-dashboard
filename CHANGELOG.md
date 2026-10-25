# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Screenshots in the README: live dashboard recording, fleet view, API reference and a curl session.
- CodeQL code scanning workflow (Python, JavaScript/TypeScript and Actions) and Dependabot updates for pip, npm, Docker and GitHub Actions.
- Roadmap tracked as GitHub issues under the v0.2.0 milestone.
- This changelog.

### Changed

- CI workflow runs with a read-only `GITHUB_TOKEN` by default.

## [0.1.0] - 2026-10-25

First public release.

### Added

- Host collector (psutil) for CPU, memory, disk and network throughput.
- Deterministic fleet simulator across Dhaka/Chattogram regions with CPU spikes, memory leaks and node-down incidents.
- Ring-buffer time-series store per node and metric with range queries and bucket-average downsampling; optional SQLite persistence with warm start.
- Threshold-for-duration alert rules with OK → FIRING → RESOLVED state per node, node/role/region filters and a notification log.
- WebSocket `/ws/metrics` (snapshot on connect, then one message per tick) and REST endpoints for history, nodes, rules and notifications.
- React + Recharts dark UI with live charts, node grid, alerts panel with rule toggles, time-range selector and a reconnecting WebSocket hook with jittered backoff.
- 29 backend and 21 frontend tests, CI for Python 3.10/3.11 and Node 18/20, docker compose with an nginx reverse proxy.
- Live demo kit: Swagger UI on GitHub Pages, Codespaces dev container and Render blueprint.

### Fixed

- The frontend image proxies `/api` and `/ws` itself, so it works without the compose nginx.

[Unreleased]: https://github.com/AkibUllah/realtime-monitoring-dashboard/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/AkibUllah/realtime-monitoring-dashboard/releases/tag/v0.1.0
