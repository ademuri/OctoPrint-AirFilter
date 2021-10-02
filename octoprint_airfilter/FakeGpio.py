
class FakeGpio:
    """Emulation for Raspberry PI GPIO"""
    def __init__(self):
        pass

    def output(self, pin_number, value):
        print(f'Set pin {pin_number} to {1 if value else 0}')

    def PWM(self, pin_number, pwm_frequency):
        return FakePwm(pin_number, pwm_frequency)

class FakePwm:
    def __init__(self, pin, frequency):
        print(f'Initialize PWM {pin} with frequency {frequency}')
        self.pin = pin
        self.frequency = frequency

    def ChangeFrequency(self, frequency):
        print(f'Change PWM {self.pin} to frequency {self.frequency}')

    def start(self, duty_cycle):
        print(f'Start PWM {self.pin} at {duty_cycle}%')

    def stop(self):
        print(f'Stop PWM {self.pin}')

