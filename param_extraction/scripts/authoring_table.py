# Copyright (c) 2026 Contributors to the RISCV UnifiedDB <https://github.com/riscv/riscv-unified-db>
# SPDX-License-Identifier: BSD-3-Clause-Clear
"""
Every non-mechanical decision needed to express our 38 parameters in James
Ball's ``param-defs-schema.json`` format, held in one reviewable table.

Kept out of the generator deliberately, following the convention set in
``scripts/``: judgement lives in a table that a reviewer can argue
with line by line, never buried in code.

Two things are decided here and nowhere else:

``long_name``
    Written by us. Neither James' list (86 of 93 are the placeholder
    ``NAME-TBD``) nor UDB itself (166 of 223 are literally ``TODO``) has real
    ones, so there was nothing to copy.

``shape``
    How the parameter's domain is expressed in his schema, which offers only
    ``type`` (a scalar token or an enum list), ``range`` ([lo, hi]) and
    ``array`` (*fixed* inclusive index bounds).

    ``shape`` is a dict passed through to the YAML almost verbatim:
      {"type": "boolean"}                     -> a yes/no choice
      {"type": [...]}                         -> an enum of legal values
      {"range": [lo, hi]}                     -> an integer range
      {"type": "boolean", "array": [lo, hi]}  -> a per-bit / per-index mask

    ``approx`` marks a shape that does not faithfully capture the spec
    sentence, with the reason. His schema has no way to say "a variable-length
    subset of a set", which is what several of our WARL findings actually are,
    so those are modelled as a fixed-length per-element boolean mask. That is
    testable and close, but it is our reading, not his schema's intent.
    Every ``approx`` entry needs a human ruling before these ship.

``note`` is the mentor's own condition where he recorded one. His exporter
appends it to the description as ``NOTE: ...``, so it survives into the UDB
YAML rather than being lost at the format boundary.
"""

from __future__ import annotations

# Mirrors James' one-file-per-chapter convention so the two sets can be
# compared, and eventually merged, file by file.
CHAPTER_FILES = {
    "counters.adoc": ("counters.yaml", "Counters"),
    "hypervisor.adoc": ("hypervisor.yaml", "H Extension"),
    "indirect-csr.adoc": ("indirect-csr.yaml", "Indirect CSR"),
    "machine.adoc": ("machine.yaml", "Machine Mode"),
    "rnmi.adoc": ("rnmi.yaml", "Smrnmi Extension"),
    "scalar-crypto.adoc": ("scalar-crypto.yaml", "Scalar Crypto"),
    "smctr.adoc": ("smctr.yaml", "SmCtr (Ctrl Xfer Records)"),
    "smstateen.adoc": ("smstateen.yaml", "State Enable Extension"),
    "supervisor.adoc": ("supervisor.yaml", "Supervisor Mode"),
    "zalasr.adoc": ("zalasr.yaml", "Zalasr Extension"),
    "zicsr.adoc": ("zicsr.yaml", "Zicsr Extension"),
}

# MXLEN-wide per-bit masks. 64 is the widest legal MXLEN, so a 64-entry mask
# is the safe fixed length his schema forces us to commit to.
_MXLEN_MASK = {"type": "boolean", "array": [0, 63]}

AUTHORING = {
    # ---------------------------------------------------------- counters --
    "HPM_UNIMPLEMENTED_ACCESS_BEHAVIOR": dict(
        long_name="Behavior when an unimplemented HPM counter is read",
        # Deliberately reuses James' exact value set from HPM_READ_BEHAVIOR,
        # which resolves to the same impl-def. Inventing a different spelling
        # of the same three options would manufacture a merge conflict.
        shape={"type": ["AlwaysValue", "AlwaysIllegalInstExc", "Other"]},
    ),
    "HPM_MISCONFIGURED_BEHAVIOR": dict(
        long_name="Misconfigured HPM event returns a constant value",
        shape={"type": "boolean"},
        note="Only observable when Ssstrict is implemented; otherwise unspecified.",
    ),
    # -------------------------------------------------------- hypervisor --
    "HTVAL_LEGAL_VALUES": dict(
        long_name="Guest physical addresses `htval` is able to hold",
        shape=_MXLEN_MASK,
        approx="The spec says `htval` may hold an arbitrary subset of "
               "2-bit-shifted guest physical addresses. A per-bit implemented "
               "mask is the closest his schema allows and is testable, but a "
               "subset of addresses is not strictly a bit mask.",
    ),
    "MTVAL2_LEGAL_VALUES": dict(
        long_name="Guest physical addresses `mtval2` is able to hold",
        shape=_MXLEN_MASK,
        approx="Same approximation as HTVAL_LEGAL_VALUES; identical spec wording.",
    ),
    "VSSTATUS_UBE_PARAM": dict(
        long_name="`vsstatus`.UBE is a read-only copy of another endianness bit",
        shape={"type": "boolean"},
    ),
    "VSXL_RO_PARAM": dict(
        long_name="`hstatus`.VSXL is read-only",
        shape={"type": "boolean"},
    ),
    "VTW_VIRTINSTR_PARAM": dict(
        long_name="WFI always raises a virtual-instruction exception when `hstatus`.VTW is set",
        shape={"type": "boolean"},
    ),
    "HGATP_PPN_LOWER_BITS_RO": dict(
        long_name="`hgatp`.PPN[1:0] are read-only zero",
        shape={"type": "boolean"},
        note="Applies only to implementations supporting solely the defined "
             "paged virtual-memory schemes and/or Bare.",
    ),
    "HIP_BIT_WRITABLE": dict(
        long_name="Writable bits of `hip`",
        shape=_MXLEN_MASK,
        note="Bit i is a free choice only where the corresponding `sie` bit is "
             "read-only zero.",
    ),
    # ------------------------------------------------------ indirect-csr --
    "SISELECT_WIDTH": dict(
        long_name="Largest value `siselect` supports",
        shape={"range": [4095, 65535]},
        approx="The spec fixes only a lower bound (0..0xFFF must be supported) "
               "and leaves the maximum open. 0xFFFF is our chosen upper bound "
               "because his schema requires a closed range.",
    ),
    "VSISELECT_WIDTH": dict(
        long_name="Largest value `vsiselect` supports",
        shape={"range": [4095, 65535]},
        approx="Same bounded-range approximation as SISELECT_WIDTH.",
    ),
    # ----------------------------------------------------------- machine --
    "HINT_XLEN_REDUCTION_BEHAVIOR": dict(
        long_name="A HINT overwrites destination register bits above XLEN",
        shape={"type": "boolean"},
        note="A HINT may change state not visible to the privilege mode "
             "executing it, so this is a real choice rather than a "
             "contradiction of HINT semantics.",
    ),
    "MENVCFG_FIOM_READONLY": dict(
        long_name="`menvcfg`.FIOM is read-only zero",
        shape={"type": "boolean"},
    ),
    "MIP_WRITABLE_BITS": dict(
        long_name="Writable bits of `mip`",
        shape=_MXLEN_MASK,
        note="Each bit is read-write or read-only zero; read-only one is not legal.",
    ),
    "PMA_IDEMPOTENT_IMPLICIT_READ_SIZE": dict(
        long_name="Size of a naturally aligned idempotent implicit-read region, log2 bytes",
        shape={"range": [0, 12]},
        approx="Held as a log2 exponent, following the Sail `_exp` convention, "
               "because his schema has no power-of-2 type. Upper bound 12 "
               "(4 KiB) is the smallest supported page size the spec caps it at.",
    ),
    "PMPADDR_WARL_MASK": dict(
        long_name="Implemented address bits of `pmpaddr`",
        shape=_MXLEN_MASK,
        note="The implemented bit count is conditional on privilege mode and "
             "on xSATP.mode (virtual versus physical address).",
    ),
    "WFI_TW_ALWAYS_ILLEGAL": dict(
        long_name="WFI always raises an illegal-instruction exception when `mstatus`.TW is set",
        shape={"type": "boolean"},
    ),
    "DELEGATABLE_EXCEPTIONS": dict(
        long_name="Trap causes that may be delegated",
        shape=_MXLEN_MASK,
        note="Each bit is read-write or read-only zero; read-only one is not legal.",
    ),
    "MCYCLE_SHARED": dict(
        long_name="`mcycle` is shared between harts on the same core",
        shape={"type": "boolean"},
        note="Observable as a write to `mcountinhibit`.CY becoming visible to "
             "sibling harts; testing it needs a multi-hart harness.",
    ),
    "XRET_CLEARS_LR_RESERVATION": dict(
        long_name="An `x`RET instruction clears an outstanding LR reservation",
        shape={"type": "boolean"},
        note="Permitted but not required, so an implementation may be "
             "non-deterministic here; tests should not rely on it.",
    ),
    # -------------------------------------------------------------- rnmi --
    "MNEPC_INVALID_ADDRESS_CONVERSION": dict(
        long_name="`mnepc` converts an invalid address before writing",
        shape={"type": "boolean"},
        note="Depends on the definition of an invalid address, and implies "
             "fewer than the full width of address bits are implemented.",
    ),
    # ----------------------------------------------------- scalar-crypto --
    "MSECCFG_SEED_BITS_RW": dict(
        long_name="`mseccfg`.[s,u]seed are read-write",
        shape={"type": "boolean"},
        note="Read-write or read-only zero; read-only one is not legal.",
    ),
    # ------------------------------------------------------------- smctr --
    "CTR_CCE_WIDTH": dict(
        long_name="Exponent bits implemented in `ctrdata`.CCE",
        shape={"range": [0, 4]},
    ),
    "CTR_CYCLE_COUNTING_SUPPORTED": dict(
        long_name="`ctrdata` includes a count of CPU cycles",
        shape={"type": "boolean"},
    ),
    "SCTRDEPTH_SUPPORTED_VALUES": dict(
        long_name="`sctrdepth`.DEPTH encodings supported",
        shape={"type": "boolean", "array": [0, 4]},
        approx="A per-encoding supported mask over DEPTH values 0..4 "
               "(16/32/64/128/256 entries). The spec states a subset is "
               "supported; his schema cannot express a variable-length subset. "
               "Note James models the *configured* value as range [0,4], which "
               "is the adjacent but different question.",
    ),
    "CTRTARGET_MISP_IMPLEMENTED": dict(
        long_name="`ctrtarget`.MISP is implemented",
        shape={"type": "boolean"},
        note="When unimplemented the bit is read-only zero; when implemented "
             "it is a read-only copy of an internal mispredict state bit.",
    ),
    "CTR_CTRDATA_TYPE_IMPLEMENTED": dict(
        long_name="`ctrdata` optional fields are implemented",
        shape={"type": "boolean"},
        note="The register itself must be implemented; every field within it "
             "is optional and read-only zero when unimplemented.",
    ),
    # --------------------------------------------------------- smstateen --
    "MSTATEEN_BIT63_TYPE": dict(
        long_name="`mstateen` bit 63 (SE0) is read-only zero",
        shape={"type": "boolean"},
        note="Permitted only when the hypervisor extension is not implemented "
             "and the matching `sstateen` CSR is all read-only zeros.",
    ),
    "STATEEN_IMPLICIT_UPDATE_EXCEPTION": dict(
        long_name="An implicit state update raises an exception when disabled by `stateen`",
        shape={"type": "boolean"},
        note="Whether a trap is taken; which kind of trap is defined elsewhere.",
    ),
    # -------------------------------------------------------- supervisor --
    "HINT_SXLEN_DEST_REG_BEHAVIOR": dict(
        long_name="A HINT overwrites destination register bits above SXLEN",
        shape={"type": "boolean"},
    ),
    "SEPC_INVALID_ADDR_BEHAVIOR": dict(
        long_name="`sepc` converts an invalid address before writing",
        shape={"type": "boolean"},
        note="Software-write and hardware-write behaviour may differ for this "
             "multi-bit address field.",
    ),
    "SSTATUS_UXL_ACCESS": dict(
        long_name="`sstatus`.UXL is read-only",
        shape={"type": "boolean"},
    ),
    "SSTATUS_UBE_ACCESS": dict(
        long_name="`sstatus`.UBE is read-only",
        shape={"type": "boolean"},
    ),
    "SENVCFG_FIOM_ACCESS": dict(
        long_name="`senvcfg`.FIOM is read-only zero",
        shape={"type": "boolean"},
        note="Conditional on privilege mode.",
    ),
    "SIP_BITS_ACCESS": dict(
        long_name="Writable bits of `sip`",
        shape=_MXLEN_MASK,
        note="Each bit is read-write or read-only; read-only zero and "
             "read-only one are both seen.",
    ),
    "STANDARD_INTERRUPT_SUPPORT": dict(
        long_name="Standard supervisor interrupts implemented",
        shape=_MXLEN_MASK,
        approx="Modelled as a per-interrupt-cause mask. James instead splits "
               "this into four named booleans (SEI/STI/SSI/LCOFI), which is "
               "the same information at a different granularity. Worth "
               "settling on one before merging.",
    ),
    # ------------------------------------------------------------ zalasr --
    "ZALASR_MISALIGNED_ATOMICITY_GRANULE": dict(
        long_name="Zalasr relaxes the misaligned atomicity granule requirement",
        shape={"type": "boolean"},
        note="Overlaps UDB's existing MISALIGNED_MAX_ATOMICITY_GRANULE_SIZE; "
             "flagged for a ruling in cross_list/out/list_comparison.adoc.",
    ),
    # ------------------------------------------------------------- zicsr --
    "CSR_STRONGLY_ORDERED": dict(
        long_name="CSRs whose accesses are strongly ordered",
        shape={"type": "boolean", "array": [0, 4095]},
        approx="A per-CSR-address boolean over the full 12-bit CSR address "
               "space. The spec says a platform may designate certain CSRs; "
               "his schema cannot express a variable-length subset. 4096 "
               "entries is faithful but verbose.",
    ),
}
