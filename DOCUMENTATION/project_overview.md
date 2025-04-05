# Cycloid Machine Project Overview

## Introduction

The Cycloid Machine is a specialized drawing device designed to create complex geometric patterns known as cycloids. These patterns are created through the coordinated movement of multiple wheels rotating at different speeds, with a pen or drawing implement that traces the resulting compound motion.

## Concept

The machine operates on principles similar to a harmonograph, spirograph, or other cycloid-drawing instruments:

1. Multiple wheels (X, Y, Z, and A) rotate at different speeds and relationships
2. A pen holder is attached to a system of rods connected to these wheels
3. As the wheels rotate, the pen traces out complex patterns that would be impossible to draw by hand
4. By adjusting the speed ratios, LFO (Low-Frequency Oscillator) parameters, and other settings, different patterns can be created

## Project Components

The project consists of several key components:

1. **Mechanical Systems**:
   - Frame assembly using aluminum extrusion rails
   - Drive wheel assemblies with stepper motors, pulleys, and belts
   - Platen (drawing surface) assembly
   - Rod and pen holder assembly

2. **Control Systems**:
   - Arduino-based controller for driving stepper motors
   - LCD interface and rotary encoder for user input
   - Comprehensive menu system for adjusting parameters

3. **Software**:
   - Arduino firmware (to be implemented)
   - Python simulator for the LCD menu interface

## Project Goals

The goals of this project include:

1. Creating a versatile drawing machine capable of producing a wide variety of cycloid patterns
2. Providing an intuitive user interface for controlling the machine
3. Allowing for fine adjustment of drawing parameters through the menu system
4. Creating a modular design that can be expanded or modified

## Inspiration

The project draws inspiration from similar drawing machines and cycloid generators:
- Commercial products like the Hypnograph
- DIY projects such as the Cycloid-o-matic
- Artists and makers like Robert Balke and Alfred Hoehn

## Current Status

The project is currently in the design and early implementation phase:
- Hardware specifications and BOM are defined
- Menu system is designed and simulated
- Arduino pin mappings are specified
- Core Arduino code for motor control is pending 