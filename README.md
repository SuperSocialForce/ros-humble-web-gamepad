# ROS Humble Teleop With Browser Joy Bridge

This project avoids passing a physical gamepad device into the ROS container.
Instead, a browser on the host machine reads the controller through the Gamepad
API and sends the state to the ROS container over HTTP:

- Host browser: the page served by the ROS container reads the controller through
  the Gamepad API.
- ROS container: `scripts/http_joy_receiver.py` serves the browser page, receives
  browser POSTs on `/joy`, and publishes `sensor_msgs/Joy` on the ROS `/joy`
  topic.
- `teleop_twist_joy` subscribes to `/joy` and publishes `/cmd_vel`.

The browser sender normalizes the left stick vertical axis to the ROS Joy
convention: pushing the left stick up sends `axes[1] > 0`, matching the default
`teleop_twist_joy` configs.

## Build

```bash
docker build -t ros:humble-teleop .
```

## Run

```bash
docker run --rm -it \
  --name humble-teleop-joy \
  -p 8000:8000 \
  ros:humble-teleop
```

Inside the container, launch the HTTP Joy bridge and `teleop_twist_joy`:

```bash
ros2 launch /usr/local/share/humble_teleop/browser_teleop.launch.py
```

The launch starts one HTTP server on port `8000`:

- `GET /` serves the browser gamepad sender.
- `GET /health` returns a health check.
- `POST /joy` receives browser gamepad state.

## Open The Browser Sender

Open `http://127.0.0.1:8000/` in the same browser that can see the controller,
press a controller button, click `Scan`, then click `Start`.

## Verify

Check that the HTTP bridge is reachable from the host machine:

```bash
curl http://127.0.0.1:8000/health
```

In another terminal, verify incoming Joy messages:

```bash
docker exec -it humble-teleop-joy bash -lc \
  'source /opt/ros/humble/setup.bash && ros2 topic echo /joy'
```

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
