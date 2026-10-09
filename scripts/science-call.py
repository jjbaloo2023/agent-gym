"""Call the scientific MCP in an isolated, budgeted benchmark workspace."""
import argparse
import asyncio
import fcntl
import json
import os
from pathlib import Path
import time
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def call(args):
    root = Path(args.runs_root).resolve()
    base = Path('/home/gym/agent-gym-benchmarks')
    if root.parent != base or not root.name.startswith('attempt-'):
        raise ValueError('Expected a dedicated benchmark attempt directory')
    root.mkdir(parents=True, exist_ok=True)
    ledger = root/'tool-calls.json'
    rows = json.loads(ledger.read_text()) if ledger.exists() else []
    if len(rows) >= 12 or (rows and time.time()-rows[0]['started_at'] > 900):
        raise RuntimeError('Attempt tool/time budget exhausted')
    params = json.loads(Path(args.arguments).read_text()) if args.arguments else {}
    row = {'tool': args.tool, 'arguments': params, 'started_at': time.time()}
    rows.append(row)
    ledger.write_text(json.dumps(rows, indent=2))
    try:
        with (base/'.toolchain.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            server = StdioServerParameters(command='/opt/agent-gym-mcp/bin/python',
                args=['-m','agent_gym.mcp_server'], env={**os.environ,'AGENT_GYM_SCIENCE_RUNS': str(root)})
            async with stdio_client(server) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    if args.tool == 'list_tools':
                        result = (await session.list_tools()).model_dump(mode='json')
                    else:
                        response = await session.call_tool(args.tool, params)
                        if response.isError:
                            raise RuntimeError(response.content[0].text)
                        result = response.structuredContent or json.loads(response.content[0].text)
            row['result'] = result
            print(json.dumps(result, indent=2))
    except Exception as error:
        row['error'] = str(error)
        raise
    finally:
        row['finished_at'] = time.time()
        ledger.write_text(json.dumps(rows, indent=2))

parser=argparse.ArgumentParser()
parser.add_argument('tool', choices=['list_tools','build_venturi','mesh_venturi','inspect_design','list_designs'])
parser.add_argument('--runs-root', required=True)
parser.add_argument('--arguments')
asyncio.run(call(parser.parse_args()))
