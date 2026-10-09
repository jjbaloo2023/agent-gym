"""Scientific Agent Gym stdio MCP server; no arbitrary shell or code tools."""
from mcp.server.fastmcp import FastMCP
from .science import ROOT, build, mesh, inspect_run

mcp = FastMCP("scientific-agent-gym")

@mcp.tool()
def build_venturi(inlet_diameter_mm: float, throat_diameter_mm: float,
                  inlet_length_mm: float, convergent_length_mm: float,
                  throat_length_mm: float, diffuser_length_mm: float,
                  outlet_length_mm: float, wall_thickness_mm: float = 2.0) -> dict:
    """Build an editable axisymmetric Venturi in FreeCAD. All dimensions are mm.
    Returns opaque run ID, native FCStd, fluid/pipe STEP, STL and section SVG.
    This is a bounded five-section Venturi tool, not arbitrary CAD scripting."""
    return build(dict(inlet_diameter_mm=inlet_diameter_mm, throat_diameter_mm=throat_diameter_mm,
                      inlet_length_mm=inlet_length_mm, convergent_length_mm=convergent_length_mm,
                      throat_length_mm=throat_length_mm, diffuser_length_mm=diffuser_length_mm,
                      outlet_length_mm=outlet_length_mm, wall_thickness_mm=wall_thickness_mm))

@mcp.tool()
def mesh_venturi(run_id: str, size_mm: float = 3.0) -> dict:
    """Mesh the fluid STEP with Gmsh, convert to OpenFOAM, and run checkMesh.
    Bounded serial operation; does not start a CFD solver."""
    return mesh(run_id, size_mm)

@mcp.tool()
def inspect_design(run_id: str) -> dict:
    """Retrieve submitted dimensions, CAD validity, artifact hashes, and mesh results."""
    return inspect_run(run_id)

@mcp.tool()
def list_designs() -> list[dict]:
    """List available design IDs and completion status, without exposing unrelated files."""
    if not ROOT.exists():
        return []
    return [{"run_id": p.name} for p in sorted(ROOT.iterdir()) if p.is_dir() and len(p.name) == 32]

if __name__ == "__main__":
    mcp.run(transport="stdio")
