#!/usr/bin/env python3
import argparse
import json
import socket
import sys
import time


def parse_args():
    parser = argparse.ArgumentParser(
        description="Read a Mac game controller with pygame and send Joy state over UDP."
    )
    parser.add_argument("--host", default="127.0.0.1", help="UDP receiver host")
    parser.add_argument("--port", type=int, default=5005, help="UDP receiver port")
    parser.add_argument("--rate", type=float, default=50.0, help="Send rate in Hz")
    parser.add_argument(
        "--device-index",
        type=int,
        default=0,
        help="pygame joystick index to use",
    )
    parser.add_argument(
        "--deadzone",
        type=float,
        default=0.05,
        help="Axis values with absolute value below this are sent as 0",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List detected controllers and exit",
    )
    return parser.parse_args()


def load_pygame():
    try:
        import pygame
    except ImportError:
        print(
            "pygame is required on the Mac host. Install it with: python3 -m pip install pygame",
            file=sys.stderr,
        )
        return None

    return pygame


def apply_deadzone(value, deadzone):
    return 0.0 if abs(value) < deadzone else float(value)


def list_joysticks(pygame):
    count = pygame.joystick.get_count()
    if count == 0:
        print("No controllers detected.")
        return

    for index in range(count):
        joystick = pygame.joystick.Joystick(index)
        joystick.init()
        print(
            f"{index}: {joystick.get_name()} "
            f"axes={joystick.get_numaxes()} "
            f"buttons={joystick.get_numbuttons()} "
            f"hats={joystick.get_numhats()}"
        )


def read_payload(joystick, deadzone, sequence):
    axes = [
        apply_deadzone(joystick.get_axis(index), deadzone)
        for index in range(joystick.get_numaxes())
    ]

    # ROS Joy has only axes and buttons. pygame hats are appended as extra axes:
    # each hat contributes x, y values in the range -1, 0, 1.
    for index in range(joystick.get_numhats()):
        x_value, y_value = joystick.get_hat(index)
        axes.extend([float(x_value), float(y_value)])

    buttons = [
        int(joystick.get_button(index))
        for index in range(joystick.get_numbuttons())
    ]

    return {
        "version": 1,
        "sequence": sequence,
        "timestamp": time.time(),
        "name": joystick.get_name(),
        "axes": axes,
        "buttons": buttons,
    }


def main():
    args = parse_args()
    if args.rate <= 0:
        print("--rate must be greater than zero", file=sys.stderr)
        return 2

    pygame = load_pygame()
    if pygame is None:
        return 1

    pygame.init()
    pygame.joystick.init()

    if args.list:
        list_joysticks(pygame)
        return 0

    joystick_count = pygame.joystick.get_count()
    if joystick_count == 0:
        print("No controllers detected. Connect or pair one, then retry.", file=sys.stderr)
        return 1

    if args.device_index < 0 or args.device_index >= joystick_count:
        print(
            f"--device-index {args.device_index} is out of range. "
            f"Detected {joystick_count} controller(s).",
            file=sys.stderr,
        )
        return 1

    joystick = pygame.joystick.Joystick(args.device_index)
    joystick.init()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    target = (args.host, args.port)
    interval = 1.0 / args.rate
    sequence = 0

    print(
        f"Sending {joystick.get_name()} to udp://{args.host}:{args.port} "
        f"at {args.rate:g} Hz"
    )

    try:
        while True:
            pygame.event.pump()
            payload = read_payload(joystick, args.deadzone, sequence)
            sock.sendto(
                json.dumps(payload, separators=(",", ":")).encode("utf-8"),
                target,
            )
            sequence += 1
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0
    finally:
        sock.close()
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
