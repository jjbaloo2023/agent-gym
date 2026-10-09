"""End-to-end real MCP client test: discovery, FreeCAD, Gmsh and OpenFOAM checks."""
import asyncio
import json
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    params = StdioServerParameters(command="/opt/agent-gym-mcp/bin/python",
                                   args=["-m", "agent_gym.mcp_server"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listing = await session.list_tools()
            assert {t.name for t in listing.tools} == {
                "build_venturi", "mesh_venturi", "inspect_design", "list_designs"}
            dimensions = dict(inlet_diameter_mm=30, throat_diameter_mm=15,
                              inlet_length_mm=20, convergent_length_mm=30,
                              throat_length_mm=15, diffuser_length_mm=60,
                              outlet_length_mm=20, wall_thickness_mm=2)
            response = await session.call_tool("build_venturi", dimensions)
            assert not response.isError, response
            cad = response.structuredContent or json.loads(response.content[0].text)
            assert cad["report"]["fluid_valid"] and cad["report"]["pipe_valid"]
            result = await session.call_tool("mesh_venturi", {"run_id": cad["run_id"], "size_mm": 3})
            assert not result.isError, result
            mesh = result.structuredContent or json.loads(result.content[0].text)
            assert mesh["openfoam_check"] == "Mesh OK."
            no_stubs = await session.call_tool("build_venturi", {
                **dimensions, "inlet_length_mm": 0, "outlet_length_mm": 0})
            assert not no_stubs.isError, no_stubs
            no_stubs_cad = no_stubs.structuredContent or json.loads(no_stubs.content[0].text)
            assert no_stubs_cad["report"]["length_mm"] == 105
            invalid = await session.call_tool("inspect_design", {"run_id": "../escape"})
            assert invalid.isError
            summary = {"fixture": "synthetic toolchain check; not a benchmark drawing",
                       "cad": cad, "mesh": mesh}
            Path("/home/gym/agent-gym-runs/toolchain-check.json").write_text(json.dumps(summary, indent=2))
            print(json.dumps(summary, indent=2))

asyncio.run(main())
