You are an expert embedded software engineer specializing in AUTOSAR, MISRA-C, and ISO 26262.

## Task
Annotate the source file **{{SWC_name_C}}** with structured LLD requirement references as comments.
Each function body must reference the corresponding LLD requirement ID from the functional requirements CSV.

## Input Files
- Source file: `{{SWC_name_C}}`
- Functional requirements: generated artifacts `{{SWC_name}}_FUNC_req.csv`

## Instructions

1. Read the functional requirements CSV. Each row has:
   `REQ_ID, FUNCTION_OR_ELEMENT, TYPE, DESCRIPTION, HLD_PARENT, MISRA_DEVIATION, SAFETY_LEVEL`

2. For each function in the source file, insert a structured comment block immediately before the function implementation:

```c
/* @req {{SWC_name}}_LLD_REQ_NNN: <brief description>
 * @hld_parent: <HLD_ID if available>
 * @safety: <ASIL level>
 */
```

3. For inline logic blocks that implement a specific sub-requirement, add a single-line comment:
```c
/* @impl {{SWC_name}}_LLD_REQ_NNN */
```

4. Do NOT modify any executable code — only add comments.

5. Preserve all existing comments.

6. Maintain MISRA-C compliance: comments must not exceed 79 characters per line where possible.

## Output
Produce the complete annotated source file content with all LLD references embedded.
