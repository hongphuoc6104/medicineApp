# Medicine Agent Kit Plan

This document maps upstream ideas into the repo-specific `.agent` kit.

## 1. Mapping From `antigravity-kit`

### Kept Conceptually

- agent routing
- skill loading
- reusable workflows
- role-based planning/debug/testing structure

### Kept In Project Scope

- backend specialist
- mobile developer
- debugger
- project planner
- test engineer
- database architect
- orchestrator
- documentation writer

### Not Prioritized

- game development tracks
- SEO-centric workflows
- generic Next.js-first assumptions

## 2. Mapping From `ui-ux-pro-max-skill`

### Kept Conceptually

- design-system generation mindset
- anti-pattern avoidance
- style selection by product category
- page override pattern over a master design system

### Adapted For `medicineApp`

- healthcare accessibility first
- older-user readability
- light theme by default
- no flashy generic AI visual language
- stronger focus on empty/error/offline states

## 3. New Domain Layer Added

- protected Phase A guardrails
- VN drug DB knowledge
- scan-session flow
- medication plan domain
- reminder offline sync
- demo and pilot runbooks

## 4. Suggested First Use Cases

1. redesign Home using `ux-health`
2. debug scan regressions using `scan-debug`
3. plan plan-edit flow using `plan-feature`
4. check demo readiness using `demo-ready`
5. review pilot blockers using `pilot-check`
