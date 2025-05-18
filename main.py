import uasyncio
import mcp


async def main():
    print("Starting MCP MicroPython Stdio Server from main.py...")
    await mcp.stdio_server()
    print("MCP MicroPython Stdio Server finished in main.py.")


if __name__ == "__main__":
    try:
        uasyncio.run(main())
    except KeyboardInterrupt:
        print("Main application interrupted. Exiting.")
    except Exception as e:
        print(f"An error occurred in main: {e}")
