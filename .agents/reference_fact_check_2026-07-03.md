# Reference Fact Check 2026-07-03

Scope: imported the project writing/fact-checking norms, then audited `article/*.md` references and high-risk prose around recent spintronics/RC citations. This is an internal audit trail; deliverable manuscript files should remain free of local paths and workflow notes.

## Automated Link Check

- Extracted DOI/arXiv links from `article/*.md`: 57 links, 54 unique before edits.
- Reran the link checker with network approval after sandbox socket denial.
- Interpreted publisher `403 Forbidden` and certificate-chain failures as access policy, not evidence of bibliographic error; treated HTTP 404 / no public hit / title-author mismatch as actionable.

## Corrections Applied

- `article/chapter04.md` `[^smtj_arm_compact]`: old DOI `10.1109/SMACD52803.2021.9636229` returned 404 and the stored authors did not match the verifiable arXiv record. Corrected to García-Redondo, Prabhat, Bhargava, Dray, *A Compact Model for Scalable MTJ Simulation*, arXiv:2106.04976. Also narrowed the prose to the verified claims: Python/Verilog-A compact model, OOMMF validation, and 1 Mb 28 nm MRAM macro benchmark.
- `article/chapter04.md` `[^sutton_pbit]`: old Science Advances entry / DOI `10.1126/sciadv.abb2823` returned 404. Corrected to the verifiable arXiv record: Sutton et al., *Autonomous Probabilistic Coprocessing with Petaflips per Second*, arXiv:1907.09664.
- `article/chapter05.md` `[^tunable_rtn]`: old `Physical Review Applied` citation and DOI `10.1103/tbm9-6938` could not be verified. Corrected to arXiv:2509.13458 and narrowed prose to stable pMTJs actuated by nanosecond pulses producing tunable RTN, not a demonstrated low-barrier sMTJ/RC dual-mode array.
- `article/chapter05.md` `[^vcma_macro]`: no public web hit for the cited 2026 VLSI macro title; removed citation and dependent prose rather than carrying an unverifiable reference.
- `article/appendix_D_circuit_comparison.md`: removed local audit-file paths from manuscript prose; retained only publishable evidence language.

## Checked And Retained

- `[^pbit_asic]` DOI `10.1038/s41928-025-01439-6` resolves to Nature Electronics volume 8, pages 784-793 (2025), with 130 nm CMOS ASIC and voltage-controlled MTJ entropy-source claims matching the manuscript usage.
- `[^ens_rc]` arXiv:2601.21807 resolves to *Ensemble Reservoir Computing for Physical Systems* (submitted 2026-01-29), and supports the low/mid-resolution readout and ensemble/noise framing used in chapter 5.
- `[^smtj_pbit_driver]` DOI resolved via script to IEEE Xplore; arXiv:2604.14446 independently matches the CMOS-integrated 130 nm sMTJ p-bit claim used in chapter 4.

## Follow-Up Candidates

- A future full bibliography pass should add DOI/arXiv verification to non-DOI entries such as IEDM/ISSCC conference papers where publisher pages are accessible.
- If the removed 2026 VCMA-MTJ macro becomes publicly indexed, re-add it only with a stable DOI, IEEE/VLSI page, or arXiv link and with claims limited to the indexed abstract/full text.
