# run_all_tests.py
import sys

# Ensure the project root is in the path so 'tests' can be imported as a package.
if "." not in sys.path:
    sys.path.insert(0, ".")

# This script is intended to be run ONLY with MicroPython.
# Use native uasyncio.
import uasyncio as asyncio

print("Using native uasyncio for tests.")

# mock_bootstrap.py has been removed.
# All tests are expected to run in a MicroPython environment.
# Importing modules from the 'tests' package.
import tests.test_tool_registry
import tests.test_tool_handlers
import tests.test_resource_handlers
import tests.test_prompt_handlers
import tests.test_stdio_transport

# import tests.test_wifi_server # Import will be conditional

# Conditionally import and run Wi-Fi tests
RUN_WIFI_TESTS = False
wifi_test_module = None
try:
    import network
    import microdot  # microdot is needed by test_wifi_server and the server itself
    import tests.test_wifi_server

    wifi_test_module = tests.test_wifi_server
    RUN_WIFI_TESTS = True
    print(
        "MicroPython environment with 'network' and 'microdot' found, will run Wi-Fi tests."
    )
except ImportError as e:
    print(f"Skipping Wi-Fi tests due to ImportError: {e}")
    print(
        "This is expected if the MicroPython build/port lacks network modules or if 'microdot' is not installed."
    )
    print(
        "Ensure 'network' is part of your firmware and 'microdot' is installed (e.g., via mip or mpremote)."
    )


# Conditionally import and run bluetooth tests
RUN_BLUETOOTH_TESTS = False
bluetooth_test_module = None
# We assume sys.implementation.name will be "micropython" since this script is for MicroPython.
try:
    import bluetooth
    import aioble
    import tests.test_bluetooth_server  # Import only if bluetooth and aioble are present

    bluetooth_test_module = tests.test_bluetooth_server
    RUN_BLUETOOTH_TESTS = True
    print(
        "MicroPython environment with 'bluetooth' and 'aioble' found, will run Bluetooth tests."
    )
except ImportError as e:
    print(f"Skipping Bluetooth tests due to ImportError: {e}")
    print(
        "This is expected if the MicroPython build/port lacks necessary Bluetooth modules."
    )
    print(
        "Ensure 'bluetooth' is part of your firmware and 'aioble' is installed (e.g., via mip or mpremote)."
    )
# Removed the 'else' block for non-MicroPython interpreters, as this script is now uPy-only.


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
    if RUN_WIFI_TESTS and wifi_test_module:
        await wifi_test_module.run_wifi_server_tests()
        print("=======================================\\n")
    else:
        print("--- Wi-Fi Server Tests SKIPPED ---")
        print("=======================================\\n")

    # Run Bluetooth Server tests
    if RUN_BLUETOOTH_TESTS and bluetooth_test_module:
        await bluetooth_test_module.run_bluetooth_server_tests()
        print("=======================================\\n")
    else:
        print("--- Bluetooth Server Tests SKIPPED ---")
        print("=======================================\\n")

    print(">>> All MCP MicroPython Tests Completed <<<", file=sys.stderr)


if __name__ == "__main__":
    all_passed = False
    try:
        asyncio.run(main_test_suite())  # Reverted to uasyncio
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
