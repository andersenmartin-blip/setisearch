# LS7W public-source follow-up — 19 September 2026

Operational continuation after the public IASW assessment. This is a source-
resolution checkpoint, not a target-image experiment and not a reconstruction
of the earlier local LS7W artifact set.

## Question

Can the exact CHEOPS onboard `gcoadd` operator or the remaining reference-
selection rules be established from currently accessible public sources strongly
enough to freeze the native-image study without contacting the mission team?

## Sources checked

1. University of Vienna CHEOPS project page:
   https://space.univie.ac.at/en/projects/cheops/
   It states that the CHEOPS IFSW was developed as open-source software and
   links the public CHEOPS-IASW repository.

2. Public CHEOPS-IASW repository:
   https://gitlab.phaidra.org/ottensr5/cheops
   The public project is identified as CHEOPS Instrument Application Software.
   Indexed public-branch content is visible, but the present execution
   environment could not retrieve a complete repository archive or perform a
   repository-wide code search.

3. CHEOPS Data Products Definition Document, issue 1.16:
   https://www.cosmos.esa.int/documents/1416855/12897414/CHEOPS-UGE-SOC-DD-002-i1.16_data_products_definition_document.pdf/c0980d2d-595b-b0bd-6413-c569501eb242?t=1687517012308
   It distinguishes `coadd`, `mean`, `gmean`, `gcoadd` and `none`,
   marks `gmean` and `gcoadd` as imagette modes, and delegates their exact
   definitions to RD-11, `CHEOPS-UVIE-INST-TN-001`, issue 2.0.

4. CHEOPS mission technical paper:
   https://doi.org/10.1007/s10686-020-09679-4
   Section 7.2 states that ordinary stacked window images and margins are
   co-added pixel-by-pixel, while nominal short-exposure imagettes are cropped
   before the window stack and retained at full cadence.

5. ESA OBDP 2019 CHEOPS presentation / conference record:
   https://indico.esa.int/event/225/contributions/4306/
   The public presentation places stacking as the first lossy stage of the
   configurable data-processing chain and explicitly lists
   `NONE, COADD, MEAN, GCOADD, GMEAN`. The conference record states that the
   complete CHEOPS IFSW sources are available under GPL2.

6. Bounded public-web searches for the exact technical-note identifier
   `CHEOPS-UVIE-INST-TN-001`, its title `On-Board Data Processing Steps`,
   `gcoadd`, the exact dark-map filename and the exact flat-field filename.
   These searches returned the DPD references above but not RD-11 itself, an
   indexed `gcoadd` implementation, or native validity-header contents for
   the required reference files.

## Result

**PUBLIC_SOURCE_RESOLUTION_INCOMPLETE.**

The public evidence now establishes:

- provenance of the onboard operator family;
- distinct `gcoadd` and ordinary `coadd` modes;
- ordinary window `coadd` at high level as pixel-by-pixel coaddition;
- that the authoritative numeric stacking definitions exist in RD-11;
- that the complete CHEOPS IFSW source is intended to be public.

It still does **not** establish, for the retained visit's
`NEXP=2, STACKING=gcoadd` imagettes:

- exact normalization or grouping;
- weighting;
- clipping or saturation behavior;
- arithmetic type and overflow behavior;
- ordering relative to any onboard preprocessing relevant to these pixels;
- a flight-relevant source revision for the March 2020 observation.

The same bounded search did not establish the native `V_STRT_U/V_STOP_U`
contents or the version-specific selection/interpolation rule for the required
dark/bad maps, nor deliver the exact flat/LUT contents.

## Decision

The public-source route has produced a concrete repository and narrowed the
questions, but it has not closed the physical input contract. Do not infer
`gcoadd` from its name and do not open target-image ranges.

The next justified action is the already prepared, narrowly scoped technical
clarification request in `CHEOPS_CALIBRATION_REQUEST.md`. It remains
**unsent** because person-directed contact has not been authorized in this
workflow.

If exact RD-11 material, a flight-relevant IASW source path/revision, or the
required reference files are supplied through a supported channel, verify them
against `CHEOPS_REQUIRED_INPUTS.json`, then freeze one integrated calibration,
uncertainty, pulse-preservation, nuisance and native-prediction study before
evaluating source images.
