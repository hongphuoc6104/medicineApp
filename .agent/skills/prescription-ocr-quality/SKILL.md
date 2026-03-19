# Skill: Prescription OCR Quality

## Primary Quality Axes

- blur
- glare
- content cutoff
- orientation
- convergence across multiple captures

## UX Requirement

Every rejection or warning should tell the user what to do next:
- move back
- reduce glare
- hold steady
- capture the full sheet

## Debug Clues

- empty OCR blocks -> inspect crop and preprocess
- fragmented text -> inspect OCR layout and grouping strategy
- 0 drugs but visible text -> inspect NER labels and mapping thresholds
