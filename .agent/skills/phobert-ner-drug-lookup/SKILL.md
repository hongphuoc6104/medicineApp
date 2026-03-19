# Skill: PhoBERT NER And Drug Lookup

## Current Reality

- NER is still limited compared with the planned richer medication extraction model
- false positives can happen when quantity or usage resembles drug text
- lookup quality depends on OCR quality and VN drug DB coverage

## Important Concepts

- `confirmed`
- `unmapped_candidate`
- `rejected_noise`

## Review Order

1. OCR text quality
2. NER label quality
3. fuzzy match quality
4. final display name and confidence
