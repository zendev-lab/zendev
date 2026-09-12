# Finding calibration

These are reasoning examples, not mandatory checks or reusable accusations.

## A change creates a reachable regression

A list endpoint changes from filtering visible records and then taking 20 to taking
20 and then filtering. Its contract promises up to 20 visible records when available.
If the first 20 records are hidden but the next 20 are visible, the endpoint now
returns an empty page. Verify the actual query ordering and whether the consumer
continues pagination before reporting it. The repair belongs where the visible
result limit is enforced; adding a second cache does not restore the contract.

A useful finding names the changed query location, the mixed-visibility input,
the incomplete result, and the documented limit semantics. "Pagination might be
wrong" does not provide enough evidence.

## Context disproves a suspected bug

An internal helper indexes `items[0]`. The only caller rejects empty input before
calling it, and the helper is not public. An empty-list crash is not reachable
through the supported entry point. Do not request another guard just because the
helper looks unsafe in isolation. If a newly added caller skips validation, that
new path changes the conclusion.

## Complexity needs a concrete cost

A new mutable `active_count` duplicates a collection's length. Removal updates the
collection but misses the counter, and admission uses the counter. Report the stale
capacity decision and the missing update path; consider deriving the count from the
collection. A wrapper that centralizes a real authorization invariant is not the
same problem, even if it currently has only one implementation.

## Missing evidence is a limitation

A patch calls an unavailable package's `commit()` method, and rollback semantics
cannot be established from the supplied diff. Identify the needed API contract or
implementation. Do not assert data loss, invent a test result, or give an unqualified
clean bill of health. Report confirmed findings elsewhere and the uncovered boundary.

## Separate severity and certainty

A fully reproduced typo in an optional diagnostic may be P3. A statically established
cross-tenant read may be P1 or P0 depending on reachability and scope. Certainty alone
does not make a small issue critical. Tests are not required to demonstrate every
static defect, and a plausible security story is not proof of exploitability.
