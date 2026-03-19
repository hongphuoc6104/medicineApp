# Skill: Vietnam Drug Database

## Main Source

- primary: `data/drug_db_vn_full.json`
- legacy fallback: `data/drug_db_vn.csv`

## Practical Notes

- search should consider both trade names and active ingredients
- mobile search results should stay understandable for non-expert users
- low-score fuzzy matches should not be presented as certainty

## When Updating Logic

- explain whether the change affects recall or precision
- call out if old benchmark assumptions may change
