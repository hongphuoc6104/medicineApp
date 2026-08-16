# Current Experiment Scope

The active milestone is ten-class entity extraction from ML Kit OCR regions.

Included: OCR contract, token/span classification, character-noise robustness,
training data validation, strict entity metrics, API inference, and Android review.

Deferred: parent assignment, relations, layout graph models, drug normalization,
medication plans, authentication, persistence, and server-side OCR.

The legacy dataset supports DRUG only. A model must not be described as ten-class
until every class is represented in versioned train, validation, and test manifests.
