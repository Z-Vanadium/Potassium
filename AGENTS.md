# AGENTS.md

## Project Overview

课程实验：通过浏览器自动化脚本"养号"，在不同社交平台构建差异化的用户画像（user profile portraits）。

## Tech Stack (TBD - choose from evaluation below)

- **Automation Core**: Playwright (Python or Node.js/TypeScript)
- **Anti-Detection**: playwright-stealth / puppeteer-extra-plugin-stealth
- **Platforms**: 微博, 小红书, 抖音, B站, 知乎, X/Twitter, LinkedIn

## Key Constraints

- This is a course project — prefer lightweight, single-machine solutions over distributed/cloud setups
- Account safety is critical: stealth/human-like behavior is mandatory, not optional
- Each platform needs independent session isolation (separate browser contexts, cookies, fingerprints per account)
- Chinese platforms (微博/小红书/抖音/B站/知乎) have different anti-bot mechanisms than Western platforms — use platform-specific tools when available

## Architecture Principles

- **Session isolation per account**: Each social media account gets its own Playwright `BrowserContext` with isolated storage state
- **Stealth-first**: Always apply anti-detection patches before any navigation
- **Human-like behavior**: Random delays (1-5s between actions), natural typing speed (50-150ms/char), mouse movement simulation
- **Persistent profiles**: Save and reuse `storageState` (cookies + localStorage) to avoid repeated logins
- **Rate limiting**: Enforce daily action caps per account; actions spread across active hours

## Project Conventions (once implementation starts)

- Use `uv` for Python dependency management if Python is chosen
- Use `pnpm` for Node.js monorepo if TypeScript is chosen
- Run `lsp_diagnostics` on changed files before committing
- No `as any`, `@ts-ignore`, or type suppression
- Prefer existing open-source modules — do not reinvent browser automation primitives

## References

- [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) — reference implementation for multi-platform Chinese social media automation with Playwright
- [playwright-stealth](https://github.com/ozio/stealth) — current best Playwright stealth plugin
- [rebrowser-patches](https://github.com/rebrowser/rebrowser-patches) — CDP-level anti-detection patches
