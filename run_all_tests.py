# run_all_tests.py
import uasyncio
import sys

# Ensure the project root is in the path so 'tests' can be imported as a package.
if "." not in sys.path:
    sys.path.insert(0, ".")

# sys.path should have "." from the initial lines, which is the project root.
# Importing modules from the 'tests' package.
import tests.test_tool_registry
import tests.test_tool_handlers
import tests.test_resource_handlers
import tests.test_prompt_handlers  # New
import tests.test_stdio_transport


async def main_test_suite():
    """
    Runs all test suites sequentially.
    """
    print(">>> Running All MCP MicroPython Tests <<<")
    print("\\n=======================================")

    # Run ToolRegistry tests
    await tests.test_tool_registry.run_tool_registry_tests()
    print("=======================================\\n")

    # Run Tool Handler tests
    await tests.test_tool_handlers.run_tool_handler_tests()
    print("=======================================\\n")

    # Run Resource Handler tests
    await tests.test_resource_handlers.run_resource_handler_tests()
    print("=======================================\\n")

    # Run Prompt Handler tests
    await tests.test_prompt_handlers.run_prompt_handler_tests()
    print("=======================================\\n")

    # Run Stdio Transport tests
    await tests.test_stdio_transport.run_stdio_transport_tests()
    print("=======================================\\n")

    print(">>> All MCP MicroPython Tests Completed <<<")


if __name__ == "__main__":
    try:
        uasyncio.run(main_test_suite())
    except KeyboardInterrupt:
        print("Test suite interrupted.")
    except Exception as e:
        print(f"An error occurred during the test suite: {e}")
        # Optionally re-raise or exit with error code for CI environments
        # raise e
