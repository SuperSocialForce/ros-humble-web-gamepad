# ROS Humble Teleop On Mac With Browser Joy Bridge

Docker Desktop for Mac does not expose macOS game controllers as `/dev/input/js0`
inside Linux containers. If a browser gamepad tester can see the controller,
use the browser bridge:

- Mac browser: `web_gamepad_sender.html` reads the controller through the Gamepad API.
- ROS container: `scripts/http_joy_receiver.py` publishes `sensor_msgs/Joy` on `/joy`.
- `teleop_twist_joy` subscribes to `/joy` and publishes `/cmd_vel`.

## Build The Image

```bash
docker build -t ros:humble-teleop .
```

## Start The ROS Container

```bash
docker run --rm -it \
  --name humble-teleop-joy \
  -p 8000:8000 \
  ros:humble-teleop
```

Inside the container:

```bash
ros2 launch /usr/local/share/humble_teleop/browser_teleop.launch.py
```

In another terminal, verify `/joy`:

```bash
docker exec -it humble-teleop-joy bash -lc \
  'source /opt/ros/humble/setup.bash && ros2 topic echo /joy'
```

## Start The Browser Sender

On the Mac host, serve this directory over localhost:

```bash
python3 -m http.server 9000
```

Open `http://127.0.0.1:9000/web_gamepad_sender.html` in the same browser that
can see the controller, press a controller button, click `Scan`, then click
`Start`.

## Inspect Teleop Output

Inspect generated velocity commands:

```bash
docker exec -it humble-teleop-joy bash -lc \
  'source /opt/ros/humble/setup.bash && ros2 topic echo /cmd_vel'
```

If `/joy` works but `/cmd_vel` does not move, the controller button/axis mapping
does not match the default `teleop_twist_joy` configuration. Check the `/joy`
axis and button numbers, then pass a matching params file to the launch file:

```bash
ros2 launch /usr/local/share/humble_teleop/browser_teleop.launch.py \
  config_filepath:=/path/to/your.config.yaml
```

## Optional Pygame UDP Sender

If pygame can see your controller, this older path also works:

```bash
docker run --rm -it \
  --name humble-teleop-joy \
  -p 5005:5005/udp \
  ros:humble-teleop
```

Inside the container:

```bash
python3 /usr/local/bin/udp_joy_receiver.py
```

On the Mac host:

```bash
python3 -m pip install pygame
python3 scripts/mac_joy_sender.py --list
python3 scripts/mac_joy_sender.py --host 127.0.0.1 --port 5005
```
