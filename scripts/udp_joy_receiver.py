#!/usr/bin/env python3
import argparse
import json
import socket
import sys
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy


class UdpJoyReceiver(Node):
    def __init__(self, args):
        super().__init__("udp_joy_receiver")
        self.frame_id = args.frame_id
        self.stale_timeout = args.stale_timeout
        self.last_packet_time = None
        self.last_axis_count = 0
        self.last_button_count = 0
        self.sent_stale_zero = True

        self.publisher = self.create_publisher(Joy, args.topic, 10)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((args.bind_address, args.port))
        self.sock.setblocking(False)

        self.timer = self.create_timer(0.01, self.poll_socket)
        self.get_logger().info(
            f"listening for UDP Joy packets on {args.bind_address}:{args.port}, "
            f"publishing {args.topic}"
        )

    def destroy_node(self):
        self.sock.close()
        super().destroy_node()

    def poll_socket(self):
        received_any = False

        while True:
            try:
                data, _address = self.sock.recvfrom(65535)
            except BlockingIOError:
                break

            received_any = True
            self.handle_packet(data)

        if not received_any:
            self.publish_stale_zero_if_needed()

    def handle_packet(self, data):
        try:
            payload = json.loads(data.decode("utf-8"))
            axes = [float(value) for value in payload["axes"]]
            buttons = [int(value) for value in payload["buttons"]]
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            self.get_logger().warn(f"ignored invalid UDP Joy packet: {exc}")
            return

        self.last_packet_time = time.monotonic()
        self.last_axis_count = len(axes)
        self.last_button_count = len(buttons)
        self.sent_stale_zero = False

        self.publish_joy(axes, buttons)

    def publish_stale_zero_if_needed(self):
        if self.last_packet_time is None or self.sent_stale_zero:
            return

        elapsed = time.monotonic() - self.last_packet_time
        if elapsed < self.stale_timeout:
            return

        self.publish_joy(
            [0.0] * self.last_axis_count,
            [0] * self.last_button_count,
        )
        self.sent_stale_zero = True

    def publish_joy(self, axes, buttons):
        message = Joy()
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = self.frame_id
        message.axes = axes
        message.buttons = buttons
        self.publisher.publish(message)


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Receive UDP packets from mac_joy_sender.py and publish sensor_msgs/Joy."
    )
    parser.add_argument("--bind-address", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5005)
    parser.add_argument("--topic", default="/joy")
    parser.add_argument("--frame-id", default="joy")
    parser.add_argument(
        "--stale-timeout",
        type=float,
        default=0.5,
        help="Seconds without UDP packets before publishing one zeroed Joy message",
    )
    return parser.parse_known_args(argv)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    args, ros_args = parse_args(argv)

    rclpy.init(args=ros_args)
    node = UdpJoyReceiver(args)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
