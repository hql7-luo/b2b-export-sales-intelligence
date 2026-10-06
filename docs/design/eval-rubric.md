# Evaluation Rubric

Pass threshold: 7.0 / 10. Stability and business correctness take precedence.

## Functionality (40%)

- P0 customer, scoring, quotation, and dashboard paths work end to end.
- P1 rule/AI inquiry analysis and follow-up core workflows work.
- P2 remains small but functional.
- Invalid input and empty data do not crash the app.

## Business correctness (30%)

- Lead scoring is transparent and totals 100 points.
- Gross Margin and Markup formulas are distinct, labeled, and tested.
- EXW/FOB/CIF/DDP cost inclusion is visible and calculations round half up.
- All records and contacts are clearly fictional.

## Maintainability and safety (20%)

- UI does not contain SQL or pricing/scoring logic.
- SQL is parameterized, uploads are validated, API keys use environment variables.
- Modules have focused responsibilities and helpful Chinese comments.

## Visual craft (10%)

- Professional export-operations identity with restrained color and typography.
- Tables, metrics, forms, empty states, and charts remain readable on common widths.
- No animation or decoration interferes with the core workflows.
