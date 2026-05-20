FROM ros:humble

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ros-humble-teleop-twist-joy \
    && rm -rf /var/lib/apt/lists/*

COPY ros_entrypoint.sh /ros_entrypoint.sh
COPY scripts/http_joy_receiver.py /usr/local/bin/http_joy_receiver.py
COPY launch/browser_teleop.launch.py /usr/local/share/humble_teleop/browser_teleop.launch.py
COPY web_gamepad_sender.html /usr/local/share/humble_teleop/web_gamepad_sender.html
RUN chmod +x /ros_entrypoint.sh /usr/local/bin/http_joy_receiver.py

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["bash"]
