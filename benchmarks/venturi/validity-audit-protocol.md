# Agent-decided numerical-validity follow-up

The user requested that each model assess its own numerical validity, decide whether correction experiments are needed, select the corrections, and rerun if warranted. This follows the initial CFD recovery pilot, rather than replacing or overwriting it.

Each model audits only its own results and records an experiment plan before further solves. Agents may read and plan concurrently, but meshing and solving remain sequential in order Luna, Sol, Astra. The coordinator releases compute slots and reviews evidence; it does not prescribe a scientific correction strategy. Decisions not to rerun must also be justified.

Common conditions remain water at 20 degrees C, density 998.2 kg/m3, kinematic viscosity 1.004e-6 m2/s, volume flow 3.000 L/min, and the approved Venturi geometry. Mesh, domain and physical-model changes require explicit documentation and comparisons. Prior pilot artifacts remain intact. Each model is allowed up to three additional actual solves, each with a ten-minute wall-clock watchdog, finite model-selected step/iteration budget, one CPU thread, and at most 250,000 cells. Startup repairs are separately bounded and logged.

Agents select appropriate numerical and physical checks, tolerances, and experiments before running. Reports must distinguish convergence of a discrete problem, sensitivity to numerical choices, and evidence for physical accuracy. A bounded or inconclusive result is acceptable; residual reduction alone cannot establish validity. Preserve logs, execution status, fields, monitor histories, comparison metrics and recovery decisions in artifacts/venturi-benchmark/cfd/{label}/validity-audit.

The benchmark compares these workflows and decisions. Different independently selected experiments do not provide a controlled model ranking or common accuracy score. No new score or training eligibility is implied.
