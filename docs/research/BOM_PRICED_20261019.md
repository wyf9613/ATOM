# ATOM priced BOM and battery review

Date:2026-10-19. English content used in the reviewed PDF.

BOM and funding proposal

Power integration, mobile arm energy and the school purchasing process

<b>Preferred proposal.</b> Use one BLUETTI Elite 100 V2 AU integrated power station for the original arm AC controller and Pi power supply. Team electrical parts and Pi kit total 602.96 AUD; request 1,099 AUD separately from Chemical Engineering for the station and installation allowance. Procurement approval and compatibility validation remain pending.

1. Procurement scope - five power items and one computer

ID

ITEM / PURPOSE

QTY

BUDGET AUD

01

UF850 tool IO breakout cable. Access tool 24 V/GND. Check supplied accessories first. OEM-compatible quote still needed.

1

80.00<br/>Allowance

02

5 V logic supply. Pololu D24V50F5 candidate for ESP32 VIN and URT-1 logic. [S1]

1

49.95<br/>Retail

03

7.4 V servo supply. CE07271 adjustable XL4015, for controlled prototype evaluation only. [S2]

1

2.40<br/>Retail

04

Distribution/protection kit. Four terminals: 1.28; two fuse holders: 9.90; remaining wire/fuses/board/guard/switching: 50.00. [S3, S4]

1 kit

61.18<br/>Mixed

05

Shared arm/computer power: BLUETTI Elite 100 V2 AU, preferred candidate 999.00; installation/freight allowance 100.00. Integrated battery, BMS, inverter and AC charging. [S5]

1 system

1,099.00<br/>Mixed

06

Onboard computer: Raspberry Pi 5 8GB starter kit CE09799. Included in the team purchase budget. [S7]

1 kit

389.43<br/>Retail

2. Proposed funding allocation

FUNDING ROUTE

PLANNING AMOUNT AUD

Capstone: electrical 213.53 + Pi kit 389.43

602.96

Chemical Engineering request: item 05

1,099.00

Combined estimate, including Pi kit

1,701.96

Headroom under 800 before prior spend / extra mounting

197.04

Prices checked 19 October 2026. Public prices are not formal quotations. IO cable 80.00, remaining protection parts 50.00, electrical freight 20.00 and battery installation/freight 100.00 are explicit allowances. GST on Jaycar/BLUETTI must be confirmed on the university quotation; no additional GST is silently added. Prior spending and the actual remaining $800 balance are unknown.

Shared onboard power proposal

Prioritise an integrated station and retain the original arm and computer power interfaces.

3. Proposed architecture

<b>One station, two AC loads:</b> BLUETTI AC outlet to original UF850 AC control box; separate AC outlet to the Pi kit power supply. Retain original leads and internal equipment wiring. Tracer retains its traction battery/BMS. Compatibility is to be verified during commissioning.

Use the original approved arm power lead. The tool power limit is 1.8 A total, nominal 24 V with 20-30 V range [S9]. Converter output ratings do not increase that input budget. Verify actual servo current, start-up, voltage excursions and converter temperature before deployment.

4. Candidate selection

BLUETTI Elite 100 V2 remains the 999 AUD baseline candidate. BLUETTI and EcoFlow are different brands. The next page compares three DJI models and two EcoFlow models; these are alternatives for one station, not additional purchases. The main funding totals are unchanged.

The integrated route reduces separate component matching and high-current wiring work. Internal battery, BMS, inverter and AC charging are included; no separate charger or DIY battery pack is budgeted. Prices remain subject to formal quote and approval.

5. Sizing and expected duration

UF850 AC input is 100-240 V,47-63 Hz [S10]; BLUETTI lists 230 V,50/60 Hz,1,800 W [S14]. Nominal ranges overlap. Arm typical 240 W / max 1,000 W [S11] are not measured AC-input peaks. Inrush, waveform, power factor, braking-energy handling and protection remain unverified; no paired test or vendor approval exists.

ASSUMED AVERAGE AC LOAD

ILLUSTRATIVE DURATION

300 W

2.73 h

500 W

1.64 h

1,000 W

0.82 h

Target: 2 h. Calculation: 1,024 Wh x 0.80 / combined AC load. The 0.80 conversion/reserve factor is an assumption; the target requires about 410 W or less average arm-plus-computer load. Duration excludes Tracer traction and is not a guarantee. Measure a representative task before confirming capacity.

Funding rationale for the Chemical Engineering team

A shared integrated station supports laptop-free operation and removes the external mains tether while preserving the original arm controller. Request 1,099 AUD for the station plus installation/freight allowance, subject to the purchase checks and commissioning below.

Finished power station alternatives

Six candidates for one shared arm/computer energy system; public AU prices checked 19 October 2026

All candidates below use integrated LFP batteries and AC inverters. Compare continuous battery output, not surge, voltage-reduction boost or mains-bypass figures. Ratings support screening; none has been tested with this arm and computer.

CANDIDATE / SOURCE

UNIT AUD

ENERGY Wh

CONT. AC W

PROJECT ASSESSMENT

BLUETTI Elite 100 V2 AU<br/>[S5 / S14]

999

1,024

1,800

Current BOM baseline. Original arm controller and Pi PSU retain their AC leads.

DJI Power 1000 V2<br/>[S15 / S16]

999

1,024

2,600

Same nominal energy and price as baseline; greater continuous output headroom. Not longer runtime at the same load.

DJI Power 2000<br/>[S17 / S18 / S16]

1,999

2,048

3,000

Double nominal energy. Stronger option if measured power makes the 2 h target marginal; approx 22 kg.

DJI Power 1000 Mini<br/>[S19 / S20]

699

1,008

800

800 W continuous is below the arm published 1000 W maximum before computer load. Not a primary arm candidate.

EcoFlow DELTA 3 Classic<br/>[S6]

1,099

1,024

1,800

Same nominal energy and rated output as baseline; higher public price. Confirm availability.

EcoFlow DELTA 3 Plus<br/>[S21]

1,399

1,024

1,800

Same nominal energy and rated output as Classic. The Plus name does not imply more runtime at the same load.

DJI prices are D1 Store Australia standalone prices including GST. The DJI official source [S16] is used for technical ratings; its solar-bundle price is excluded. DJI specifies 2600 W continuous for Power 1000 V2 under 25 C laboratory conditions. Confirm the exact AU unit, delivery, tax invoice and school PO acceptance on the formal quote. Stock wording was inconsistent; no delivery date is confirmed.

How to choose between the leading candidates

<b>Keep the current cost baseline:</b> BLUETTI at 999 AUD. <b>Seek a same-price DJI quote:</b> Power 1000 V2 at 999 AUD provides more output headroom with the same 1024 Wh nominal energy. Higher W alone does not increase operating duration. <b>Prioritise capacity:</b> Power 2000 at 1999 AUD doubles nominal energy to 2048 Wh, with a higher cost and approximate 22 kg mass [S18].

Two-hour target and funding effect

STATION SIZE / EXAMPLE

ILLUSTRATIVE RESULT

ENERGY FUNDING REQUEST

1,024 Wh / BLUETTI or DJI V2

2 h requires average AC load at or below 409.6 W. At 500 W: 1.64 h.

999 + 100 allowance = 1,099 AUD

2,048 Wh / DJI Power 2000

2 h requires average AC load at or below 819.2 W. At 500 W: 3.28 h.

1,999 + 100 allowance = 2,099 AUD

Both estimates use an assumed 80% conversion/reserve factor and exclude Tracer traction. They are sizing examples, not measured runtimes. The same 100 AUD installation/freight provision is illustrative and must be re-quoted for the selected unit. Team electrical/Pi budget remains 602.96 AUD. Power 1000 Mini is a lower-power reference, not a primary arm candidate.

Battery and electrical safety

Controls to include in the revised activity assessment and operating procedure

<b>LFP does not mean fireproof.</b> All lithium-ion chemistries, including LFP, can experience thermal runaway [S13]. An integrated BMS reduces some fault risks but cannot eliminate fire, physical damage or external wiring faults.

6. Controls before charging or operating

RISK

REQUIRED CONTROL / EVIDENCE

Battery quality and faults

Obtain exact AU model, manual, BMS/temperature protection information, applicable compliance evidence and warranty/recall status. Transport test documents do not replace use approval. Keep the pack unopened and unmodified.

Charging and smoke

Use manufacturer-specified charging equipment. Charge under supervision in the cluster-approved location, on a non-combustible surface with clear ventilation and exits, away from chemicals. No unattended overnight charging assumed. [S12]

AC shock / earthing

University electrical staff must review the portable source earth/PE arrangement, fault protection, inspection and any RCD requirements. A plug-in RCD is not assumed effective on an unverified inverter arrangement. No student-made neutral-earth links.

DC wiring / converter heat

Set 7.4 V before connecting the servo. Select fuses, wire and connectors from actual current and fault conditions. Verify load transients, insulation, strain relief and temperature. CE07271 remains a bench candidate until this review passes.

Installation / intended use

Secure the unit and plugs, protect against spills, preserve ventilation and assess mass/CoM. Manual p5 restricts movement during operation to avoid poor connections: obtain written confirmation for fixed onboard use before purchase. [S14]

Power loss / recovery

Test low-SOC stops, tool holding after loss of power and restart inhibition. Disable unverified automatic AC restoration, scheduled start and low-load auto-off functions. Preserve the independent hardware stop path.

7. Commissioning sequence

Confirm intended-use conditions, controller nameplate and electrical protection. Then conduct an approved stationary trial logging start-up, combined arm/computer load, voltage and temperature. Check the 2 h target, low SOC, controlled loss/recovery and hardware stops with a safe test payload. Record conditions and repetitions before progressing to onboard trials.

<b>Site restriction:</b> the supplied 2026 school procurement slides explicitly list lithium batteries and 240 V equipment as not permitted in Creator Space [U1, slide 20]. Use the location designated by the lab cluster. An approved general GRA must be checked for coverage of these new activities.

<b>Abnormal heat, swelling, smell or damage:</b> stop use. For smoke or fire, evacuate and follow the local emergency procedure, calling 000 as appropriate. Do not carry a smoking/burning station or open the pack. Software STOP is not a hardware emergency stop. [S12]

School purchasing actions

GRA, budget submission, endorsement/review, eMarket and delivery

8. What the team needs to do now

STEP

ACTION / EVIDENCE

1. Scope and funding

Review five power items plus one Pi kit with the supervisor. Include the Pi in the 602.96 AUD team budget; seek separate Chemical Engineering funding for the 1,099 AUD energy system. Confirm the project code and prior expenditure.

2. Cluster review

Take the GRA, BOM and battery proposal to the designated lab cluster. Check stock/loans, charging location, electrical review, additional RA/SOP and approved suppliers. [U1, slides 6,8-10]

3. Quotes and checklist

Obtain compatible supplier quotes and the current prepurchase checklist. That checklist and the separately referenced FEIT Budget Guide are not included in the supplied folder. [U2, p 6]

4. Budget App

Use Cash for purchases and In Kind for loans/services. Group purchases by supplier, include GST and actual freight, and attach matching itemised BOM/quotes. App values round up to whole AUD. [U2, pp 3-8]

5. Submit

Upload the prepurchase checklist and support files, then click SUBMIT. Saving/Update is not submission. Supervisor endorsement is not final Faculty approval. [U2; U3, p 2]

6. eMarket

After approval, prepare a basket named with the project code. Use Catalogue, PunchOut or Free Format. Share with current cluster/Student Guides staff and allow edits, then notify the approver to complete the order/PO. [U1, slides 13-16; U4, pp 6-15]

7. Receive

Confirm the university delivery route; hazardous/bulky items may go to a specialist store. Collect after notification, inspect and retain PO/invoice/serial details. [U1, slide 16]

9. Rules that change this budget

The supplied course notice and Week 3 lecture state an 800 AUD team consumables limit. It is not an additional computer allowance. The 2026 slides say there are no reimbursements for student self-purchases [U1, slide 11]. IT equipment should first be checked for loans and recorded as In Kind [U1, slide 9; U2, pp 7-8].

The lecture labour rates and under 100 AUD Sundries convention concern project/Charter costing [U5, slides 5-6]. The procurement App guide instead requires supplier-grouped cash requests. Do not put notional student labour into the cash purchase budget.

Computing and quotation follow-up

Pi kit included in the team budget; shared energy funded separately

10. Computing route

OPTION

COST / CAPSTONE EFFECT

NEXT ACTION

Pi 5 8GB starter kit [S7]

Included: 389.43 AUD retail. Electrical 213.53 + kit =602.96.

One kit in the purchase budget. Validate task performance and price vehicle power/mounting from remaining headroom.

University loan

Fallback if a suitable computer is offered; declare the confirmed In Kind value.

Do not buy a duplicate if a suitable loan is confirmed. The current cash budget includes the Pi.

x86 Mini PC [S8]

GEEKOM A5 range 709-909 AUD; at lower bound electrical + PC =922.53.

Exceeds 800 by 122.53 before additional costs or previous spending. Exact configuration quote needed; do not rely on a coupon.

Onboard computing is required for laptop-free perception, planning and task execution. Pi 5 is a valid candidate; there is no project evidence proving it inadequate. Compare the actual RGB-D pipeline and MoveIt planning concurrently, checking latency, memory, device compatibility and heat. Buy a Mini PC only if the evidence and funding justify it; a borrowed x86 unit can reduce migration effort without a new cash request.

11. Supplier grouping and missing quotations

Core electrical subtotal: 49.95 +2.40 +(4 ×0.32) =53.63 AUD; including the budgeted Pi kit, Core totals 443.06 AUD before freight. Jaycar fuse holders: 2 ×4.95 =9.90. Assign remaining protection parts and freight to actual suppliers once quoted, then round each supplier line upward. Allowance-only rows still need quotations.

OPEN ITEM

WHAT TO OBTAIN

IO cable

Stock check and exact OEM mating/pinout confirmation; written price.80 AUD is an engineering allowance only.

Protection parts

Fuse ratings/interrupt capability, PCB/terminals, wire/guard/switch/filter and delivered quotation.50 AUD is an allowance.

Station / installation

Approved reseller or Free Format route, AU model, GST, stock/date, safety documents, original charging lead and installation/freight cost.

School paperwork

Current prepurchase checklist, project code, prior spend and current basket-sharing contacts.

Version differences to resolve: the 2026 slides and olderFAQ name different Student Guides. TheFAQ also gives conflicting instructions for changing a shared basket; create a new numbered basket for additions and confirm the current route. Some 2026 divider slides still say Semester 1. Opening dates are not current deadlines. [U1, U3]

Contacts for the team to use: feit-medlabcluster@unimelb.edu.au; chemical laboratory conditions: feit-cmmlabcluster@unimelb.edu.au; purchasing support: feit-studentguide@unimelb.edu.au. Include the project code. No emails have been sent as part of this preparation.

Sources and pricing basis

School document references and dated public-price evidence

All external pages checked 19 October 2026. Public retail prices can change and do not establish university supplier approval or robot compatibility. The companion workbook distinguishes numeric allowances from observed prices. Earlier EcoFlow search/promotion results conflicted with the canonical product page; 1099 AUD is used for its comparison, not the lower indexed offers.

School documents provided by the team

<b>U1.</b> MATZ - S2 2026 Capstone budget and procurement steps.pptx. Slides 6,8-11,13-16,20.

<b>U2.</b> FEIT Capstone Project App Guide - budget plan (updated March 2026).pdf. Pages 3-6 cash/GST/support; 7-8 In Kind.

<b>U3.</b> EMI CAPSTONE- FAQ AND FAS.pdf. Pages 2-4 risk, budget endorsement and basket handling.

<b>U4.</b> eMarket - Student User Guide 2025.pdf. Pages 4,6-15 workflow and basket permissions. Final slide is dated February 2021.

<b>U5.</b> Lecture_week3_Scheduling_and_Cost.pptx. Slides 5-6 costing rules. The team also supplied the LMS Budget-plan and E-market Guidelines notice.

Supplier and technical references - clickable links

<b>S1.</b> <link href="https://core-electronics.com.au/pololu-5v-5a-step-down-voltage-regulator-d24v50f5.html" color="#000000"><u>Core Electronics: Pololu D24V50F5, SKU POLOLU-2851</u></link>

<b>S2.</b> <link href="https://core-electronics.com.au/dc-dc-adjustable-step-down-module-5a-75w.html" color="#000000"><u>Core Electronics: adjustable XL4015, SKU CE07271</u></link>

<b>S3.</b> <link href="https://core-electronics.com.au/2-pin-screw-terminal-block-5mm-pitch.html" color="#000000"><u>Core Electronics: terminal block, SKU CE08311</u></link>

<b>S4.</b> <link href="https://www.jaycar.com.au/30a-32vdc-stackable-inline-standard-blade-fuse-holder/p/SZ2045" color="#000000"><u>Jaycar: inline fuse holder, CAT SZ2045</u></link>

<b>S5.</b> <link href="https://www.bluettipower.com.au/products/elite-100-v2-portable-power-station" color="#000000"><u>BLUETTI Australia: Elite 100 V2</u></link>

<b>S6.</b> <link href="https://au.ecoflow.com/products/ecoflow-delta-3-classic-portable-power-station" color="#000000"><u>EcoFlow Australia: DELTA 3 Classic</u></link>

<b>S7.</b> <link href="https://core-electronics.com.au/raspberry-pi-5-8gb-starter-bundle.html" color="#000000"><u>Core Electronics: Pi 5 8GB starter kit, CE09799</u></link>

<b>S8.</b> <link href="https://www.geekom.au/geekom-a5-mini-pc/" color="#000000"><u>GEEKOM Australia: A5 model range</u></link>

<b>S9.</b> <link href="https://docs.850.ufactory.cc/4.robotic_electrical_interface.html" color="#000000"><u>UFACTORY 850 tool electrical interfaces</u></link>

<b>S10.</b> <link href="https://docs.850.ufactory.cc/3.controller_electrical_interface.html" color="#000000"><u>UFACTORY 850 control-box electrical interfaces</u></link>

<b>S11.</b> <link href="https://docs.850.ufactory.cc/8.technical_specifications.html" color="#000000"><u>UFACTORY 850 technical specifications</u></link>

<b>S12.</b> <link href="https://www.cfa.vic.gov.au/fire-safety/home-fire-safety/preventing-house-fires/battery-and-charging-safety" color="#000000"><u>CFA: Battery and charging safety</u></link>

<b>S13.</b> <link href="https://www.cfa.vic.gov.au/ArticleDocuments/1933/250611%20-%20CFA%20DGMR%20Renewable%20Energy%20Facilities%20v4.4.pdf" color="#000000"><u>CFA: Renewable Energy Facilities Guidelines v4.4</u></link>

<b>S14.</b> <link href="https://s4.bluettipower.com/bluetti_lgf/support/2026/05/81a69e72-f8b6-41e9-a057-24a767ff28a5.pdf" color="#000000"><u>BLUETTI AU support: Elite 100 V2 manual</u></link>

<b>S15.</b> <link href="https://www.d1store.com.au/products/dji-power-1000-v2" color="#000000"><u>D1 Store Australia: DJI Power 1000 V2</u></link>

<b>S16.</b> <link href="https://store.dji.com/au/product/dji-power-1000-v2-200w-foldable-solar-panel-combo?from=site-nav&amp;set_region=AU" color="#000000"><u>DJI AU Store: Power 1000 V2 specifications</u></link>

<b>S17.</b> <link href="https://www.d1store.com.au/products/dji-power-2000" color="#000000"><u>D1 Store Australia: DJI Power 2000</u></link>

<b>S18.</b> <link href="https://www.dji.com/power-2000/specs" color="#000000"><u>DJI: Power 2000 specifications</u></link>

<b>S19.</b> <link href="https://www.d1store.com.au/products/dji-power-1000-mini" color="#000000"><u>D1 Store Australia: DJI Power 1000 Mini</u></link>

<b>S20.</b> <link href="https://www.dji.com/power-1000-mini/specs" color="#000000"><u>DJI: Power 1000 Mini specifications</u></link>

<b>S21.</b> <link href="https://au.ecoflow.com/products/ecoflow-delta-3-plus-portable-power-station" color="#000000"><u>EcoFlow Australia: DELTA 3 Plus</u></link>

Allowance register: E1 remaining distribution/protection 50 AUD; E2 electrical freight 20 AUD; E3 battery installation/freight 100 AUD. IO cable 80 AUD is also an allowance. These are team planning inputs, not vendor evidence.