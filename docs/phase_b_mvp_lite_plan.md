# Phase B MVP-Lite Plan

## Goal

Kick off Phase B without waiting for full automatic contrastive matching.

The first version should help the user verify pills before taking them and, at the same time, collect structured feedback for future model training.

## Why MVP-Lite

Current reality:
- pill detection code exists in `core/phase_b/s1_pill_detect/pill_detector.py`
- matching code exists in `core/phase_b/s2_match/gcn_matcher.py`
- full contrastive matching is not production-ready yet

So the right first product is:
- detect pills
- show crops to the user
- let the user confirm or correct them
- save feedback as training/evaluation data

## User Flow

1. User opens a due dose from Home.
2. User taps `Kiem tra thuoc truoc khi uong`.
3. App opens `PillScanScreen`.
4. User captures one image containing all pills for the current dose.
5. Backend returns detected pill boxes.
6. App shows each crop in `PillReviewScreen`.
7. User assigns each pill to one of the expected medications or marks it unknown.
8. App shows summary:
   - matched
   - missing
   - extra
   - unsure
9. User taps `Xac nhan da uong`.

## MVP Scope

### In Scope

- pill scan session for one due dose
- detection-only backend path
- review UI with manual assignment
- result summary and save
- feedback storage for future training

### Out Of Scope

- fully automatic final matching
- zero-shot production claims
- family mode / multi-patient support
- deep interaction checking in this phase

## Screens

### 1. Pill Scan Screen

Actions:
- `Chup anh`
- `Chon tu thu vien`
- `Chup lai`
- `Quet lai`
- `Dung khong kiem tra`

UI states:
- camera ready
- processing
- detection failed
- too dark / blurry / glare warning

### 2. Pill Review Screen

For each detection:
- show crop
- show score
- `Gan vao thuoc ...`
- `Khong chac`
- `Xoa vien nay`

Bottom summary:
- expected list
- matched count
- missing count
- extra count

Primary CTA:
- `Xac nhan da uong`

### 3. Verification Result Sheet

Summary buckets:
- dung
- thieu
- thua
- khong chac

CTA:
- `Sua lai`
- `Xac nhan`

## Backend Plan

### Node Routes

- `POST /api/pill-verifications/start`
- `POST /api/pill-verifications/:id/image`
- `POST /api/pill-verifications/:id/assign`
- `POST /api/pill-verifications/:id/confirm`
- `GET /api/pill-verifications/:id`

### Python Bridge

Short term:
- expose a detector-first endpoint based on `PillDetector`

Later:
- return top-N assisted matching suggestions

## Data Model

### Suggested Tables

- `pill_verification_sessions`
- `pill_detections`
- `pill_detection_crops`
- `pill_assignments`
- `pill_feedback`

## Labels For Review

- `matched_expected`
- `missing_expected`
- `extra_detected`
- `unknown_pill`
- `user_corrected`

## Technical Milestones

### Milestone 1

- define contract
- create screens and navigation
- use mock data in UI

### Milestone 2

- connect detection-only backend
- save session and assignment results

### Milestone 3

- export feedback dataset
- add evaluation notebook/script

### Milestone 4

- test assisted matching baseline
- compare against manual review quality

## Success Criteria For MVP-Lite

- user can finish a verification flow on a phone
- system stores structured feedback for every corrected pill
- Phase B creates value before full matching is ready
- no false claim of automatic certainty
