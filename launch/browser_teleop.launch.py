from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    bind_address = LaunchConfiguration("bind_address")
    http_port = LaunchConfiguration("http_port")
    joy_topic = LaunchConfiguration("joy_topic")
    cmd_vel_topic = LaunchConfiguration("cmd_vel_topic")
    config_filepath = LaunchConfiguration("config_filepath")

    default_config_filepath = PathJoinSubstitution(
        [
            FindPackageShare("teleop_twist_joy"),
            "config",
            "xbox.config.yaml",
        ]
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "bind_address",
                default_value="0.0.0.0",
                description="HTTP bind address for browser Joy packets.",
            ),
            DeclareLaunchArgument(
                "http_port",
                default_value="8000",
                description="HTTP port for browser Joy packets.",
            ),
            DeclareLaunchArgument(
                "joy_topic",
                default_value="/joy",
                description="Joy topic published by the HTTP bridge.",
            ),
            DeclareLaunchArgument(
                "cmd_vel_topic",
                default_value="/cmd_vel",
                description="Twist command topic published by teleop_twist_joy.",
            ),
            DeclareLaunchArgument(
                "config_filepath",
                default_value=default_config_filepath,
                description="teleop_twist_joy YAML config path.",
            ),
            ExecuteProcess(
                cmd=[
                    "python3",
                    "/usr/local/bin/http_joy_receiver.py",
                    "--bind-address",
                    bind_address,
                    "--port",
                    http_port,
                    "--topic",
                    joy_topic,
                ],
                name="http_joy_receiver",
                output="screen",
            ),
            Node(
                package="teleop_twist_joy",
                executable="teleop_node",
                name="teleop_twist_joy_node",
                output="screen",
                parameters=[config_filepath],
                remappings=[
                    ("joy", joy_topic),
                    ("cmd_vel", cmd_vel_topic),
                ],
            ),
        ]
    )
