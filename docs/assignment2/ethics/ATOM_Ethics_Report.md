# Project ATOM: Ethical Review

ENGR90037 | Assignment 2 | Ethics

Yifan Wu | Student ID: 1618332

## 1. Project and significance

Project ATOM (Autonomous Transport & Object Manipulation) aims to develop a robot system that moves test tubes between laboratory workstations and operates a representative instrument fixture. Its potential value is reducing repetitive handling while making transfers more consistent. The proposed proof of concept uses non-hazardous surrogate tubes in a controlled university workcell; human-movement scenarios are simulation only [1]. Current evidence includes simulated visual approach and physical gripper bench measurements, rather than a demonstrated integrated autonomous laboratory workflow [2–4]. Benefits remain conditional on reliable handling and appropriate human oversight.

## 2. Three stakeholder groups at scale

Laboratory technicians could gain relief from repetitive work but lose tasks, influence or employment. Researchers and laboratory owners could gain capacity but bear equipment and sample losses. Nearby laboratory users, including maintenance and cleaning staff, could face collision or spill risks without directly sharing productivity gains.

## 3. Purpose

ATOM should support laboratory workers through dependable, accountable assistance with routine tube handling. Its purpose is to improve working conditions and research reliability while preserving meaningful human control, distributing benefits fairly and avoiding preventable harm to people and the environment.

## 4. Three values and three principles

Values identify what matters; principles guide decisions about action. I apply the lecture’s principles to ATOM’s foreseeable effects [6].

Honesty matters because users depend on engineering claims: I must distinguish magnetic readings from calibrated force and simulation from physical validation. Care matters because broken tubes, unintended motion and spills can harm people who did not choose the experiment. Accountability matters because responsibility must remain identifiable when software, operators and hardware interact; test records and explicit approval boundaries support this.

Non-maleficence requires avoiding preventable harm: uncertain grasp or localisation feedback should prevent progression to a more hazardous task. Beneficence requires pursuing demonstrable benefit: assess worker exposure and transfer reliability alongside speed, rather than treating automation itself as success. Justice requires a fair distribution of benefits and burdens: consult technicians and nearby staff, provide training and consider who bears maintenance work or job disruption.

These principles can conflict. Faster operation may benefit researchers while increasing risk to others. I would retain conservative operating limits until evidence supports a change, and involve affected staff in that decision. Our duty of care persists beyond meeting specifications: productivity alone cannot justify avoidable harm [6].

## 5. Goals, means and ends

Following the lecture’s ethical-design approach, goals must be just, means acceptable, and foreseeable ends examined [6]. Goals are a repeatable, supervised tube-transfer workflow with verified completion and controlled failure responses. Ends include intended benefits, such as less repetitive exposure and trustworthy experiments, and unintended effects, such as job disruption and overreliance. Successful movement alone does not establish better working conditions: fewer handling steps could be offset by troubleshooting or spills.

Means are the methods used to achieve those goals. I support staged simulation and bench testing, non-hazardous surrogates, measured calibration and a deterministic manipulation baseline before more complex autonomy. The existing controller blocks force commands while calibration is incomplete [3]. This is ethically justified restraint: magnetic-field changes occurred during a recorded empty-gripper sequence, so a sensor signal alone cannot establish safe contact force [2].

Before integrated hardware trials, the team should validate grasp retention, coordinate calibration, collision controls and the hardware emergency-stop boundary. Communication loss and power loss need separate assessment: halting movement may still leave a tube at risk of falling. A browser stop is not a hardware emergency stop, and simulation cannot establish safe operation around people [1,4]. Unresolved controls should keep testing at the supervised subsystem level, even if this delays the demonstration.

For scale-up, I would seek technicians’ and nearby users’ input on operating zones, recovery procedures and task allocation, with training and an accessible way to report concerns. Brey’s anticipatory approach supports examining both the artefact and its application context [7]. Repairable modules and equipment reuse may reduce waste, but environmental benefit must be checked against energy use and failed consumables. These means make the goals and ends ethically defensible only if evidence supports proportionate risk and affected people have a meaningful voice.

## 6. Two relevant professional-code tenets

Consult Australia’s tenet 7 requires statements and evidence to be fair, honest and based on adequate knowledge, as discussed in the lectures [6]. For ATOM, I must disclose uncalibrated force sensing, preserve unsuccessful tests and acknowledge inherited work and AI assistance. Reporting a successful simulation as a validated physical transfer could induce unsafe reliance.

Engineers Australia’s tenet 4.2 addresses community and environmental health, safety and wellbeing [5,6]. This requires considering technicians, nearby staff and waste alongside research productivity. I would apply it through reviewed test boundaries, demonstrated stopping and sample-retention behaviour, staff consultation and maintainable hardware. Together, these tenets connect truthful evidence with responsibility for deployment’s consequences; neither a promising demonstration nor deadline pressure establishes ethical acceptability.

## AI use declaration

ChatGPT/Codex was used to assist with developing, drafting and revising the report and presentation.

## References

[1] Wu, Y. and Zhang, X. (2026). Project Charter: Towards a Robotic and AI-Enabled Autonomous Chemical Laboratory. Version 0.2, 27 August. Internal planning draft, University of Melbourne. File: uni documents/Project_Charter.docx.

[2] Project ATOM (2026a). Empty-gripper closure and return dataset, 7 October. Primary platform CSVs and controller records: docs/data/gripper/20261007/empty_closure_20261007/. Test conditions and interpretation: docs/GRIPPER_EMPTY_CLOSURE_20261007.md. University of Melbourne, internal project records.

[3] Project ATOM (2026b). GripperController and UncalibratedForceModel. Source inspected 14 October 2026. Files: ros2_ws/src/atom_gripper_hardware/atom_gripper_hardware/controller.py and calibration.py. University of Melbourne, project source code.

[4] Project ATOM (2026c). Current system architecture, 30 September; and simulation-to-hardware log. Files: docs/SYSTEM_ARCHITECTURE.md and docs/SIM2REAL_LOG.md. Internal records inspected 14 October 2026.

[5] Engineers Australia (2022). Code of Ethics and Guidelines on Professional Conduct. Section 4.2. https://www.engineersaustralia.org.au/sites/default/files/2022-08/code-ethics-guidelines-professional-conduct-2022.pdf (accessed 14 October 2026).

[6] Howard, M. (2026). Professional Practice Ethics: Final lecture and Q&A. ENGR90037, Semester 2, University of Melbourne. Slides 8, 21, 25, 34–35 and 38–41, including speaker notes. File: uni documents/slides/Final PPE Lecture [2026 S2 MH].pptx. See also Professional Practice Ethics, Lecture 4, pp. 14 and 26–31, file: uni documents/slides/Final EE-4 [2026 S2].pdf. Consult Australia tenet 7 is cited as reproduced in the lecture.

[7] Brey, P.A.E. (2012). Anticipating ethical issues in emerging IT. Ethics and Information Technology, 14, 305–317, especially section 4. https://doi.org/10.1007/s10676-012-9293-y. Course-provided copy: uni documents/slides/Brey2012_Article_AnticipatingEthicalIssuesInEme.pdf.
