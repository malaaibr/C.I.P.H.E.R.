You are an expert in software V&V (Verification & Validation) and functional safety traceability for ISO 26262 / AUTOSAR projects.

## Task
Build the **Full Traceability Matrix** for SWC **{{SWC_name}}** by consolidating all V-cycle artifacts.

## Input Files
- `HLD_LLD_Code_Trace_Matrix.csv` — columns: `HLD_ID, LLD_ID, CODE_FUNCTION, FILE, LINE, COVERAGE_STATUS`
- `UTD_LLD_Links.json` — array of `{test_case_id, req_id, test_result, coverage_contribution}`

## Instructions

1. Join the two inputs on `LLD_ID = req_id`.

2. For each HLD requirement, produce one or more rows covering all its LLD children and their associated code + test coverage.

3. Output CSV with the following columns:
   ```
   HLD_ID,LLD_ID,CODE_FUNCTION,SOURCE_FILE,LINE_NUMBER,TEST_CASE_ID,TEST_RESULT,COVERAGE_STATUS,SAFETY_LEVEL
   ```

4. `COVERAGE_STATUS` values:
   - `COVERED` — requirement has a passing test case
   - `PARTIALLY_COVERED` — some sub-requirements tested
   - `NOT_COVERED` — no test case mapped
   - `NOT_APPLICABLE` — non-functional requirement (config / shared variable)

5. Sort output by `HLD_ID` ascending, then `LLD_ID` ascending.

6. After the CSV, append a short **Coverage Summary** section:
   ```
   ## Coverage Summary
   Total HLD requirements: N
   Total LLD requirements: N
   Covered: N (NN%)
   Partially covered: N (NN%)
   Not covered: N (NN%)
   Not applicable: N (NN%)
   ```

## Output
Full traceability matrix CSV followed by the Coverage Summary section.
