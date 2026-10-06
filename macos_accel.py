#!/usr/bin/env python3

# macOS-like pointer acceleration for libinput
# Author: fufexan <mihai@fufexan.net>
# Downloaded from https://gist.github.com/fufexan/e6bcccb7787116b8f9c31160fc8bc543 on 2026-01-18 by vivlim

# Uncomment matplotlib and the plot_curve definition and call to visualize the curve
import matplotlib.pyplot as plt
import sys
import os

# ===== PARAMETERS =====
sample_point_count = 20  # number of sample points to calculate
# factors for accelerated speeds
low = 0.1
mid = 0.01
high = 0.005

# ===== END PARAMETERS =====


def find_arg(arg):
    """Check if a specific argument was passed via command line."""
    for i in sys.argv:
        if i == arg:
            return True
    return False


if find_arg("help") or find_arg("-h") or find_arg("--help") or find_arg("h"):
    print(f"{sys.argv[0]} [[accel_profile] [scroll_points] device=<device>]")
    exit(0)


def macos_acceleration(speed_in):
    # Apply a cubic function to simulate acceleration
    return low * speed_in + mid * speed_in**2 + high * speed_in**3


# Generate points using the macOS-like curve function
def generate_curve_points(count):
    max_speed = 10  # Adjust the maximum speed as needed
    step = max_speed / count
    speeds = [step * i for i in range(count)]
    factors = [macos_acceleration(speed) for speed in speeds]
    return speeds, factors, step


# Plot the curve
def plot_curve(speeds, factors):
    plt.plot(speeds, factors, label="macOS-like Curve")
    plt.xlabel("Device Speed")
    plt.ylabel("Pointer Speed (Factor)")
    plt.legend(loc="best")
    plt.show()


# Generate the sample points
speeds, factors, step = generate_curve_points(sample_point_count)

# Display points as text (optional)
sample_points_str = " ".join([f"{factor:.3f}" for factor in factors])
print(f"Points: {sample_points_str}")
print(f"Step: {step}")


def get_device():
    for i in sys.argv:
        if str(i).startswith("device="):
            print(str(i)[7::])
            return str(i)[7::]


def hyprctl(device, option, arg):
    os.system(f"hyprctl keyword 'device[{device}]:{option}' '{arg}'")


if find_arg("accel_profile"):
    device = get_device()
    print(f"Setting device:'{device}':accel_profile using hyprctl")
    hyprctl(device, "accel_profile", f"custom {step} {sample_points_str}")

if find_arg("scroll_points"):
    device = get_device()
    print(f"Setting device:'{device}':scroll_points using hyprctl")
    hyprctl(device, "scroll_points", f"{step} {sample_points_str}")

# Plot the generated curve
plot_curve(speeds, factors)
