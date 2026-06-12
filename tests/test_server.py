import subprocess
import sys
import unittest


class TestStartup(unittest.TestCase):
    def test_server_startup(self):
        try:
            subprocess.run(
                [sys.executable, "-m", "markindex"],
                timeout=2,
                capture_output=True,
                check=True
            )
        except subprocess.TimeoutExpired:
            pass # Expected, stdio server waits for input
        except subprocess.CalledProcessError as e:
            self.fail(f"Server startup failed: {e.stderr.decode()}")

    def test_register_tools(self):
        try:
            from markindex.server import _register_tools
            _register_tools()
        except Exception as e:
            self.fail(f"_register_tools raised an exception: {e}")

if __name__ == "__main__":
    unittest.main()
