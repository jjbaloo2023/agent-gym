# Sequential CFD recovery pilot

Run order authorized by the user: Luna (C), Sol (A), Astra (B). Start the next model only after the previous model finishes and its solver processes have exited. Models receive their own approved geometry and mesh, without another model's case, diagnostics, or results.

Common conditions: water at 20 degrees C, density 998.2 kg/m3, kinematic viscosity 1.004e-6 m2/s, volume flow 3.000 L/min (5.000e-5 m3/s). The 26 mm inlet and 16 mm throat imply bulk speeds approximately 0.09417 and 0.24868 m/s and Reynolds numbers approximately 2439 and 3963. These nominal pipe Reynolds numbers target transition; they do not establish the actual transition state in a contracting/diffusing geometry.

Models independently choose and justify physical models, boundary conditions, numerics, and diagnostics. Flow and fluid cannot be changed to obtain convergence. Existing model-specific meshes differ, so results are workflow pilots rather than a controlled comparison of numerical accuracy. Geometry is fixed; mesh limitations and boundary placement must be acknowledged.

Each solver runs serially with one CPU thread. Permit at most two attempts that reach the solution loop, ten minutes wall time each, and 1200 steady iterations per attempt or a justified finite transient budget. Bound startup repairs separately; preserve every launch and failure. The original two-launch limit stopped Luna before any iterations and was revised to support the requested recovery evaluation. This protocol change must remain visible in the event record.

Models must monitor progress, detect crashes and hangs, inspect residual and physical monitor histories, quantify flux imbalance, and distinguish converged, bounded transient, unconverged, timed out, and failed results. An exit code of zero or reaching the iteration limit is not sufficient evidence of convergence. A steady solution with a fully turbulent closure does not establish physically resolved transitional flow.

Preserve dictionaries, logs, fields, monitoring data, recovery decisions, elapsed runtime, and machine-readable metrics under artifacts/venturi-benchmark/cfd/{label}. This pilot uses agent-generated OpenFOAM cases through shell tools; the current MCP exposes CAD and meshing only. Solver MCP support remains separate future work.
