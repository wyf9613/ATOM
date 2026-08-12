# CAD Inventory

## Received archive

`hardware/end effector/End Effector Assembly V3.f3z`

- Format: Fusion 360 distributed design archive (ZIP container).
- Size: 3,242,872 bytes.
- SHA-256: `9E27B636EE18203D0501DDA5FDDBF83745068A4C52F6580EE69B1A690C6E5581`
- Manifest root: `c20df9ed-acc4-470e-bb55-90ebb96c8449.f3d`.

## Components declared by the archive

| Friendly name | Archive member | Role |
|---|---|---|
| End Effector Assembly V3 | `c20df9ed-acc4-470e-bb55-90ebb96c8449.f3d` | Root assembly |
| STS3215 Sub Assembly | `f0795558-8f67-4bee-9ddc-19ff2827dc19.f3d` | Referenced servo subassembly |
| PDL-RS-MTR-STS3215 FeeTech STS3215 ASM | `92ca7797-e0d8-4603-8317-6ad3d94966b9.f3d` | Servo model |
| STS3215 Servo Mount | `a72196c6-7a60-4a88-b460-35e568c067eb.f3d` | Servo mount |
| Case Opened | `c32a4a06-e177-4b62-b025-11ab20e7abce.f3d` | Referenced case part |

The F3Z contains its declared XRef members. This confirms archive structure, not geometric correctness or manufacturability.

## Before mesh export

- Open the archive in Fusion 360 and verify that every XRef resolves.
- Confirm document units and measure the reported 225 x 105 x 131 mm envelope.
- Identify grounded component, joint types, joint axes, limits and finger symmetry.
- Identify the flange/mount datum, gripper base frame and TCP datum.
- Record materials/masses and compare CAD mass properties with the reported 580 g.
- Export visual and simplified collision geometry separately.
- Preserve this archive unchanged; export derived files under the future gripper-description package.

## Missing CAD items

- Neutral STEP export for tool-independent review.
- Per-part manufacturing exports and revision identifiers.
- Dimensioned drawing for the arm interface and quick-disconnect.
- Explicit assembly joint-limit documentation.
- Verified material assignments and centre-of-mass report.

