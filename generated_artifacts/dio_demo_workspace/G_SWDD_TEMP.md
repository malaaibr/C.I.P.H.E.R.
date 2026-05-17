# Generic Software Detailed Design Document (G_SWDD_TEMP)

> Generic SWDD scaffold used by the CIPHER DevNex S1N1 (LLD generation) node.
> S1N1 fills each section below with module-specific content extracted from the
> provided `.c`, `.h`, HLD, linker script, and map file.

## 1. Module Overview

Single paragraph identifying the SWC name, AUTOSAR module class (MCAL / BSW /
SWC), governing SWS document, ASIL claim, and a one-sentence statement of
module purpose. S1N1 fills this from the HLD frontmatter and CAR reference.

## 2. Functional Decomposition

One paragraph per public API listing: API name, service ID, synchronicity,
re-entrancy, primary inputs, primary outputs, DET errors raised, and which HLD
requirement the API implements. S1N1 fills this by walking every `extern`
prototype in `<SWC>.h`.

## 3. Data Dictionary

One paragraph enumerating every typedef, enum, macro, and static / global
variable found in the source files. For each item record: name, kind, base
type, size in bytes (if known from map file), and the scope. S1N1 fills this
by extracting `typedef`, `enum`, `#define`, and file-scope variable
declarations from `<SWC>.c` and `<SWC>.h`.

## 4. Interface Specification

One paragraph describing the upper-edge interface (callers, RTE port, BSW
client) and the lower-edge interface (target peripheral, register block, or
stubbed shadow). For the demo this records the in-memory shadow register
array as the lower edge. S1N1 fills this by cross-referencing the HLD section
2 (Architectural Context) with the `static` arrays declared in `<SWC>.c`.

## 5. Memory Layout

One paragraph mapping every static and global symbol to a linker section,
section base address, and section length, derived from the `.map` file and
verified against the `.ld` script's MEMORY / SECTIONS blocks. S1N1 fills this
by parsing `firmware.map` and resolving each symbol to a region in
`stm32h7xx_flash.ld`.

---

End of generic SWDD template.
