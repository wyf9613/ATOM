# Evidence and review notes — not for submission

Prepared 14 October 2026 for Yifan Wu, 1618332.

## Claim boundaries

| Claim in the materials | Evidence inspected | Boundary retained |
| --- | --- | --- |
| Intended tube transport and representative instrument workflow | `uni documents/Project_Charter.docx`, v0.2, 27 Aug | Planning draft; not proof of completed or approved capability |
| Non-hazardous surrogates and controlled physical workcell; moving-person scenarios in simulation only | Same Charter, objectives and scope | Describes proposed limits; not a completed hardware safety assessment |
| Simulated visual approach exists; integrated autonomous laboratory workflow not demonstrated | `docs/SYSTEM_ARCHITECTURE.md`; `docs/SIM2REAL_LOG.md`; later gripper bench records | Simulation and bench tests remain separate kinds of evidence; no claimed real tube-transfer success rate |
| Mean magnetic readings changed in a reported empty-gripper sequence | Five raw CSVs under `docs/data/gripper/20261007/empty_closure_20261007/` plus corresponding test log | One sequence; 100 samples per platform; user-reported unloaded condition, not independently measured contact force |
| Force estimate is uncalibrated and force command is blocked | `ros2_ws/src/atom_gripper_hardware/atom_gripper_hardware/calibration.py` and `controller.py` | Source-code behaviour checked; not new hardware validation and not calibrated force control |
| Benefits, task displacement, overreliance and distributional effects at scale | Reasoned scenarios in this ethical review | Prospective possibilities; no staff survey, employment forecast or measured productivity/environmental gain is fabricated |
| Calibration, stopping/retention validation and staff consultation should precede progression | Proposed ethical/design actions | Not described as completed controls, consultation or certification |

## Quantitative figure

The figure is derived directly from the raw platform CSVs. Values use unrounded means internally. `evidence.json` contains precise statistics and SHA-256 hashes of each input.

| Platform | Samples | Bz mean (µT) | Sample SD (µT) | Mean ΔBz from first platform (µT) |
| --- | ---: | ---: | ---: | ---: |
| Baseline | 100 | 7748.786714 | 1.215405 | 0.000000 |
| Close 1 | 100 | 7746.180386 | 1.280313 | −2.606328 |
| Close 2 | 100 | 7744.617051 | 1.095507 | −4.169663 |
| Close 3 | 100 | 7742.710103 | 1.131992 | −6.076611 |
| Return | 100 | 7744.984893 | 1.175659 | −3.801821 |

Nominal sampling platforms were 10 seconds, separated by motion and settling periods; the 500 values are not 500 independent experimental trials. Actual pose, physical jaw opening, current and physical temperature were not independently measured. There was no independent force reference or matched fixed-opening time control. Sample SD is not total uncertainty. No confidence interval or force uncertainty is inferred from these data. The figure shows descriptive platform means, without error bars that could be mistaken for calibrated physical uncertainty. The last platform is a return to the starting target, not proof of identical physical geometry.

## Course and public sources

- **Howard, Final PPE Lecture [2026 S2 MH].pptx:** all 43 slides and available notes were extracted and read. Key sections: slide 8 (purpose, values/goals, means/principles, foreseeable ends); 21 (moral, prudential and legal reasons); 25 (duty of care and principlism); 34 (ethical duty of care is not to be replaced by a legal definition); 35 (positive responsibility); 38–39 (ethical design and unintended effects); 40–41 (codes). Slide 37's embedded graphic was visually inspected.
- **Howard, Final EE-4 [2026 S2].pdf:** 32 pages; pp.14, 26–31 reinforce the principles, positive responsibility, ethical design and codes. The images on pp.27–29 were rendered; p.29 was visually inspected. This report cites the lecturer for the Beard/Longstaff argument, rather than falsely citing the original work as read.
- **Brey (2012), Anticipating ethical issues in emerging IT:** supplied 13-page paper was extracted; section 4 explains technology, artefact and application levels, especially journal pp.309–311. The review adapts that method to ATOM. No prediction is represented as a measured outcome.
- **Engineers Australia (2022), Code of Ethics and Guidelines on Professional Conduct:** official indexed PDF text verified sections 1.2 and 4.2; only 4.2 is selected in the final report. Direct page/PDF fetches returned HTTP 403, so no local full-text PDF download is claimed. The exact section 4.2 is also present in both supplied lectures. Official source: <https://www.engineersaustralia.org.au/sites/default/files/2022-08/code-ethics-guidelines-professional-conduct-2022.pdf>.
- **Consult Australia 7:** cited as reproduced in Howard's final lecture slide 40 and EE-4 p.30. It was selected because the adequacy of evidence is central to the gripper example. No claim is made that a different current edition was independently downloaded.
- **University of Melbourne, Studying with GenAI:** public guidance confirms the need to check assessment-specific permission; it cannot establish the unavailable Faculty/Capstone rules. <https://students.unimelb.edu.au/academic-skills/study-skills/learning-with-genai/studying-with-genai>.

The supplied resource list, `Why be ethical.pdf` and Asaro paper were extracted for discovery/context. The latter two are not cited or represented as the basis of the final analysis. The initial Belmont search was not used in the report: the provided engineering lectures give the relevant principlism directly.

## Outstanding administrative facts

1. Canvas Faculty/Capstone AI policy text is unavailable. The assignment demands disclosure but does not itself establish the permitted level of generation. The declaration accurately describes substantial AI participation and makes no claim of student verification already performed.
2. The brief specifies PowerPoint. HTML is the user's explicit format choice; acceptance of HTML/PDF remains unconfirmed.
3. Calendar dates and oral-session booking are not inferred from week numbers. Use the actual Canvas deadlines and booking options.

No external messages were sent; no course submissions, hardware actions or repository commits were performed.
