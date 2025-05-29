# Import neccessary libraries
import time
from machine import Pin, PWM

# You might need to calibrate the min_dutycycle (pulse at 0 degrees) and max_dutycycle (pulse at 180 degrees) to get an accurate servo angle.
# The servo dutycycle values 2200-8300 represent 0-180 degrees.
min_dutycycle = 2200
max_dutycycle = 8300
dutycycle = 0

class Servo:

    def __init__(self) -> None:
        self._horizontal_angle = 90
        self._vertical_angle = 90
        self._horizontal_motor = PWM(Pin(12)) 
        self._vertical_motor = PWM(Pin(13))
        self._horizontal_motor.freq(50)
        self._vertical_motor.freq(50)
        self._update_angle(self._horizontal_angle, self._horizontal_motor)
        self._update_angle(self._vertical_angle, self._vertical_motor)

    async def turn_left(self, angle: int) -> None:
        """Turn the robot left to `angle` degrees.
        
        Args:
            angle: degress to turn
        """
        print('turn left', angle)
        new_angle = self._horizontal_angle - angle
        self._horizontal_angle = self._update_angle(
            angle=new_angle, motor=self._horizontal_motor
        )

    async def turn_right(self, angle: int) -> None:
        """Turn the robot right to `angle` degrees.
        
        Args:
            angle: degress to turn
        """
        new_angle = self._horizontal_angle + angle
        self._horizontal_angle = self._update_angle(
            angle=new_angle, motor=self._horizontal_motor
        )

    async def look_upward(self) -> None:
        """Let the robot look upward """
        self._vertical_angle = self._update_angle(
            angle=(self._vertical_angle - 20), 
            motor=self._vertical_motor,
        )

    async def look_downward(self) -> None:
        """Let the robot look downward """
        self._vertical_angle = self._update_angle(
            angle=(self._vertical_angle + 20), 
            motor=self._vertical_motor,
        )

    def _update_angle(self, angle: int, motor: PWM) -> int:
        if angle < 0: angle = 0
        if angle > 180: angle = 180
        dutycycle = int(((max_dutycycle - min_dutycycle) / 180) * angle) + min_dutycycle
        motor.duty_u16(dutycycle)
        return angle
