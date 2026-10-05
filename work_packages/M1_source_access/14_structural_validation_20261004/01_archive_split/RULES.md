# UK parliamentary reply-parent structural validation

## Frozen input and unit

This validator reads the registered UK parliamentary written-answer and written-statement parents in the 06 DuckDB checkpoint and the saved XML ZIP, 1991 Historic Hansard item HTML, Hansard detail JSON, official archive HTML, Questions and Statements API list JSON, and ParlParse mirror XML to which their content versions point. The publication-date frame is 1988-01-01 through 2026-09-21 inclusive. The date of a saved response, its retrieval, a content update, and this report's generation are different times. The run makes no historical body-version claim from a later saved response.

The parent unit is the source reply item: a Historic Hansard answer or statement group, a saved Historic item-page question/reply group, a Hansard detail Overview item, an HTML archive topic reply group, one Questions and Statements API answer/statement item, or a ParlParse question/reply group. Child units are source-addressed question and reply text blocks. A source-declared group of modern question UINs with identical saved answer text is recorded separately as an answer group. Repeated words alone do not prove shared identity.

## Checks and outputs

| Rule | Check | Failure interpretation |
| --- | --- | --- |
| R-UNIT | Stored external ID maps to a parsed saved-original parent group. | An absent group is a boundary conflict; inspect parser and source identity first. |
| R-TEXT-UNIT | In Historic ZIP sections without paragraph IDs, a unique exact question/reply text signature maps a stored hashed parent to one saved group. | Split alignment can be supported while independent reproduction of the hashed ID remains unavailable; ambiguous signatures remain insufficient. |
| R-DATE | Original item's publication date equals the stored date. | A disagreement is a boundary conflict, with no automatic date repair. |
| R-LOCATOR / R-ROLE | Every stored child source locator exists in that original and has the same question/reply role. | Missing or crossed locators are boundary conflicts; a missing locator field is insufficient evidence. |
| R-BOUNDARY | Response nodes belong to the stated parent group. | A reply assigned to a different source group is a boundary conflict. |
| R-SPAN | Normalized saved child text aligns with the addressable source node; short truncation, added leakage and gross mismatch are flagged. | Material differences are boundary conflicts; ambiguous differences remain insufficient. |
| R-MAPPING / R-ORDER | Linked child content version agrees with the parent and question/reply order is preserved within each role. | Version mismatch is a boundary conflict; order uncertainty remains insufficient. |
| R-OMISSION | Every parsed reply block of a mapped parent is present among its children. Historic ZIPs also inventory candidate groups in approved department/date sections with no parent linked to that ZIP. | Parent missing reply is a boundary conflict; unmatched historic groups require prior exclusion/overlap checks before repair. |
| R-DUPLICATE / R-PARENT-LINK | A saved reply node should not be owned by two different parent IDs in the same version; a parent should not have conflicting container/version links. | Flagged for review; no automatic merge or deletion. |
| R-JOINT | Explicit modern `groupedQuestions` UIN links plus identical saved answer text support a legitimate shared-answer group. | Different or missing text is left as an answer-group review state, without failing an otherwise valid parent split. |
| R-ORIGINAL / R-VERSION | A missing/unparseable saved original limits validation; multiple normalized metadata versions are noted separately. | No inferred repair or historical equivalence. |

`parent_results.csv` gives one row per parent-version linkage and its named checks. `container_results.csv` gives the linked saved-file inventory and an omission count where the historic source scope supports it. `answer_groups.csv` records explicit modern answer groups. `exceptions.csv` is an evidence locator and minimum-action queue; an exception is a check result, not a deletion command. `execution_coverage.csv` and `INPUT_MANIFEST.json` record the checkpoint and read scope. The parser and six falsification fixtures are executable locally with the repository virtual environment.

## Evidential boundaries

Historic omission candidates are limited to keyed groups in approved department sections of saved volumes linked to registered parents; they are not proof that every candidate must be inserted. Unkeyed groups cannot be counted as exact-ID omissions. Historic item HTML, archive HTML and ParlParse pages are checked for mapped parents; unselected or other mirror groups are not counted as omissions. Hansard detail JSON is checked only for the mapped item. Modern list pages are checked only for selected mapped items. Cross-source title/date mirror candidates from the earlier distribution audit are identity leads, not automatic duplicates. Content verification does not establish the truth of a speaker's claim. No climate, emotion, harm or fear labels are computed here.
