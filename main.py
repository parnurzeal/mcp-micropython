import config
from main_servo import start_servo
from main_motion import start_motion

if __name__ == '__main__':
    if config.ROBOT_TYPE == config.SERVO:
        start_servo()
    else:
        start_motion()

