# Sail RISC-V config to riscv-unified-db parameter mapping

Sources:
- Sail config enumerated from `sail-riscv/build/config/rv64d_v64_e64.json` (same schema/fields as `sail-riscv/config/config.json.in`, with CMake substitutions applied).
- UDB parameters enumerated from `riscv-unified-db/spec/std/isa/param/*.yaml`.

Conventions:
- Sail `extensions.*.supported` toggles are accepted as mappings to UDB extension selection and are excluded from the parameter table/unmapped Sail list.
- “Partial” means the concepts overlap but are not one-to-one (for example global vs per-region, one Sail knob vs several UDB knobs, or different enum value spaces).
- “Transform needed” means the units differ (for example Sail stores log2 values where UDB stores byte/bit counts).

Summary:
- Sail config leaf settings found: **220**
- Accepted Sail extension-selection leaves excluded from this parameter mapping: **100**
- Sail non-extension leaf settings considered below: **120**
- Sail non-extension settings with at least one UDB parameter mapping: **73**
- Sail non-extension settings with no UDB parameter mapping: **47**
- UDB parameters found: **228**
- UDB parameters mapped from at least one Sail setting: **84**
- UDB parameters with no Sail config option: **144**

## Mapping table

| Sail config setting | UDB parameter(s) | Notes |
|---|---|---|
| `base.xlen` | `MXLEN` | Sail has one global XLEN; UDB also has per-mode XLEN params with no separate Sail option. |
| `base.E` | **None** | Base-E support is an ISA/extension choice, not a UDB parameter; this UDB tree has no E.yaml extension file. |
| `base.writable_misa` | `MISA_CSR_IMPLEMENTED`, `MUTABLE_MISA_A`, `MUTABLE_MISA_B`, `MUTABLE_MISA_C`, `MUTABLE_MISA_D`, `MUTABLE_MISA_F`, `MUTABLE_MISA_H`, `MUTABLE_MISA_M`, `MUTABLE_MISA_Q`, `MUTABLE_MISA_S`, `MUTABLE_MISA_U`, `MUTABLE_MISA_V` | Partial/coarse mapping: Sail has one writable_misa switch; UDB separates misa existence and mutability per misa bit. |
| `base.writable_fiom` | **None** | No UDB parameter for senvcfg/menvcfg FIOM writability. |
| `base.writable_hpm_counters` | `HPM_COUNTER_EN` | Bit vector maps to enabled HPM counters. |
| `base.scounteren_writable_bits` | `SCOUNTENABLE_EN` | Bit vector maps to writable/delegatable scounteren bits. |
| `base.mcounteren_writable_bits` | `MCOUNTENABLE_EN` | Bit vector maps to writable/delegatable mcounteren bits. |
| `base.mtvec.direct.supported` | `MTVEC_MODES` | Direct support means mode 0 is present in MTVEC_MODES. |
| `base.mtvec.direct.base_alignment` | `MTVEC_BASE_ALIGNMENT_DIRECT` | Same quantity, log2 byte alignment. |
| `base.mtvec.vectored.supported` | `MTVEC_MODES` | Vectored support means mode 1 is present in MTVEC_MODES. |
| `base.mtvec.vectored.base_alignment` | `MTVEC_BASE_ALIGNMENT_VECTORED` | Same quantity, log2 byte alignment. |
| `base.stvec.direct.supported` | `STVEC_MODE_DIRECT` | Boolean support for stvec direct mode. |
| `base.stvec.vectored.supported` | `STVEC_MODE_VECTORED` | Boolean support for stvec vectored mode. |
| `base.stvec.vectored.base_alignment` | **None** | No UDB STVEC base-alignment parameter; UDB only has STVEC mode support booleans. |
| `base.medeleg.delegatable_bits` | **None** | No UDB parameter for the delegatable medeleg bit mask. |
| `base.mideleg.delegatable_bits` | **None** | No UDB parameter for the delegatable mideleg bit mask. |
| `base.xtval_nonzero.illegal_instruction` | `REPORT_ENCODING_IN_MTVAL_ON_ILLEGAL_INSTRUCTION`, `REPORT_ENCODING_IN_STVAL_ON_ILLEGAL_INSTRUCTION` | Sail has one xtval knob; UDB splits mtval/stval/vstval and by exception. |
| `base.xtval_nonzero.software_breakpoint` | `REPORT_VA_IN_MTVAL_ON_BREAKPOINT`, `REPORT_VA_IN_STVAL_ON_BREAKPOINT` | Sail distinguishes software/hardware breakpoint; UDB has breakpoint reporting params. |
| `base.xtval_nonzero.hardware_breakpoint` | `REPORT_VA_IN_MTVAL_ON_BREAKPOINT`, `REPORT_VA_IN_STVAL_ON_BREAKPOINT` | Sail distinguishes software/hardware breakpoint; UDB has breakpoint reporting params. |
| `base.xtval_nonzero.load_address_misaligned` | `REPORT_VA_IN_MTVAL_ON_LOAD_MISALIGNED`, `REPORT_VA_IN_STVAL_ON_LOAD_MISALIGNED` | Sail has one xtval knob; UDB splits by target tval CSR. |
| `base.xtval_nonzero.load_access_fault` | `REPORT_VA_IN_MTVAL_ON_LOAD_ACCESS_FAULT`, `REPORT_VA_IN_STVAL_ON_LOAD_ACCESS_FAULT` | Sail has one xtval knob; UDB splits by target tval CSR. |
| `base.xtval_nonzero.load_page_fault` | `REPORT_VA_IN_MTVAL_ON_LOAD_PAGE_FAULT`, `REPORT_VA_IN_STVAL_ON_LOAD_PAGE_FAULT` | Sail has one xtval knob; UDB splits by target tval CSR. |
| `base.xtval_nonzero.samo_address_misaligned` | `REPORT_VA_IN_MTVAL_ON_STORE_AMO_MISALIGNED`, `REPORT_VA_IN_STVAL_ON_STORE_AMO_MISALIGNED` | Sail groups store/AMO; UDB uses STORE_AMO names. |
| `base.xtval_nonzero.samo_access_fault` | `REPORT_VA_IN_MTVAL_ON_STORE_AMO_ACCESS_FAULT`, `REPORT_VA_IN_STVAL_ON_STORE_AMO_ACCESS_FAULT` | Sail groups store/AMO; UDB uses STORE_AMO names. |
| `base.xtval_nonzero.samo_page_fault` | `REPORT_VA_IN_MTVAL_ON_STORE_AMO_PAGE_FAULT`, `REPORT_VA_IN_STVAL_ON_STORE_AMO_PAGE_FAULT` | Sail groups store/AMO; UDB uses STORE_AMO names. |
| `base.xtval_nonzero.fetch_address_misaligned` | `REPORT_VA_IN_MTVAL_ON_INSTRUCTION_MISALIGNED`, `REPORT_VA_IN_STVAL_ON_INSTRUCTION_MISALIGNED` | Fetch corresponds to instruction tval reporting. |
| `base.xtval_nonzero.fetch_access_fault` | `REPORT_VA_IN_MTVAL_ON_INSTRUCTION_ACCESS_FAULT`, `REPORT_VA_IN_STVAL_ON_INSTRUCTION_ACCESS_FAULT` | Fetch corresponds to instruction tval reporting. |
| `base.xtval_nonzero.fetch_page_fault` | `REPORT_VA_IN_MTVAL_ON_INSTRUCTION_PAGE_FAULT`, `REPORT_VA_IN_STVAL_ON_INSTRUCTION_PAGE_FAULT` | Fetch corresponds to instruction tval reporting. |
| `base.xtval_nonzero.software_check` | `REPORT_CAUSE_IN_MTVAL_ON_LANDING_PAD_SOFTWARE_CHECK`, `REPORT_CAUSE_IN_MTVAL_ON_SHADOW_STACK_SOFTWARE_CHECK`, `REPORT_CAUSE_IN_STVAL_ON_LANDING_PAD_SOFTWARE_CHECK`, `REPORT_CAUSE_IN_STVAL_ON_SHADOW_STACK_SOFTWARE_CHECK` | Partial: Sail has one SoftwareCheck knob; UDB splits landing-pad vs shadow-stack and mtval/stval/vstval. |
| `base.xtval_nonzero.reserved_exceptions` | **None** | No direct UDB parameter for nonzero tval behavior on reserved exception codes. |
| `base.reserved_behavior.amocas_odd_register` | **None** | No UDB parameter for AMOCAS odd-register reserved behavior. |
| `base.reserved_behavior.fcsr_rm` | **None** | No UDB parameter for reserved dynamic fcsr.FRM behavior. |
| `base.reserved_behavior.pmpcfg_write_only` | `TRAP_ON_ILLEGAL_WLRL` | Very partial: UDB has a generic illegal-WLRL write trap knob, not this PMP-specific clear/fatal policy. |
| `base.reserved_behavior.xenvcfg_cbie` | **None** | No exact UDB parameter for reserved xenvcfg.CBIE=0b10 behavior; FORCE_UPGRADE_CBO_INVAL_TO_FLUSH is related but controls CBIE=0b11. |
| `base.reserved_behavior.xtvec_mode` | `MTVEC_ILLEGAL_WRITE_BEHAVIOR` | Partial: Sail applies to xtvec modes generally; UDB has mtvec illegal-write behavior only. |
| `base.reserved_behavior.rv32zdinx_odd_register` | **None** | No UDB parameter for RV32Zdinx odd-register reserved behavior. |
| `base.mstatus.fs_legal_states` | `MSTATUS_FS_LEGAL_VALUES` | Legal FS states. |
| `base.mstatus.vs_legal_states` | `MSTATUS_VS_LEGAL_VALUES` | Legal VS states. |
| `base.privileged_isa_version` | **None** | UDB stores spec/manual versions as metadata, not a UDB parameter in spec/std/isa/param. |
| `memory.physaddr_bits` | `PHYS_ADDR_WIDTH` | Same quantity. |
| `memory.pmp.grain` | `PMP_GRANULARITY` | Transform needed: Sail PMP grain is privileged-architecture G; UDB PMP_GRANULARITY is G+2 (log2 smallest region). |
| `memory.pmp.count` | `NUM_PMP_ENTRIES` | Same quantity. |
| `memory.pmp.usable_count` | `NUM_USABLE_PMP_ENTRIES` | Same quantity. |
| `memory.pmp.tor_supported` | `PMP_TOR_SUPPORTED` | Same quantity. |
| `memory.pmp.na4_supported` | `PMP_NA4_SUPPORTED` | Same quantity. |
| `memory.pmp.napot_supported` | `PMP_NAPOT_SUPPORTED` | Same quantity. |
| `memory.misaligned.exceptions.load_store` | `MISALIGNED_LDST`, `MISALIGNED_LDST_EXCEPTION_PRIORITY` | Partial: Sail selects none/access-fault/misaligned-exception before translation; UDB has support boolean and priority. |
| `memory.misaligned.exceptions.vector` | `VECTOR_LS_MISALIGNED_LEGAL` | Partial: Sail selects vector misaligned exception behavior; UDB has legal/supported boolean. |
| `memory.misaligned.exceptions.amo` | `MISALIGNED_AMO` | Partial: Sail selects exception behavior; UDB has support boolean. |
| `memory.misaligned.exceptions.lrsc` | `LRSC_MISALIGNED_BEHAVIOR` | Same conceptual behavior for misaligned LR/SC. |
| `memory.misaligned.order_decreasing` | `MISALIGNED_SPLIT_STRATEGY` | Partial: UDB only distinguishes sequential-bytes vs custom, not increasing vs decreasing maximum-size chunks. |
| `memory.misaligned.default_allowed_within_exp` | `MISALIGNED_MAX_ATOMICITY_GRANULE_SIZE` | Transform needed: Sail is log2 bytes; UDB is byte size. |
| `memory.misaligned.byte_by_byte` | `MISALIGNED_SPLIT_STRATEGY` | Partial: UDB sequential_bytes matches byte-by-byte increasing only; other Sail split choices become custom. |
| `memory.dtb_address` | **None** | Platform/device-tree placement, no UDB architectural parameter. |
| `memory.regions[].base` | **None** | Memory map/PMA region list; UDB has no equivalent param set for regions. |
| `memory.regions[].size` | **None** | Memory map/PMA region list; UDB has no equivalent param set for regions. |
| `memory.regions[].attributes.mem_type` | **None** | PMA region attribute; no UDB parameter. |
| `memory.regions[].attributes.cacheable` | **None** | PMA region attribute; no UDB parameter. |
| `memory.regions[].attributes.coherent` | **None** | PMA region attribute; no UDB parameter. |
| `memory.regions[].attributes.executable` | **None** | PMA region attribute; no UDB parameter. |
| `memory.regions[].attributes.readable` | **None** | PMA region attribute; no UDB parameter. |
| `memory.regions[].attributes.writable` | **None** | PMA region attribute; no UDB parameter. |
| `memory.regions[].attributes.read_idempotent` | **None** | PMA region attribute; no UDB parameter. |
| `memory.regions[].attributes.write_idempotent` | **None** | PMA region attribute; no UDB parameter. |
| `memory.regions[].attributes.misaligned_exceptions.load_store` | `MISALIGNED_LDST`, `MISALIGNED_LDST_EXCEPTION_PRIORITY` | Partial: per-region PMA override vs UDB global hart parameter. |
| `memory.regions[].attributes.misaligned_exceptions.vector` | `VECTOR_LS_MISALIGNED_LEGAL` | Partial: per-region PMA override vs UDB global vector misalignment parameter. |
| `memory.regions[].attributes.misaligned_exceptions.amo` | `MISALIGNED_AMO` | Partial: per-region PMA override vs UDB global AMO misalignment parameter. |
| `memory.regions[].attributes.atomic_support` | `MISALIGNED_AMO` | Partial: Sail models per-region AMO capability; UDB has global misaligned-atomic support. |
| `memory.regions[].attributes.misaligned_atomicity_granule_size_exp` | `MISALIGNED_MAX_ATOMICITY_GRANULE_SIZE` | Transform needed and partial: Sail is per-region log2 MAG; UDB is global byte size. |
| `memory.regions[].attributes.vector_misaligned_atomicity_granule_size_exp` | **None** | No UDB parameter for vector-specific per-region MAG size. |
| `memory.regions[].attributes.reservability` | `LRSC_RESERVATION_STRATEGY` | Partial: Sail PMA controls whether a region is reservable; UDB describes LR/SC reservation strategy globally. |
| `memory.regions[].attributes.supports_cbo_zero` | **None** | No UDB parameter for per-region cbo.zero PMA support. |
| `memory.regions[].attributes.supports_pte_read` | **None** | No UDB parameter for per-region implicit PTE-read PMA support. |
| `memory.regions[].attributes.supports_pte_write` | **None** | No UDB parameter for per-region implicit PTE-write PMA support. |
| `memory.regions[].include_in_device_tree` | **None** | Device-tree generation/platform metadata, no UDB parameter. |
| `platform.vendorid` | `VENDOR_ID_BANK`, `VENDOR_ID_OFFSET` | Transform needed: Sail stores the full mvendorid value; UDB splits JEDEC bank and offset. |
| `platform.archid` | `ARCH_ID_VALUE` | Same CSR value. |
| `platform.impid` | `IMP_ID_VALUE` | Same CSR value. |
| `platform.hartid` | **None** | No UDB parameter for mhartid value. |
| `platform.cache_block_size_exp` | `CACHE_BLOCK_SIZE` | Transform needed: Sail is log2 bytes; UDB is byte size. |
| `platform.reservation.reservation_set_size_exp` | `LRSC_RESERVATION_STRATEGY` | Partial: exact mapping only for the UDB enumerated 64-byte/128-byte/exact/custom strategies. |
| `platform.reservation.require_exact_reservation_addr` | `LRSC_FAIL_ON_NON_EXACT_LRSC` | Same concept for SC success/fail on non-exact address. |
| `platform.reservation.invalidate_on_same_hart_store` | **None** | No UDB parameter for same-hart store invalidating a reservation. |
| `platform.clint.supported` | **None** | Platform device model, no UDB architectural parameter. |
| `platform.clint.base` | **None** | Platform device address, no UDB architectural parameter. |
| `platform.clint.size` | **None** | Platform device size, no UDB architectural parameter. |
| `platform.simple_interrupt_generator.supported` | **None** | Sail test device, no UDB architectural parameter. |
| `platform.simple_interrupt_generator.base` | **None** | Sail test device address, no UDB architectural parameter. |
| `platform.clock_frequency` | **None** | Timing/platform parameter, no UDB architectural parameter. |
| `platform.instructions_per_tick` | **None** | Emulator timing parameter, no UDB architectural parameter. |
| `platform.wfi_is_nop` | **None** | No UDB WFI-is-NOP parameter. |
| `platform.wfi_available_to_user_mode` | **None** | No UDB parameter for U-mode WFI availability. |
| `platform.max_time_to_wait` | **None** | Emulator wait timeout, no UDB architectural parameter. |
| `extensions.F.fflags_dirty_policy` | `HW_MSTATUS_FS_DIRTY_UPDATE` | Partial: Sail policy is about setting FS/SD from fflags; UDB describes hardware FS Dirty updates. |
| `extensions.V.support_level` | **None** | Maps to UDB extension selection (V/Zve*), not to a UDB parameter. |
| `extensions.V.vlen_exp` | `VLEN` | Transform needed: Sail is log2 bits; UDB is bits. |
| `extensions.V.elen_exp` | `ELEN` | Transform needed: Sail is log2 bits; UDB is bits. |
| `extensions.V.reserved_behavior.illegal_vtype` | `VILL_SET_ON_RESERVED_VTYPE` | Partial: UDB boolean covers set-vill behavior for reserved vtype; Sail also allows illegal/fatal. |
| `extensions.V.reserved_behavior.vstart_out_of_bounds` | `LEGAL_VSTART` | Partial: Sail controls out-of-bounds vstart behavior; UDB enumerates legal vstart implementation limits. |
| `extensions.V.vl_use_ceil` | `RVV_VL_WHEN_AVL_LT_DOUBLE_VLMAX` | Same choice class for AVL < 2*VLMAX. |
| `extensions.V.max_index_eew_exp` | `VECTOR_LS_INDEX_MAX_EEW` | Transform needed: Sail is log2 EEW; UDB enum is EEW bits/XLEN. |
| `extensions.V.vstart.zero_required.arith` | `LEGAL_VSTART` | Partial: Sail per-instruction-class zero-required policy vs UDB global legal-vstart strategy. |
| `extensions.V.vstart.zero_required.scalar_move` | `LEGAL_VSTART` | Partial: Sail per-instruction-class zero-required policy vs UDB global legal-vstart strategy. |
| `extensions.Zawrs.nto.is_nop` | `ZAWRS_NTO_IS_NOP` | Same concept for WRS.NTO. |
| `extensions.Zawrs.sto.is_nop` | **None** | No UDB parameter for WRS.STO is-NOP behavior. |
| `extensions.Zkr.sseed_reset_value` | **None** | No UDB parameter for seed CSR reset value. |
| `extensions.Zkr.useed_reset_value` | **None** | No UDB parameter for seed CSR reset value. |
| `extensions.Zkr.sseed_read_only_zero` | **None** | No UDB parameter for seed CSR read-only-zero behavior. |
| `extensions.Zkr.useed_read_only_zero` | **None** | No UDB parameter for seed CSR read-only-zero behavior. |
| `extensions.Ssnpm.supported_pmlen_7` | `PMLEN` | Partial: Sail lists supported PMLEN values; UDB PMLEN is a configured integer. |
| `extensions.Ssnpm.supported_pmlen_16` | `PMLEN` | Partial: Sail lists supported PMLEN values; UDB PMLEN is a configured integer. |
| `extensions.Smnpm.supported_pmlen_7` | `PMLEN` | Partial: Sail lists supported PMLEN values; UDB PMLEN is a configured integer. |
| `extensions.Smnpm.supported_pmlen_16` | `PMLEN` | Partial: Sail lists supported PMLEN values; UDB PMLEN is a configured integer. |
| `extensions.Smmpm.supported_pmlen_7` | `PMLEN` | Partial: Sail lists supported PMLEN values; UDB PMLEN is a configured integer. |
| `extensions.Smmpm.supported_pmlen_16` | `PMLEN` | Partial: Sail lists supported PMLEN values; UDB PMLEN is a configured integer. |
| `extensions.Svbare.sfence_vma_illegal_if_svbare_only` | `TRAP_ON_SFENCE_VMA_WHEN_SATP_MODE_IS_READ_ONLY` | Same concept for trapping sfence.vma when satp mode is read-only Bare/Svbare-only. |
| `extensions.Stateen.C_readonly_zero` | **None** | No direct UDB parameter for Stateen C bit read-only-zero policy. |
| `extensions.Stateen.SE0_readonly_zero` | **None** | No direct UDB parameter for Stateen SE0 bit read-only-zero policy. |
| `extensions.Ssqosid.rcid_length` | `RCID_WIDTH` | Same quantity, width/length of RCID. |
| `extensions.Ssqosid.mcid_length` | `MCID_WIDTH` | Same quantity, width/length of MCID. |

## Sail options with no corresponding UDB parameter

- `base.E` — Base-E support is an ISA/extension choice, not a UDB parameter; this UDB tree has no E.yaml extension file.
- `base.writable_fiom` — No UDB parameter for senvcfg/menvcfg FIOM writability.
- `base.stvec.vectored.base_alignment` — No UDB STVEC base-alignment parameter; UDB only has STVEC mode support booleans.
- `base.medeleg.delegatable_bits` — No UDB parameter for the delegatable medeleg bit mask.
- `base.mideleg.delegatable_bits` — No UDB parameter for the delegatable mideleg bit mask.
- `base.xtval_nonzero.reserved_exceptions` — No direct UDB parameter for nonzero tval behavior on reserved exception codes.
- `base.reserved_behavior.amocas_odd_register` — No UDB parameter for AMOCAS odd-register reserved behavior.
- `base.reserved_behavior.fcsr_rm` — No UDB parameter for reserved dynamic fcsr.FRM behavior.
- `base.reserved_behavior.xenvcfg_cbie` — No exact UDB parameter for reserved xenvcfg.CBIE=0b10 behavior; FORCE_UPGRADE_CBO_INVAL_TO_FLUSH is related but controls CBIE=0b11.
- `base.reserved_behavior.rv32zdinx_odd_register` — No UDB parameter for RV32Zdinx odd-register reserved behavior.
- `base.privileged_isa_version` — UDB stores spec/manual versions as metadata, not a UDB parameter in spec/std/isa/param.
- `memory.dtb_address` — Platform/device-tree placement, no UDB architectural parameter.
- `memory.regions[].base` — Memory map/PMA region list; UDB has no equivalent param set for regions.
- `memory.regions[].size` — Memory map/PMA region list; UDB has no equivalent param set for regions.
- `memory.regions[].attributes.mem_type` — PMA region attribute; no UDB parameter.
- `memory.regions[].attributes.cacheable` — PMA region attribute; no UDB parameter.
- `memory.regions[].attributes.coherent` — PMA region attribute; no UDB parameter.
- `memory.regions[].attributes.executable` — PMA region attribute; no UDB parameter.
- `memory.regions[].attributes.readable` — PMA region attribute; no UDB parameter.
- `memory.regions[].attributes.writable` — PMA region attribute; no UDB parameter.
- `memory.regions[].attributes.read_idempotent` — PMA region attribute; no UDB parameter.
- `memory.regions[].attributes.write_idempotent` — PMA region attribute; no UDB parameter.
- `memory.regions[].attributes.vector_misaligned_atomicity_granule_size_exp` — No UDB parameter for vector-specific per-region MAG size.
- `memory.regions[].attributes.supports_cbo_zero` — No UDB parameter for per-region cbo.zero PMA support.
- `memory.regions[].attributes.supports_pte_read` — No UDB parameter for per-region implicit PTE-read PMA support.
- `memory.regions[].attributes.supports_pte_write` — No UDB parameter for per-region implicit PTE-write PMA support.
- `memory.regions[].include_in_device_tree` — Device-tree generation/platform metadata, no UDB parameter.
- `platform.hartid` — No UDB parameter for mhartid value.
- `platform.reservation.invalidate_on_same_hart_store` — No UDB parameter for same-hart store invalidating a reservation.
- `platform.clint.supported` — Platform device model, no UDB architectural parameter.
- `platform.clint.base` — Platform device address, no UDB architectural parameter.
- `platform.clint.size` — Platform device size, no UDB architectural parameter.
- `platform.simple_interrupt_generator.supported` — Sail test device, no UDB architectural parameter.
- `platform.simple_interrupt_generator.base` — Sail test device address, no UDB architectural parameter.
- `platform.clock_frequency` — Timing/platform parameter, no UDB architectural parameter.
- `platform.instructions_per_tick` — Emulator timing parameter, no UDB architectural parameter.
- `platform.wfi_is_nop` — No UDB WFI-is-NOP parameter.
- `platform.wfi_available_to_user_mode` — No UDB parameter for U-mode WFI availability.
- `platform.max_time_to_wait` — Emulator wait timeout, no UDB architectural parameter.
- `extensions.V.support_level` — Maps to UDB extension selection (V/Zve*), not to a UDB parameter.
- `extensions.Zawrs.sto.is_nop` — No UDB parameter for WRS.STO is-NOP behavior.
- `extensions.Zkr.sseed_reset_value` — No UDB parameter for seed CSR reset value.
- `extensions.Zkr.useed_reset_value` — No UDB parameter for seed CSR reset value.
- `extensions.Zkr.sseed_read_only_zero` — No UDB parameter for seed CSR read-only-zero behavior.
- `extensions.Zkr.useed_read_only_zero` — No UDB parameter for seed CSR read-only-zero behavior.
- `extensions.Stateen.C_readonly_zero` — No direct UDB parameter for Stateen C bit read-only-zero policy.
- `extensions.Stateen.SE0_readonly_zero` — No direct UDB parameter for Stateen SE0 bit read-only-zero policy.

## UDB parameters with no Sail config option

- `ASID_WIDTH` — Number of implemented ASID bits. Maximum is 16 for XLEN==64, and 9 for XLEN==32
- `CONFIG_PTR_ADDRESS` — The value returned from `mconfigptr`
- `COUNTINHIBIT_EN` — Indicates which hardware performance monitor counters can be disabled from `mcountinhibit`.
- `DBG_HCONTEXT_WIDTH` — Specifies the size of HCONTEXT
- `DBG_SCONTEXT_WIDTH` — Specifies the size of SCONTEXT
- `DCSR_MPRVEN_TYPE` — Implementation of dcsr.MPRVEN is optional.
- `DCSR_STEPIE_TYPE` — Implementation of dcsr.STEPIE is optional.
- `DCSR_STOPCOUNT_TYPE` — Implementation of dcsr.STOPCOUNT is optional.
- `DCSR_STOPTIME_TYPE` — Implementation of dcsr.STOPTIME is optional.
- `FOLLOW_VTYPE_RESET_RECOMMENDATION` — It is recommended that at reset, vtype.vill is set, the remaining bits in vtype are zero, and vl is set to zero.
- `FORCE_UPGRADE_CBO_INVAL_TO_FLUSH` — When true, an implementation prohibits setting `menvcfg.CBIE` == `11` such that all `cbo.inval`
- `GSTAGE_MODE_BARE` — Whether or not writing mode=Bare is supported in the `hgatp` register.
- `HCONTEXT_AVAILABLE` — Specifies if HCONTEXT is available
- `HCOUNTENABLE_EN` — Indicates which counters can delegated via `hcounteren`
- `HPM_EVENTS` — List of defined event numbers that can be written into mhpmeventN
- `HSTATEEN_AIA_TYPE` — Behavior of the hstateen0.AIA bit:
- `HSTATEEN_CONTEXT_TYPE` — Behavior of the hstateen0.CONTEXT bit:
- `HSTATEEN_CSRIND_TYPE` — Behavior of the hstateen0.CSRIND bit:
- `HSTATEEN_ENVCFG_TYPE` — Behavior of the hstateen0.ENVCFG bit:
- `HSTATEEN_IMSIC_TYPE` — Behavior of the hstateen0.IMSIC bit:
- `HSTATEEN_JVT_TYPE` — Behavior of the hstateen0.JVT bit:
- `HW_MSTATUS_VS_DIRTY_UPDATE` — Indicates whether or not hardware will write to `mstatus.VS`
- `IGNORE_INVALID_VSATP_MODE_WRITES_WHEN_V_EQ_ZERO` — Whether writes from M-mode, U-mode, or S-mode to vsatp with an illegal mode setting are
- `IMPRECISE_VECTOR_TRAP_SETTABLE` — Some profiles may provide a privileged configuration bit that selects
- `JVT_BASE_MASK` — Mask representing the implemented bits of jvt.BASE.
- `JVT_BASE_TYPE` — Type of the jvt.BASE CSR field. One of:
- `JVT_READ_ONLY` — If Zcmt is implemented, JVT is implemented, but can contain a read-only value
- `LRSC_FAIL_ON_VA_SYNONYM` — Whether or not an `sc.l`/`sc.d` will fail if its VA does not match the VA of the prior
- `MARCHID_IMPLEMENTED` — * false: `marchid` is not implemented, and must be read-only-0
- `MCONTEXT_AVAILABLE` — Specifies if MCONTEXT is available
- `MCOUNTINHIBIT_IMPLEMENTED` — Options:
- `MCTRCTL_CORSWAPINH_IMPLEMENTED` — Whether or not mctrctl.CORSWAPINH is implemented.
- `MCTRCTL_CUSTOM_IMPLEMENTED` — Whether or not mctrctl.CUSTOM is implemented.
- `MCTRCTL_DIRCALLINH_IMPLEMENTED` — Whether or not mctrctl.DIRCALLINH is implemented.
- `MCTRCTL_DIRJMPINH_IMPLEMENTED` — Whether or not mctrctl.DIRJMPINH is implemented.
- `MCTRCTL_DIRLJMPINH_IMPLEMENTED` — Whether or not mctrctl.DIRLJMPINH is implemented.
- `MCTRCTL_EXCINH_IMPLEMENTED` — Whether or not mctrctl.EXCINH is implemented.
- `MCTRCTL_INDCALLINH_IMPLEMENTED` — Whether or not mctrctl.INDCALLINH is implemented.
- `MCTRCTL_INDJMPINH_IMPLEMENTED` — Whether or not mctrctl.INDJMPINH is implemented.
- `MCTRCTL_INDLJMPINH_IMPLEMENTED` — Whether or not mctrctl.INDLJMPINH is implemented.
- `MCTRCTL_INTRINH_IMPLEMENTED` — Whether or not mctrctl.INTRINH is implemented.
- `MCTRCTL_MTE_IMPLEMENTED` — Whether or not mctrctl.MTE is implemented.
- `MCTRCTL_NTBREN_IMPLEMENTED` — Whether or not mctrctl.NTBREN is implemented.
- `MCTRCTL_RASEMU_IMPLEMENTED` — Whether or not mctrctl.RASEMU is implemented.
- `MCTRCTL_RETINH_IMPLEMENTED` — Whether or not mctrctl.RETINH is implemented.
- `MCTRCTL_STE_IMPLEMENTED` — Whether or not mctrctl.STE is implemented.
- `MCTRCTL_TKBRINH_IMPLEMENTED` — Whether or not mctrctl.TKBRINH is implemented.
- `MCTRCTL_TRETINH_IMPLEMENTED` — Whether or not mctrctl.TRETINH is implemented.
- `MIMPID_IMPLEMENTED` — * false: `mimpid` is not implemented, and must be read-only-0
- `MSTATEEN_AIA_TYPE` — Behavior of the mstateen0.AIA bit:
- `MSTATEEN_CONTEXT_TYPE` — Behavior of the mstateen0.CONTEXT bit:
- `MSTATEEN_CSRIND_TYPE` — Behavior of the mstateen0.CSRIND bit:
- `MSTATEEN_ENVCFG_TYPE` — Behavior of the mstateen0.ENVCFG bit:
- `MSTATEEN_IMSIC_TYPE` — Behavior of the mstateen0.IMSIC bit:
- `MSTATEEN_JVT_TYPE` — Behavior of the mstateen0.JVT bit:
- `MTVAL_WIDTH` — The number of implemented bits in the `mtval` CSR.
- `MTVEC_ACCESS` — Options:
- `M_MODE_ENDIANNESS` — Options:
- `NUM_EXTERNAL_GUEST_INTERRUPTS` — Number of supported virtualized guest interrupts
- `PMA_GRANULARITY` — Generally, for systems with an MMU, should not be smaller than 12,
- `PRECISE_SYNCHRONOUS_EXCEPTIONS` — If false, any exception not otherwise mandated to precise (e.g., PMP violation)
- `REPORT_CAUSE_IN_VSTVAL_ON_LANDING_PAD_SOFTWARE_CHECK` — When true, `vstval` is written with the shadow stack cause (code=18) when a SoftwareCheck exception is raised into VS-mode due to a landing pad error.
- `REPORT_CAUSE_IN_VSTVAL_ON_SHADOW_STACK_SOFTWARE_CHECK` — When true, `vstval` is written with the shadow stack cause (code=3) when a SoftwareCheck exception is raised into VS-mode due to a shadow stack pop check instruction.
- `REPORT_ENCODING_IN_VSTVAL_ON_ILLEGAL_INSTRUCTION` — When true, `vstval` is written with the encoding of an instruction that causes an
- `REPORT_ENCODING_IN_VSTVAL_ON_VIRTUAL_INSTRUCTION` — When true, `vstval` is written with the encoding of an instruction that causes an
- `REPORT_GPA_IN_HTVAL_ON_GUEST_PAGE_FAULT` — When true, `htval` is written with the Guest Physical Address, shifted right by 2, that
- `REPORT_GPA_IN_TVAL_ON_INSTRUCTION_GUEST_PAGE_FAULT` — Whether or not GPA >> 2 is written into htval/mtval2 when an instruction guest page fault occurs.
- `REPORT_GPA_IN_TVAL_ON_INTERMEDIATE_GUEST_PAGE_FAULT` — Whether or not GPA >> 2 is written into htval/mtval2 when a guest page fault occurs while
- `REPORT_GPA_IN_TVAL_ON_LOAD_GUEST_PAGE_FAULT` — Whether or not GPA >> 2 is written into htval/mtval2 when a load guest page fault occurs.
- `REPORT_GPA_IN_TVAL_ON_STORE_AMO_GUEST_PAGE_FAULT` — Whether or not GPA >> 2 is written into htval/mtval2 when a store/amo guest page fault occurs.
- `REPORT_VA_IN_VSTVAL_ON_BREAKPOINT` — When true, `vstval` is written with the virtual PC of the EBREAK instruction (same information as `mepc`).
- `REPORT_VA_IN_VSTVAL_ON_INSTRUCTION_ACCESS_FAULT` — When true, `vstval` is written with the virtual PC of an instructino when fetch causes an
- `REPORT_VA_IN_VSTVAL_ON_INSTRUCTION_MISALIGNED` — When true, `vstval` is written with the virtual PC when an instruction fetch is misaligned.
- `REPORT_VA_IN_VSTVAL_ON_INSTRUCTION_PAGE_FAULT` — When true, `vstval` is written with the virtual PC of an instructino when fetch causes an
- `REPORT_VA_IN_VSTVAL_ON_LOAD_ACCESS_FAULT` — When true, `vstval` is written with the virtual address of a load when it causes a
- `REPORT_VA_IN_VSTVAL_ON_LOAD_MISALIGNED` — When true, `vstval` is written with the virtual address of a load instruction when the
- `REPORT_VA_IN_VSTVAL_ON_LOAD_PAGE_FAULT` — When true, `vstval` is written with the virtual address of a load when it causes a
- `REPORT_VA_IN_VSTVAL_ON_STORE_AMO_ACCESS_FAULT` — When true, `vstval` is written with the virtual address of a store when it causes a
- `REPORT_VA_IN_VSTVAL_ON_STORE_AMO_MISALIGNED` — When true, `vstval` is written with the virtual address of a store instruction when the
- `REPORT_VA_IN_VSTVAL_ON_STORE_AMO_PAGE_FAULT` — When true, `vstval` is written with the virtual address of a store when it causes a
- `RESERVED_VSET_X0X0_VILL_SET` — When rs1 = x0 and rd = x0, vset instructions act as if the current
- `RESERVED_VSET_X0X0_VLMAX_CHANGE` — When rs1=x0 and rd=x0, the instructions operate as if the current vector length in vl is used as the AVL.
- `SATP_MODE_BARE` — Whether or not satp.MODE == Bare is supported.
- `SEW_MIN` — Implementations must provide fractional LMUL settings that allow the
- `SSTATEEN_JVT_TYPE` — Behavior of the sstateen0.JVT bit:
- `STVAL_WIDTH` — The number of implemented bits in `stval`.
- `SUPPORT_FRACTIONAL_LMUL_BEYOND_REQUIRED` — For a given supported fractional LMUL setting, implementations must
- `SV32X4_TRANSLATION` — Whether or not Sv32x4 translation mode is supported.
- `SV32_VSMODE_TRANSLATION` — Whether or not Sv32 translation is supported in first-stage (VS-stage)
- `SV39X4_TRANSLATION` — Whether or not Sv39x4 translation mode is supported.
- `SV39_VSMODE_TRANSLATION` — Whether or not Sv39 translation is supported in first-stage (VS-stage)
- `SV48X4_TRANSLATION` — Whether or not Sv48x4 translation mode is supported.
- `SV48_VSMODE_TRANSLATION` — Whether or not Sv48 translation is supported in first-stage (VS-stage)
- `SV57X4_TRANSLATION` — Whether or not Sv57x4 translation mode is supported.
- `SV57_VSMODE_TRANSLATION` — Whether or not Sv57 translation is supported in first-stage (VS-stage)
- `SXLEN` — Set of XLENs supported in S-mode. Can be one of:
- `S_MODE_ENDIANNESS` — Endianness of data in S-mode. Can be one of:
- `TIME_CSR_IMPLEMENTED` — Whether or not a real hardware `time` CSR exists. Implementations can either provide a real
- `TINST_VALUE_ON_BREAKPOINT` — Value written into htinst/mtinst on a Breakpoint exception from VU/VS-mode.
- `TINST_VALUE_ON_FINAL_INSTRUCTION_GUEST_PAGE_FAULT` — Value to write into htval/mtval2 when there is a guest page fault on a final translation.
- `TINST_VALUE_ON_FINAL_LOAD_GUEST_PAGE_FAULT` — Value to write into htval/mtval2 when there is a guest page fault on a final translation.
- `TINST_VALUE_ON_FINAL_STORE_AMO_GUEST_PAGE_FAULT` — Value to write into htval/mtval2 when there is a guest page fault on a final translation.
- `TINST_VALUE_ON_INSTRUCTION_ADDRESS_MISALIGNED` — Value written into htinst/mtinst when there is an instruction address misaligned exception.
- `TINST_VALUE_ON_LOAD_ACCESS_FAULT` — Value written into htinst/mtinst on an AccessFault exception from VU/VS-mode.
- `TINST_VALUE_ON_LOAD_ADDRESS_MISALIGNED` — Value written into htinst/mtinst on a VirtualInstruction exception from VU/VS-mode.
- `TINST_VALUE_ON_LOAD_PAGE_FAULT` — Value written into htinst/mtinst on a LoadPageFault exception from VU/VS-mode.
- `TINST_VALUE_ON_MCALL` — Value written into htinst/mtinst on a MCall exception from VU/VS-mode.
- `TINST_VALUE_ON_SCALL` — Value written into htinst/mtinst on a SCall exception from VU/VS-mode.
- `TINST_VALUE_ON_STORE_AMO_ACCESS_FAULT` — Value written into htinst/mtinst on an AccessFault exception from VU/VS-mode.
- `TINST_VALUE_ON_STORE_AMO_ADDRESS_MISALIGNED` — Value written into htinst/mtinst on a VirtualInstruction exception from VU/VS-mode.
- `TINST_VALUE_ON_STORE_AMO_PAGE_FAULT` — Value written into htinst/mtinst on a StoreAmoPageFault exception from VU/VS-mode.
- `TINST_VALUE_ON_UCALL` — Value written into htinst/mtinst on a UCall exception from VU/VS-mode.
- `TINST_VALUE_ON_VIRTUAL_INSTRUCTION` — Value written into htinst/mtinst on a VirtualInstruction exception from VU/VS-mode.
- `TINST_VALUE_ON_VSCALL` — Value written into htinst/mtinst on a VSCall exception from VU/VS-mode.
- `TRAP_ON_EBREAK` — The spec states that implementations may handle EBREAKs transparently
- `TRAP_ON_ECALL_FROM_M` — The spec states that implementations may handle ECALLs transparently
- `TRAP_ON_ECALL_FROM_S` — Whether or not an ECALL-from-S-mode causes a synchronous exception.
- `TRAP_ON_ECALL_FROM_U` — Whether or not an ECALL-from-U-mode causes a synchronous exception.
- `TRAP_ON_ECALL_FROM_VS` — Whether or not an ECALL-from-VS-mode causes a synchronous exception.
- `TRAP_ON_RESERVED_INSTRUCTION` — Options:
- `TRAP_ON_UNIMPLEMENTED_CSR` — Options:
- `TRAP_ON_UNIMPLEMENTED_INSTRUCTION` — Options:
- `UXLEN` — Set of XLENs supported in U-mode. When both 32 and 64 are supported, SXLEN can be changed,
- `U_MODE_ENDIANNESS` — Endianness of data in U-mode. Can be one of:
- `VECTOR_FF_NO_EXCEPTION_TRIM` — Implementations may process fewer than `vl` elements and reduce `vl`
- `VECTOR_FF_SEG_EXCEPTION_PARTIAL_LOAD` — For fault-only-first segment loads, if an exception occurs partway
- `VECTOR_FF_UPDATE_PAST_TRIM` — Fault-only-first (FF) load instructions may update active destination
- `VECTOR_LOAD_PAST_TRAP` — Vector load instructions may overwrite active destination vector register
- `VECTOR_LOAD_SEG_FF_OVERWRITE_ELEMENTS_AFTER_FAULT` — Fault-only-first segment load instructions may overwrite destination
- `VECTOR_LS_SEG_PARTIAL_ACCESS` — If a trap occurs during access to a segment, it is implementation-defined
- `VECTOR_LS_WHOLEREG_MISALIGNED_LEGAL` — Implementations may raise a misaligned address exception for whole-register
- `VFREDUSUM_FINAL_NODE_ELEMENT_BEHAVIOR` — Implementations are permitted to insert an additional additive identity
- `VFREDUSUM_INACTIVE_NODE_ELEMENT_BEHAVIOR` — A reduction node that receives an input derived solely from masked-off
- `VFREDUSUM_NAN` — The reduction tree structure must be deterministic for a given `vtype`
- `VFREDUSUM_NODE_ROUNDING_BEHAVIOR` — Each reduction operator computes an exact sum using an ideal scalar
- `VMID_WIDTH` — Number of bits supported in `hgatp.VMID` (i.e., the supported width of a virtual machine ID).
- `VSSTAGE_MODE_BARE` — Whether or not writing mode=Bare is supported in the `vsatp` register.
- `VSSTATUS_VS_EXISTS` — Some implementations provide a `vsstatus.VS` field even when the `misa.V`
- `VSTVEC_MODE_DIRECT` — Whether or not `vstvec.MODE` supports Direct (0).
- `VSTVEC_MODE_VECTORED` — Whether or not `stvec.MODE` supports Vectored (1).
- `VSXLEN` — Set of XLENs supported in VS-mode. Can be one of:
- `VS_MODE_ENDIANNESS` — Endianness of data in VS-mode. Can be one of:
- `VUXLEN` — Set of XLENs supported in VU-mode. When both 32 and 64 are supported, VUXLEN can be changed
- `VU_MODE_ENDIANNESS` — Endianness of data in VU-mode. Can be one of:

## UDB parameters mapped from Sail options

- `ARCH_ID_VALUE` ← `platform.archid`
- `CACHE_BLOCK_SIZE` ← `platform.cache_block_size_exp`
- `ELEN` ← `extensions.V.elen_exp`
- `HPM_COUNTER_EN` ← `base.writable_hpm_counters`
- `HW_MSTATUS_FS_DIRTY_UPDATE` ← `extensions.F.fflags_dirty_policy`
- `IMP_ID_VALUE` ← `platform.impid`
- `LEGAL_VSTART` ← `extensions.V.reserved_behavior.vstart_out_of_bounds`, `extensions.V.vstart.zero_required.arith`, `extensions.V.vstart.zero_required.scalar_move`
- `LRSC_FAIL_ON_NON_EXACT_LRSC` ← `platform.reservation.require_exact_reservation_addr`
- `LRSC_MISALIGNED_BEHAVIOR` ← `memory.misaligned.exceptions.lrsc`
- `LRSC_RESERVATION_STRATEGY` ← `memory.regions[].attributes.reservability`, `platform.reservation.reservation_set_size_exp`
- `MCID_WIDTH` ← `extensions.Ssqosid.mcid_length`
- `MCOUNTENABLE_EN` ← `base.mcounteren_writable_bits`
- `MISALIGNED_AMO` ← `memory.misaligned.exceptions.amo`, `memory.regions[].attributes.misaligned_exceptions.amo`, `memory.regions[].attributes.atomic_support`
- `MISALIGNED_LDST` ← `memory.misaligned.exceptions.load_store`, `memory.regions[].attributes.misaligned_exceptions.load_store`
- `MISALIGNED_LDST_EXCEPTION_PRIORITY` ← `memory.misaligned.exceptions.load_store`, `memory.regions[].attributes.misaligned_exceptions.load_store`
- `MISALIGNED_MAX_ATOMICITY_GRANULE_SIZE` ← `memory.misaligned.default_allowed_within_exp`, `memory.regions[].attributes.misaligned_atomicity_granule_size_exp`
- `MISALIGNED_SPLIT_STRATEGY` ← `memory.misaligned.order_decreasing`, `memory.misaligned.byte_by_byte`
- `MISA_CSR_IMPLEMENTED` ← `base.writable_misa`
- `MSTATUS_FS_LEGAL_VALUES` ← `base.mstatus.fs_legal_states`
- `MSTATUS_VS_LEGAL_VALUES` ← `base.mstatus.vs_legal_states`
- `MTVEC_BASE_ALIGNMENT_DIRECT` ← `base.mtvec.direct.base_alignment`
- `MTVEC_BASE_ALIGNMENT_VECTORED` ← `base.mtvec.vectored.base_alignment`
- `MTVEC_ILLEGAL_WRITE_BEHAVIOR` ← `base.reserved_behavior.xtvec_mode`
- `MTVEC_MODES` ← `base.mtvec.direct.supported`, `base.mtvec.vectored.supported`
- `MUTABLE_MISA_A` ← `base.writable_misa`
- `MUTABLE_MISA_B` ← `base.writable_misa`
- `MUTABLE_MISA_C` ← `base.writable_misa`
- `MUTABLE_MISA_D` ← `base.writable_misa`
- `MUTABLE_MISA_F` ← `base.writable_misa`
- `MUTABLE_MISA_H` ← `base.writable_misa`
- `MUTABLE_MISA_M` ← `base.writable_misa`
- `MUTABLE_MISA_Q` ← `base.writable_misa`
- `MUTABLE_MISA_S` ← `base.writable_misa`
- `MUTABLE_MISA_U` ← `base.writable_misa`
- `MUTABLE_MISA_V` ← `base.writable_misa`
- `MXLEN` ← `base.xlen`
- `NUM_PMP_ENTRIES` ← `memory.pmp.count`
- `NUM_USABLE_PMP_ENTRIES` ← `memory.pmp.usable_count`
- `PHYS_ADDR_WIDTH` ← `memory.physaddr_bits`
- `PMLEN` ← `extensions.Ssnpm.supported_pmlen_7`, `extensions.Ssnpm.supported_pmlen_16`, `extensions.Smnpm.supported_pmlen_7`, `extensions.Smnpm.supported_pmlen_16`, `extensions.Smmpm.supported_pmlen_7`, `extensions.Smmpm.supported_pmlen_16`
- `PMP_GRANULARITY` ← `memory.pmp.grain`
- `PMP_NA4_SUPPORTED` ← `memory.pmp.na4_supported`
- `PMP_NAPOT_SUPPORTED` ← `memory.pmp.napot_supported`
- `PMP_TOR_SUPPORTED` ← `memory.pmp.tor_supported`
- `RCID_WIDTH` ← `extensions.Ssqosid.rcid_length`
- `REPORT_CAUSE_IN_MTVAL_ON_LANDING_PAD_SOFTWARE_CHECK` ← `base.xtval_nonzero.software_check`
- `REPORT_CAUSE_IN_MTVAL_ON_SHADOW_STACK_SOFTWARE_CHECK` ← `base.xtval_nonzero.software_check`
- `REPORT_CAUSE_IN_STVAL_ON_LANDING_PAD_SOFTWARE_CHECK` ← `base.xtval_nonzero.software_check`
- `REPORT_CAUSE_IN_STVAL_ON_SHADOW_STACK_SOFTWARE_CHECK` ← `base.xtval_nonzero.software_check`
- `REPORT_ENCODING_IN_MTVAL_ON_ILLEGAL_INSTRUCTION` ← `base.xtval_nonzero.illegal_instruction`
- `REPORT_ENCODING_IN_STVAL_ON_ILLEGAL_INSTRUCTION` ← `base.xtval_nonzero.illegal_instruction`
- `REPORT_VA_IN_MTVAL_ON_BREAKPOINT` ← `base.xtval_nonzero.software_breakpoint`, `base.xtval_nonzero.hardware_breakpoint`
- `REPORT_VA_IN_MTVAL_ON_INSTRUCTION_ACCESS_FAULT` ← `base.xtval_nonzero.fetch_access_fault`
- `REPORT_VA_IN_MTVAL_ON_INSTRUCTION_MISALIGNED` ← `base.xtval_nonzero.fetch_address_misaligned`
- `REPORT_VA_IN_MTVAL_ON_INSTRUCTION_PAGE_FAULT` ← `base.xtval_nonzero.fetch_page_fault`
- `REPORT_VA_IN_MTVAL_ON_LOAD_ACCESS_FAULT` ← `base.xtval_nonzero.load_access_fault`
- `REPORT_VA_IN_MTVAL_ON_LOAD_MISALIGNED` ← `base.xtval_nonzero.load_address_misaligned`
- `REPORT_VA_IN_MTVAL_ON_LOAD_PAGE_FAULT` ← `base.xtval_nonzero.load_page_fault`
- `REPORT_VA_IN_MTVAL_ON_STORE_AMO_ACCESS_FAULT` ← `base.xtval_nonzero.samo_access_fault`
- `REPORT_VA_IN_MTVAL_ON_STORE_AMO_MISALIGNED` ← `base.xtval_nonzero.samo_address_misaligned`
- `REPORT_VA_IN_MTVAL_ON_STORE_AMO_PAGE_FAULT` ← `base.xtval_nonzero.samo_page_fault`
- `REPORT_VA_IN_STVAL_ON_BREAKPOINT` ← `base.xtval_nonzero.software_breakpoint`, `base.xtval_nonzero.hardware_breakpoint`
- `REPORT_VA_IN_STVAL_ON_INSTRUCTION_ACCESS_FAULT` ← `base.xtval_nonzero.fetch_access_fault`
- `REPORT_VA_IN_STVAL_ON_INSTRUCTION_MISALIGNED` ← `base.xtval_nonzero.fetch_address_misaligned`
- `REPORT_VA_IN_STVAL_ON_INSTRUCTION_PAGE_FAULT` ← `base.xtval_nonzero.fetch_page_fault`
- `REPORT_VA_IN_STVAL_ON_LOAD_ACCESS_FAULT` ← `base.xtval_nonzero.load_access_fault`
- `REPORT_VA_IN_STVAL_ON_LOAD_MISALIGNED` ← `base.xtval_nonzero.load_address_misaligned`
- `REPORT_VA_IN_STVAL_ON_LOAD_PAGE_FAULT` ← `base.xtval_nonzero.load_page_fault`
- `REPORT_VA_IN_STVAL_ON_STORE_AMO_ACCESS_FAULT` ← `base.xtval_nonzero.samo_access_fault`
- `REPORT_VA_IN_STVAL_ON_STORE_AMO_MISALIGNED` ← `base.xtval_nonzero.samo_address_misaligned`
- `REPORT_VA_IN_STVAL_ON_STORE_AMO_PAGE_FAULT` ← `base.xtval_nonzero.samo_page_fault`
- `RVV_VL_WHEN_AVL_LT_DOUBLE_VLMAX` ← `extensions.V.vl_use_ceil`
- `SCOUNTENABLE_EN` ← `base.scounteren_writable_bits`
- `STVEC_MODE_DIRECT` ← `base.stvec.direct.supported`
- `STVEC_MODE_VECTORED` ← `base.stvec.vectored.supported`
- `TRAP_ON_ILLEGAL_WLRL` ← `base.reserved_behavior.pmpcfg_write_only`
- `TRAP_ON_SFENCE_VMA_WHEN_SATP_MODE_IS_READ_ONLY` ← `extensions.Svbare.sfence_vma_illegal_if_svbare_only`
- `VECTOR_LS_INDEX_MAX_EEW` ← `extensions.V.max_index_eew_exp`
- `VECTOR_LS_MISALIGNED_LEGAL` ← `memory.misaligned.exceptions.vector`, `memory.regions[].attributes.misaligned_exceptions.vector`
- `VENDOR_ID_BANK` ← `platform.vendorid`
- `VENDOR_ID_OFFSET` ← `platform.vendorid`
- `VILL_SET_ON_RESERVED_VTYPE` ← `extensions.V.reserved_behavior.illegal_vtype`
- `VLEN` ← `extensions.V.vlen_exp`
- `ZAWRS_NTO_IS_NOP` ← `extensions.Zawrs.nto.is_nop`
