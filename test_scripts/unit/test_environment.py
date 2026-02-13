import os
import sys
import unittest
from typing import Any, Dict, cast

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.agent.base import BaseAgent
from src.environment.base import BaseEnvironment, EnvironmentFactory, EnvironmentType


class DummyAgent:
    name: str

    def __init__(self, name: str):
        self.name = name


class DummyEnvironment(BaseEnvironment):
    async def run(self, **kwargs: Any) -> Dict[str, Any]:
        return {"ok": True, **kwargs}


class TestBaseEnvironment(unittest.IsolatedAsyncioTestCase):
    async def test_create_register_get_agent(self):
        env = await DummyEnvironment.create(max_steps=5)
        self.assertEqual(env.max_steps, 5)

        agent = cast(BaseAgent, cast(object, DummyAgent(name="demo_agent")))
        env.register_agent(agent)
        self.assertIs(env.get_agent("demo_agent"), agent)

    async def test_environment_factory_unknown_type(self):
        with self.assertRaises(ValueError):
            invalid_type = cast(EnvironmentType, cast(object, "invalid"))
            _ = await EnvironmentFactory.create_environment(invalid_type)


