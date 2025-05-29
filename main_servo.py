import asyncio
import sys
import servo
from main_server_loop import run_loop

from mcp.registry import ToolRegistry

def setup_my_tools(servo_motors: servo.Servo):
    registry = ToolRegistry()
    registry.register_tool(
        name="turn_left",
        description="turn the servo motor to left by some degrees",
        input_schema={
            "angle": {"type":"number",  "description": "degrees of the angle to turn"}
        },
        handler_func=servo_motors.turn_left
    )
    registry.register_tool(
        name="turn_right",
        description="turn the servo motor to right by some degrees",
        input_schema={
            "angle": {"type":"number",  "description": "degrees of the angle to turn"}
        },
        handler_func=servo_motors.turn_right
    )
    registry.register_tool(
        name="look_upward",
        description="Move the head of the robot upward",
        input_schema={},
        handler_func=servo_motors.look_upward
    )
    registry.register_tool(
        name="look_downward",
        description="Move the head of the robot downward",
        input_schema={},
        handler_func=servo_motors.look_downward
    )   
    return registry

if __name__ == "__main__":
    try:
        servo_motor = servo.Servo()
        asyncio.run(run_loop(setup_my_tools(servo_motors=servo_motor)))
    except KeyboardInterrupt:
        print("Main application interrupted by user. Exiting.", file=sys.stderr)
    except Exception as e:
        print(
            f"An unexpected error occurred in main: {type(e).__name__}: {e}",
            file=sys.stderr,
        )
