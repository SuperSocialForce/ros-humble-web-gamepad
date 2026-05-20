#!/usr/bin/env python3
import argparse
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy


DEFAULT_STATIC_FILE = "/usr/local/share/humble_teleop/web_gamepad_sender.html"


class JoyRequestHandler(BaseHTTPRequestHandler):
    server_version = "HttpJoyReceiver/1.0"

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        self.handle_get_or_head(send_body=True)

    def do_HEAD(self):
        self.handle_get_or_head(send_body=False)

    def handle_get_or_head(self, send_body):
        path = urlsplit(self.path).path
        if path == "/health":
            self.send_json(200, {"ok": True}, send_body=send_body)
            return

        if path in ("/", "/web_gamepad_sender.html"):
            self.send_static_html(send_body=send_body)
            return

        self.send_json(404, {"ok": False, "error": "not found"}, send_body=send_body)

    def do_POST(self):
        if urlsplit(self.path).path != "/joy":
            self.send_json(404, {"ok": False, "error": "not found"})
            return

        content_length = self.headers.get("Content-Length")
        if content_length is None:
            self.send_json(411, {"ok": False, "error": "missing content-length"})
            return

        try:
            body_length = int(content_length)
        except ValueError:
            self.send_json(400, {"ok": False, "error": "invalid content-length"})
            return

        if body_length > self.server.receiver_node.max_body_bytes:
            self.send_json(413, {"ok": False, "error": "request body too large"})
            return

        try:
            payload = json.loads(self.rfile.read(body_length).decode("utf-8"))
            axes = [float(value) for value in payload["axes"]]
            buttons = [int(value) for value in payload["buttons"]]
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
            return

        self.server.receiver_node.update_joy_state(axes, buttons)
        self.send_json(200, {"ok": True})

    def send_static_html(self, send_body=True):
        try:
            body = Path(self.server.receiver_node.static_file).read_bytes()
        except OSError:
            self.send_json(404, {"ok": False, "error": "static file not found"}, send_body=send_body)
            return

        self.send_response(200)
        self.send_cors_headers()
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if send_body:
            self.wfile.write(body)

    def send_json(self, status, payload, send_body=True):
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if send_body:
            self.wfile.write(body)

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, _format, *_args):
        return


class HttpJoyReceiver(Node):
    def __init__(self, args):
        super().__init__("http_joy_receiver")
        self.frame_id = args.frame_id
        self.stale_timeout = args.stale_timeout
        self.max_body_bytes = args.max_body_bytes
        self.static_file = args.static_file
        self.lock = threading.Lock()
        self.latest_axes = None
        self.latest_buttons = None
        self.last_packet_time = None
        self.sent_stale_zero = True

        self.publisher = self.create_publisher(Joy, args.topic, 10)
        self.publish_timer = self.create_timer(1.0 / args.publish_rate, self.publish_latest)

        self.httpd = ThreadingHTTPServer((args.bind_address, args.port), JoyRequestHandler)
        self.httpd.receiver_node = self
        self.http_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.http_thread.start()

        self.get_logger().info(
            f"listening for HTTP Joy packets on http://{args.bind_address}:{args.port}/joy, "
            f"serving browser sender on /, publishing {args.topic}"
        )

    def destroy_node(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.http_thread.join(timeout=1.0)
        super().destroy_node()

    def update_joy_state(self, axes, buttons):
        with self.lock:
            self.latest_axes = axes
            self.latest_buttons = buttons
            self.last_packet_time = time.monotonic()
            self.sent_stale_zero = False

    def publish_latest(self):
        with self.lock:
            if self.latest_axes is None or self.latest_buttons is None:
                return

            elapsed = time.monotonic() - self.last_packet_time
            if elapsed >= self.stale_timeout:
                if self.sent_stale_zero:
                    return

                axes = [0.0] * len(self.latest_axes)
                buttons = [0] * len(self.latest_buttons)
                self.sent_stale_zero = True
            else:
                axes = list(self.latest_axes)
                buttons = list(self.latest_buttons)

        self.publish_joy(axes, buttons)

    def publish_joy(self, axes, buttons):
        message = Joy()
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = self.frame_id
        message.axes = axes
        message.buttons = buttons
        self.publisher.publish(message)


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Receive Joy state from a browser Gamepad API page and publish sensor_msgs/Joy."
    )
    parser.add_argument("--bind-address", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--topic", default="/joy")
    parser.add_argument("--frame-id", default="joy")
    parser.add_argument("--publish-rate", type=float, default=50.0)
    parser.add_argument("--stale-timeout", type=float, default=0.5)
    parser.add_argument("--max-body-bytes", type=int, default=65536)
    parser.add_argument("--static-file", default=DEFAULT_STATIC_FILE)
    return parser.parse_known_args(argv)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    args, ros_args = parse_args(argv)
    if args.publish_rate <= 0:
        print("--publish-rate must be greater than zero", file=sys.stderr)
        return 2

    rclpy.init(args=ros_args)
    node = HttpJoyReceiver(args)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
