import asyncio, os, sys, time
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

async def main():
    params = StdioServerParameters(command="npx", args=sys.argv[1:], env=dict(os.environ))
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            t0 = time.time()
            await s.initialize()
            print(f"init {time.time()-t0:.1f}s", flush=True)
            for name, args, to in [
                ("browser_navigate", {"url": "about:blank"}, 30),
                ("browser_navigate", {"url": "https://example.com"}, 90),
                ("browser_snapshot", {}, 30),
                ("browser_close", {}, 30),
            ]:
                t0 = time.time()
                try:
                    res = await asyncio.wait_for(s.call_tool(name, args), timeout=to)
                    txt = res.content[0].text[:300] if res.content else ""
                    print(f"{name}: OK {time.time()-t0:.1f}s isErr={res.isError} :: {txt}".replace("\n"," | "), flush=True)
                except asyncio.TimeoutError:
                    print(f"{name}: TIMEOUT {to}s", flush=True)

asyncio.run(main())