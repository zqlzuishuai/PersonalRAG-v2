async def test_mcp(url: str, token: str, query: str) -> None:
    import httpx2
    from mcp import Client
    from mcp.client.streamable_http import streamable_http_client

    async with httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
        trust_env=False,
    ) as http:
        transport = streamable_http_client(url,http_client=http)
        async with Client(transport,cache=None) as client:
            tools=await client.list_tools()
            print("可用工具：",[tool.name for tool in tools.tools])
            result=await client.call_tool("rag_search",{"query":query,"top_k":3})
            if result.is_error:
                raise ValueError("调用rag_search失败")
            print(f"调用rag_search成功，结果：{result.structured_content}")

            print("***"*20)


            results=result.structured_content["result"]
            if not results:
                print("rag_search没有返回结果")
                return
            
            chunk_id = results[0]["chunk_id"]
            print(f"调用rag_fetch，chunk_id={chunk_id}")
            print("***"*20)
            chunk=await client.call_tool("rag_fetch",{"chunk_id":chunk_id})
            if chunk.is_error:
                raise ValueError("调用rag_fetch失败")
            print(f"调用rag_fetch成功，结果：{chunk.structured_content}")
            print("***"*20)

if __name__ == "__main__":
    import asyncio

    from config import load_settings
    settings= load_settings()

    asyncio.run(
        test_mcp(
            url=f"http://{settings.mcp_host}:{settings.mcp_port}/mcp",
            token=settings.auth_token,
            query="毛泽东思想活的灵魂是什么"
        )
    )