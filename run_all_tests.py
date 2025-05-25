# run_all_tests.py
import uasyncio  # Reverted to uasyncio for MicroPython environment
import sys

# Ensure the project root is in the path so 'tests' can be imported as a package.
if "." not in sys.path:
    sys.path.insert(0, ".")

# sys.path should have "." from the initial lines, which is the project root.
# Importing modules from the 'tests' package.
import tests.test_tool_registry
import tests.test_tool_handlers
import tests.test_resource_handlers
import tests.test_prompt_handlers
import tests.test_stdio_transport
import tests.test_wifi_server  # New import


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

    # Run Wifi Server tests
    await tests.test_wifi_server.run_wifi_server_tests()
    print("=======================================\\n")

    print(">>> All MCP MicroPython Tests Completed <<<", file=sys.stderr)


if __name__ == "__main__":
    all_passed = False
    try:
        uasyncio.run(main_test_suite())  # Reverted to uasyncio
        all_passed = True  # If main_test_suite completes without exception
    except KeyboardInterrupt:
        print("Test suite interrupted by user.", file=sys.stderr)
        sys.exit(130)  # Standard exit code for Ctrl+C
    except Exception as e:
        print(f"!!! A TEST OR THE TEST SUITE FAILED !!!", file=sys.stderr)
        print(f"Error details: {type(e).__name__}: {e}", file=sys.stderr)
        # If MicroPython has traceback module and it's useful:
        # import traceback
        # traceback.print_exc(file=sys.stderr)
        sys.exit(1)  # Exit with error code 1 on any test failure or error

    if all_passed:
        print("---------------------------------------", file=sys.stderr)
        print(">>> ALL TESTS PASSED SUCCESSFULLY <<<", file=sys.stderr)
        print("---------------------------------------", file=sys.stderr)
        sys.exit(0)  # Explicitly exit with 0 on success
    else:
        # This case should ideally not be reached if exceptions are handled above,
        # but as a fallback.
        print(
            "!!! SOME TESTS MAY HAVE FAILED (runner did not complete successfully) !!!",
            file=sys.stderr,
        )
        sys.exit(1)
