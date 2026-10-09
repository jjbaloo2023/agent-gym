# Scientific toolchain and MCP

## Installed in general-purpose WSL
Ubuntu-24.04 hosts OpenFOAM Foundation 14 (package 20261008), Gmsh 4.12.1, and FreeCAD (conda-forge package 2026.09.16, build py311hb8dae88_0; reports application version 26.3.0). FreeCAD uses /opt/agent-gym-cad, MCP SDK 1.30.0 uses /opt/agent-gym-mcp. No FreeCAD apt package is available in this Ubuntu release; the FreeCAD project's Conda route is used.

Scientific execution is WSL-native in this phase. The earlier Docker image still runs the analytical baseline only. WSL is not a per-agent security sandbox. The server exposes structured operations, not arbitrary generated Python or shell code.

Tools run as the non-root gym Linux user. Code is deployed to /home/gym/agent-gym; run artifacts live in /home/gym/agent-gym-runs, outside OneDrive. Installing a normal interactive Ubuntu user/password remains optional; the dedicated gym account is for tool execution.

## MCP tools
- build_venturi: supplied dimensions in mm -> spreadsheet-driven FCStd, pipe and fluid STEP, STL, section SVG, validity checks, artifact hashes.
- mesh_venturi: fluid STEP -> Gmsh tetrahedral MSH in metres -> OpenFOAM polyMesh with inlet/outlet/walls -> checkMesh.
- inspect_design: submitted dimensions and status/verification evidence.
- list_designs: opaque run IDs.

This is a constrained axisymmetric Venturi family. It measures drawing interpretation and tool use, not unrestricted CAD programming. It currently excludes pressure taps, flanges, fillets, and asymmetric designs. Optional inlet/outlet extensions can be zero. Wall thickness is radial; if the drawing omits it, record an explicit assumption before construction.

FreeCAD dimensions are mm; the imported fluid STEP is explicitly converted to metres for Gmsh/OpenFOAM. Native primitive expressions refer to the dimension spreadsheet. A headless reopen/edit needs two recompute passes with object touch between them; scripts/test-cad-edit.py verifies that behavior without saving the modified fixture.

Meshing is limited to two threads, 180 seconds per subprocess, a conservative preflight size bound, and 250,000 cells. A lock prevents simultaneous meshing of one design. These do not impose a hard memory or whole-process-tree limit; keep one science operation active at a time on this laptop. Failed stages retain logs and do not count as valid candidates.

## Codex registration
The globally registered server is named scientific-agent-gym. Its stdio launch command is:
```powershell
wsl.exe -d Ubuntu-24.04 -u gym --cd /home/gym/agent-gym -- /opt/agent-gym-mcp/bin/python -m agent_gym.mcp_server
```
It was registered using codex mcp add. A fresh Codex session or reconnection may be needed to load newly registered tools. The real SDK client has already tested initialization, discovery, tool calls, and errors.

## Verification and deployment
Run in WSL from /home/gym/agent-gym:
```sh
/usr/bin/python3 -m unittest discover -s tests -v
/opt/agent-gym-mcp/bin/python scripts/test-science-mcp.py
/opt/agent-gym-cad/bin/python scripts/test-cad-edit.py
```
The integration fixture is synthetic and is not a downloaded benchmark drawing. Its 145 mm domain produced 12,689 tetrahedra, with explicit inlet/outlet/walls; OpenFOAM reported Mesh OK. CAD volume matches an independent cylinder/frustum formula. A second fixture verifies zero inlet/outlet extensions.

After source changes, copy agent_gym, tests, and scripts from the Windows checkout into /home/gym/agent-gym as user gym. Do not edit both copies independently. scripts/install-science-wsl.sh records the root installer. It pins the installed FreeCAD/OpenFOAM/MCP versions; underlying apt/Conda dependency repositories can change.

Windows can inspect WSL files through \\wsl.localhost\Ubuntu-24.04\home\gym\agent-gym-runs. For GUI use, launch /opt/agent-gym-cad/bin/freecad through WSL. Mesh checks are topology/quality checks, not a solved or physically validated CFD simulation.

## Drawing, scoring, CFD
See benchmarks/venturi for the three-model plan and scoring template. Drawing download/model runs await explicit approval. Human scores choose the preferred valid design. CFD then needs specified fluid/boundary conditions, a short validated case, and mesh refinement before any overnight job. No solver run or overnight automation is started by these MCP tools.

Primary documentation:
- https://openfoam.org/download/14-ubuntu/
- https://github.com/FreeCAD/FreeCAD_Conda
- https://gmsh.info/doc/texinfo/
- https://modelcontextprotocol.io/docs/develop/build-server
