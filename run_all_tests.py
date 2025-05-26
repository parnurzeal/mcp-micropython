# run_all_tests.py
import sys

# Ensure the project root is in the path so 'tests' can be imported as a package.
if "." not in sys.path:
    sys.path.insert(0, ".")

# This script is intended to be run ONLY with MicroPython.
import sys

# Ensure the project root is in the path so 'tests' can be imported as a package.
if "." not in sys.path:
    sys.path.insert(0, ".")

import uasyncio as asyncio

print("Using native uasyncio for tests.")

# Importing common test modules
import tests.test_tool_registry
import tests.test_tool_handlers
import tests.test_resource_handlers
import tests.test_prompt_handlers
import tests.test_stdio_transport

# Setup flags and module placeholders for conditional test execution
RUN_WIFI_TESTS = False
wifi_test_module = None
RUN_BLUETOOTH_TESTS = False
bluetooth_test_module = None

# Try to import for native Wi-Fi tests
try:
    import network
    import microdot  # Required by wifi_server and its tests
    import tests.test_wifi_server

    wifi_test_module = tests.test_wifi_server
    RUN_WIFI_TESTS = True
    print("MicroPython env: Native Wi-Fi tests will be attempted.")
except ImportError as e:
    print(f"Skipping native Wi-Fi tests due to ImportError: {e}")
    print(
        "Ensure 'network' and 'microdot' are available in your MicroPython environment."
    )

# Try to import for native Bluetooth tests
try:
    import bluetooth
    import aioble  # Required by bluetooth_server and its tests
    import tests.test_bluetooth_server

    bluetooth_test_module = tests.test_bluetooth_server
    RUN_BLUETOOTH_TESTS = True
    print("MicroPython env: Bluetooth tests will be attempted.")
except ImportError as e:
    print(f"Skipping Bluetooth tests due to ImportError: {e}")
    print(
        "Ensure 'bluetooth' and 'aioble' are available in your MicroPython environment."
    )


async def main_test_suite():
    """
    Runs all test suites sequentially.
    """
    print(">>> Running All MCP MicroPython Tests <<<")  # Clarified title
    print("\\n=======================================")

    await tests.test_tool_registry.run_tool_registry_tests()
    print("=======================================\\n")

    await tests.test_tool_handlers.run_tool_handler_tests()
    print("=======================================\\n")

    await tests.test_resource_handlers.run_resource_handler_tests()
    print("=======================================\\n")

    await tests.test_prompt_handlers.run_prompt_handler_tests()
    print("=======================================\\n")

    await tests.test_stdio_transport.run_stdio_transport_tests()
    print("=======================================\\n")

    if RUN_WIFI_TESTS and wifi_test_module:
        print("--- Running Native Wi-Fi Server Tests ---")
        await wifi_test_module.run_wifi_server_tests()
        print("=======================================\\n")
    else:
        print("--- Wi-Fi Server Tests SKIPPED ---")  # Simplified skip message
        print("=======================================\\n")

    if RUN_BLUETOOTH_TESTS and bluetooth_test_module:
        print("--- Running Native Bluetooth Server Tests ---")
        await bluetooth_test_module.run_bluetooth_server_tests()
        print("=======================================\\n")
    else:
        print("--- Bluetooth Server Tests SKIPPED ---")
        print("=======================================\\n")

    print(">>> All MCP Tests Completed <<<", file=sys.stderr)


if __name__ == "__main__":
    all_passed = False
    try:
        asyncio.run(main_test_suite())
        all_passed = True
    except KeyboardInterrupt:
        print("Test suite interrupted by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"!!! A TEST OR THE TEST SUITE FAILED !!!", file=sys.stderr)
        print(f"Error details: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)

    if all_passed:
        print("---------------------------------------", file=sys.stderr)
        print(">>> ALL TESTS PASSED SUCCESSFULLY <<<", file=sys.stderr)
        print("---------------------------------------", file=sys.stderr)
        sys.exit(0)
    else:
        print(
            "!!! SOME TESTS MAY HAVE FAILED (runner did not complete successfully) !!!",
            file=sys.stderr,
        )
        sys.exit(1)
