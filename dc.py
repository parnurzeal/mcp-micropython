import time
from machine import Pin, PWM


# DC motor setup
LB = M1A = PWM(Pin(8)) # left backward
LF = M1B = PWM(Pin(9)) # left forward
RF = M2A = PWM(Pin(10)) # right forward
RB = M2B = PWM(Pin(11)) # right backward
M1A.freq(50)
M1B.freq(50)
M2A.freq(50)
M2B.freq(50)

LEFT_DUTY = 55560
RIGHT_DUTY = 60000


def test_dc():
    # Throttle value must be between -1.0 and +1.0
    print("\nForwards slow")
    forward()
    stop()
    time.sleep(1)


    print("\nLeft")
    turn_left()
    stop()
    time.sleep(1)


    print("\nBackwards")
    backward()
    stop()
    time.sleep(1)

    print("\nRight")
    turn_right()
    stop()
    time.sleep(1)


def forward():
    LB.duty_u16(0)     # Duty Cycle must be between 0 until 65535
    LF.duty_u16(LEFT_DUTY)
    RB.duty_u16(0)
    RF.duty_u16(RIGHT_DUTY)
    time.sleep(3)

def backward():
    LF.duty_u16(0)     # Duty Cycle must be between 0 until 65535
    LB.duty_u16(LEFT_DUTY)
    RF.duty_u16(0)
    RB.duty_u16(RIGHT_DUTY)
    time.sleep(3)

def turn_left():
    LF.duty_u16(LEFT_DUTY)
    RF.duty_u16(0)
    LB.duty_u16(0)
    RB.duty_u16(RIGHT_DUTY)
    time.sleep(3)
    
def turn_right():
    LF.duty_u16(0)
    LB.duty_u16(LEFT_DUTY)
    RF.duty_u16(RIGHT_DUTY)
    RB.duty_u16(0)
    time.sleep(3)

def stop():
    LB.duty_u16(0)     # Duty Cycle must be between 0 until 65535
    LF.duty_u16(0)
    RB.duty_u16(0)
    RF.duty_u16(0)
