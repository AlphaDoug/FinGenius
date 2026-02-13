import os
import sys
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.mcp.server import MCPServer, create_starlette_app



class TestMCPServer(unittest.TestCase):
    def test_build_docstring_and_signature(self):
        server = MCPServer()
        tool_function = {
            "description": "demo tool",
            "parameters": {
                "properties": {
                    "text": {"type": "string", "description": "demo text"},
                    "count": {"type": "integer", "description": "demo count"},
                },
                "required": ["text"],
            },
        }

        doc = server._build_docstring(tool_function)
        self.assertIn("Parameters:", doc)
        self.assertIn("text", doc)
        self.assertIn("(required)", doc)

        sig = server._build_signature(tool_function)
        params = list(sig.parameters.values())
        self.assertEqual(params[0].name, "text")
        self.assertEqual(params[1].name, "count")

    def test_create_starlette_app_has_health(self):
        server = MCPServer()
        app = create_starlette_app(server.server._mcp_server, debug=False)
        paths = [getattr(route, "path", "") for route in app.routes]
        self.assertIn("/health", paths)
