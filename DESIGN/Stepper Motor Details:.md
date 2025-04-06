Stepper Motor Details:
How many stepper motors are you controlling (I assume 4 motors for wheels X, Y, Z, A)?
What is the step resolution of your stepper motors/drivers?
Are you using microstepping? If so, what microstepping setting?
CNC Shield Specifics:
Which CNC shield model are you using? (e.g., Arduino CNC Shield V3, V4)
Are you using additional driver boards (like A4988, DRV8825, TMC2208)?
Does your shield have enable pins that need to be controlled?
Rotary Encoder Details:
Pins for connecting the rotary encoder to Arduino
Debounce requirements
LCD Display:
Which I2C address is your LCD using? (typically 0x27 or 0x3F)
Do you need specific I2C pins (SDA/SCL) or will the default ones work?
Additional Functionality:
Do you need to implement the LFO (Low Frequency Oscillation) in real-time to modulate the motor speeds?
Are there any emergency stop or limit switch requirements?
Does the system need to remember settings across power cycles (using EEPROM)?
Any timing constraints or requirements for the motor control loop?
Power Management:
What's powering your stepper motors? (Is it separate from the Arduino's power?)
Are there any current limitations to be aware of?
Having these details will help create a more tailored and functional Arduino program that will work well with your specific hardware setup.
1. There are a maximum of four motors being controlled. X, Y and Z are all drive wheels which drive the motion of the machine. A is the platen where the linkages will draw images with a pen. Lets create the program for no microstepping by default, but lets also include a variable for implementing microstepping as the final design will use 128 step microstepping drivers. 

2. The CNC shield is a v3.0 version. Eventually I will use the TMC2208 drivers but currently I am using the A4988 drivers that came with the shield. I will be using the four independent motor controls on the shield ((X,Y,Z and A) along with some of the axis pins to receive the rotary encoder and button data. I haven't received the I2C display yet so for now we'll also include a full set of serial commands to operate the program. I will also confirm the pins I am using after this message. and before you begin coding. A basic debounce library should suffice for the encoder operations as there will be no real time control of the motors. Changes to motor speed are only applied in the sub-menus when returning to the main screen.

5. I will eventually add an e-stop but there isn't one for now. Settings will be reset to default upon boot. Settings such as the ratios will be hard-coded into the software. Once I have a minimum viable product I'll be able to tune the motor control further based on how it works together.

6. The power for the motor shield comes from the 12V+ rail of a converted computer power supply, it should have plenty of power for the low speed operation of the machine. 

Thanks for the detailed information. This helps clarify the requirements. Before I start coding, let's confirm a few more specifics about the pin connections:
Rotary Encoder Pins:
Which Arduino pins will you connect to the rotary encoder's CLK, DT, and SW pins?
Typical connections might be pins 2 and 3 for the CLK and DT (these support interrupts) and another pin for the SW (button).
I2C LCD Pins:
For a standard Arduino Uno, the I2C pins are A4 (SDA) and A5 (SCL). Is this setup acceptable for your design?
Available Pins on CNC Shield:
The CNC Shield v3.0 generally connects to these Arduino pins:
X stepper: Pins 2 (step) and 5 (direction)
Y stepper: Pins 3 (step) and 6 (direction)
Z stepper: Pins 4 (step) and 7 (direction)
A stepper: Pins 12 (step) and 13 (direction)
Enable pin: Pin 8
Are you planning to use the standard pin assignments of the CNC Shield? If not, what are your custom assignments?
Serial Interface:
For the serial command interface, what baud rate would you like to use? (9600 is typical but 115200 provides faster communication)
Would you like a specific command syntax for serial control?
Motor Parameters:
What are the steps per revolution for your stepper motors? (Typically 200 for 1.8° motors or 400 for 0.9° motors)
What's the maximum speed (in RPM or steps/second) you'd like to target?
Once I have this information, I can create a well-tailored Arduino program for your system.
Could I use the limit switch connections on the board to access D9,D10 and D11 for the encoder?

Yes, you can absolutely use the limit switch pins (D9, D10, D11) on the CNC Shield for your rotary encoder. This is a good approach since those pins are:
Readily accessible via the CNC Shield's limit switch connections
Not being used for stepper motor control
Capable of handling the digital input required for the encoder
Here's how you could connect them:
D9: Connect to rotary encoder's CLK (clock) pin
D10: Connect to rotary encoder's DT (data) pin
D11: Connect to rotary encoder's SW (switch/button) pin
Using these pins would leave the standard stepper motor control pins (2, 3, 4, 5, 6, 7, 8, 12, 13) available for their intended purpose with the CNC Shield. The I2C LCD would still use A4 (SDA) and A5 (SCL) which don't conflict with the CNC Shield's functionality.
Does this configuration work for you? If so, I can proceed with developing the code using these pin assignments.
For your remaining quetions. The I2C will be on the standard A4 and A5 pins. I will be using the standard pin asssignments for step and direction of the motor control. We can use the 9600 serial baud rate for now. The motors are 200 step 1.8deg motors connected to drive wheels via a 1:3 gear ratio. The user editable parameters like wheel speed and the LFO controls should take the motor and gear parameters into account. Related to that, lets talk a little about the data structure and types befor you begin.

Great, let's clarify the data structure and types before beginning the code implementation. Based on your system specifications, here's what I'm thinking:
1. Motor Configuration Parameters:
200 steps per revolution (1.8° motors)
1:3 gear ratio (3x multiplication for steps)
This means 600 steps per revolution of the wheel
2. Speed Parameters:
The user-editable wheel speeds (range 0.0 to 256.0) should represent RPM of the wheels
We'll need to convert these to steps/second for the stepper library
Formula: steps_per_second = (rpm * steps_per_revolution) / 60
3. Data Types for Variables:
Menu navigation: Use byte or uint8_t for indices (efficient for Arduino)
Wheel speeds: Use float to allow decimal precision
LFO parameters:
Depths: float (0.0 to 100.0%)
Rates: float (0.0 to 256.0)
Polarity: bool (0 for UNI, 1 for BI)
Master time multiplier: float (0.01 to 999.99)
Ratio presets: Store as arrays of float
Motor step intervals: Use unsigned long for microsecond timing
4. Core Functionalities to Implement:
Menu navigation system as per the LCD Menu Schema
Real-time motor control based on current parameters
LFO modulation applied to base speeds
Serial command interface for debugging/control
Interrupt-based encoder reading for reliable input
Debounced button handling with short/long press detection
5. Proposed Libraries:
LiquidCrystal_I2C for the 16x2 LCD display
AccelStepper for advanced stepper motor control
Encoder library for rotary encoder reading (or manual implementation)
6. Overall Structure:
Setup function: Initialize hardware, default parameters
Loop function: Handle inputs, update display, calculate and set motor speeds
Input handling functions: Process encoder and button inputs
Display update functions: Format and show current menu/values
Motor control functions: Calculate speeds including LFO, update stepper motors
Serial interface functions: Process commands, provide feedback
Does this approach align with your expectations? Would you like to modify any aspects of this data structure or implementation plan before I start coding?
So, the way I currently envisage the machine, the master time multiplier is the number of seconds it takes to complete 1 rotation of the drive wheel.  This number can be fine set to fine tune the speed at which the linkages all drive quickly but also smoothly. 

The user set parameters for the wheel speed should be scaled so that a wheel speed of 1 is 1 rotation in 1 master time. A wheel speed of 2 should be 1/2 rotations in 1 master time. A wheel speed of 10 should be 1/10 rotations in 1 master time. 

LFO rate should be the same system, a rate of 1 is equal to a wheel speed of 1, ie 1 full LFO cycle in 1 master time. When set to UNI for the polarity, the LFO settings should never cause the wheel to run in the opposite direction, the LFO should only modulate the speed of the direction it is the wheel is currently turning.

Thank you for clarifying these critical aspects of your design. I now have a much clearer understanding of how the system should work:
1. Master Time and Speed Relationship:
Master Time (in seconds) = time for one full wheel rotation at speed 1.0
At wheel speed 1.0, the wheel makes exactly 1 rotation in Master Time seconds
At wheel speed 10.0, the wheel completes 1/10 rotation in Master Time seconds (slower)
At wheel speed 0.1, the wheel completes 10 rotations in Master Time seconds (faster)
This is an inverse relationship where higher values = slower speeds, which is intuitive for your application.
2. Speed to Steps/Second Conversion:
Steps per wheel rotation = 600 (200 motor steps × 3 gear ratio)
For wheel speed S and master time M:
Steps per second = (Steps per rotation) ÷ (M × S)
Example: At speed 10.0 and master time 1.0, steps/sec = 600 ÷ (1.0 × 10.0) = 60 steps/sec
3. LFO Implementation:
LFO Rate follows the same scale as wheel speed:
Rate 1.0 = 1 complete oscillation cycle in Master Time seconds
Rate 10.0 = 1/10 oscillation cycle in Master Time seconds (slower)
LFO Depth (0-100%) defines the amplitude of the oscillation as percentage of base speed
For UNI polarity:
Speed varies between base speed and base speed + (depth% × base speed)
Example: With base speed 10.0 and depth 50%, speed oscillates between 10.0 and 15.0
For BI polarity:
Speed varies between base speed - (depth% × base speed) and base speed + (depth% × base speed)
Example: With base speed 10.0 and depth 50%, speed oscillates between 5.0 and 15.0
This approach ensures that in UNI mode, the wheel never reverses direction.
With this understanding, I can now proceed to implement the Arduino code for your system. I'll include the necessary conversions and calculations to ensure the motors follow these specifications precisely.
