import unittest

from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain.agents.middleware.tool_call_limit import ToolCallLimitExceededError
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import tool


class FakeToolCallingModel(GenericFakeChatModel):
    def bind_tools(self,tools,**kwargs):
        return self

class AgentLimitTests(unittest.TestCase):
    def test_rejects_entire_batch_when_over_limit(self):
        executed=[]

        @tool
        def demo_search(query:str)->str:
            """Return a fixed search result."""
            executed.append(query)
            return "fixed result"

        reply = AIMessage(
            content="",
            tool_calls=[
                {"name":"demo_search","args":{"query":f"q{i}"},"id":f"call_{i}"}
                for i in range(4)
            ]
        )
        agent = create_agent(
            model=FakeToolCallingModel(messages=iter([reply]),disable_streaming=True),
            tools=[demo_search],
            middleware=[ToolCallLimitMiddleware(run_limit=3,exit_behavior="error")],
        )

        with self.assertRaises(ToolCallLimitExceededError):
            agent.invoke({"messages": [{"role": "user", "content": "开始测试"}]})

        self.assertEqual(executed,[])
    def test_rejects_entire_batch_when_not_over_limit(self):
        executed=[]

        @tool
        def demo_search(query:str)->str:
            """Return a fixed search result."""
            executed.append(query)
            return "fixed result"

        reply = AIMessage(
            content="",
            tool_calls=[
                {"name":"demo_search","args":{"query":f"q{i}"},"id":f"call_{i}"}
                for i in range(3)
            ]
        )
        agent = create_agent(
            model=FakeToolCallingModel(messages=iter([reply,AIMessage(content="done")]),disable_streaming=True),
            tools=[demo_search],
            middleware=[ToolCallLimitMiddleware(run_limit=3,exit_behavior="error")],
        )

        # with self.assertRaises(ToolCallLimitExceededError):
        result=agent.invoke({"messages": [{"role": "user", "content": "开始测试"}]})

        self.assertCountEqual(executed,["q0","q1","q2"])
        self.assertEqual(result["messages"][-1].content,"done")
    def test_rejects_entire_batch_when_over_limit_by_two_toolbatches(self):
        executed=[]

        @tool
        def demo_search(query:str)->str:
            """Return a fixed search result."""
            executed.append(query)
            return "fixed result"

        reply1 = AIMessage(
            content="",
            tool_calls=[
                {"name":"demo_search","args":{"query":f"q{i}"},"id":f"call_{i}"}
                for i in range(3)
            ]
        )
        reply2 = AIMessage(
            content="",
            tool_calls=[
                {"name":"demo_search","args":{"query":"q4"},"id":"call_4"}
    
            ]
        )
        agent = create_agent(
            model=FakeToolCallingModel(messages=iter([reply1, reply2]),disable_streaming=True),
            tools=[demo_search],
            middleware=[ToolCallLimitMiddleware(run_limit=3,exit_behavior="error")],
        )

        with self.assertRaises(ToolCallLimitExceededError):
            agent.invoke({"messages": [{"role": "user", "content": "开始测试"}]})

        self.assertCountEqual(executed,["q0","q1","q2"])

if __name__ == "__main__":
    unittest.main()