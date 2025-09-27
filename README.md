# ROSA TM Agent (LLM-driven control for TM robots)

This document explains how we adapted the existing UR-focused ROSA agent to control a TM robot using the TM MoveIt stack. It covers the changes we made, how to run the system, expected topics/actions, and troubleshooting tips.

## Overview
- Original agent targeted UR robots and UR-specific controllers/services.
- We refocused the agent on TM robots using MoveIt + ros2_control:
  - Controller: `tmr_arm_controller` (JointTrajectoryController)
  - Command topic: `/tmr_arm_controller/joint_trajectory`
  - Action server: `/tmr_arm_controller/follow_joint_trajectory`
- We removed UR-only dependencies (e.g., controller switching and custom cartesian services) and aligned joint naming.

## What changed (code edits)
All paths below are under `tm2_ros2-humble/src/llm-tm-control/ur_agent/`.

- `scripts/tools/ur.py`
  - Publisher topic changed to TM controller:
    - From `/scaled_joint_trajectory_controller/joint_trajectory`
    - To `/tmr_arm_controller/joint_trajectory`
  - Joint names updated to TM:
    - From `shoulder_pan_joint, shoulder_lift_joint, elbow_joint, wrist_1_joint, wrist_2_joint, wrist_3_joint`
    - To `joint_1, joint_2, joint_3, joint_4, joint_5, joint_6`
  - Joint state callback ordering fixed for TM:
    - Removed the rotation of the last position to the front; now uses `list(msg.position)` as-is.
  - UR-only tools disabled (return NotSupported messages):
    - `activate_controller_request` (UR custom controller switching)
    - `cartesian_motion_request` and `get_current_pose` (UR custom cartesian service / topic)

- `scripts/ur_agent.py`
  - Blacklisted UR-only tools so the agent will not attempt to call them:
    - `activate_controller_request`, `cartesian_motion_request`, `get_current_pose`
  - Examples updated to reflect TM usage (joint control, status checks).
  - Greeting updated to “ROSA-TM agent”.

- `scripts/prompts.py`
  - Persona updated to TM robot (e.g., TM5S).
  - Critical instructions updated to use `tmr_arm_controller`.
  - Joint list updated to `joint_1..joint_6`.
  - Capabilities updated (no controller-switch/cartesian services).

## What we did NOT change
- We did not modify the TM MoveIt packages themselves beyond using their existing launch/config files.
- We did not add a TM cartesian controller or a controller switching service. The agent focuses on joint-space control via JointTrajectory.

## TM stack components (for reference)
- Launch file (example TM5S): `tm_moveit/tm5s_moveit_config/launch/tm5s_moveit.launch.py`
  - Starts: `move_group`, `robot_state_publisher`, RViz, `controller_manager` (`ros2_control_node`), `joint_state_broadcaster`, `tmr_arm_controller`, and `tm_driver`.
- Controller config: `tm_moveit/tm5s_moveit_config/config/ros2_controllers.yaml`
  - Defines `tmr_arm_controller` (position command interface) and `joint_state_broadcaster`.

## How to run
1) Launch the TM MoveIt stack (replace `tm5s` with your model if needed):
```bash
source /home/asrlab/tm2_ros2-humble/install/setup.bash
ros2 launch tm5s_moveit_config tm5s_moveit.launch.py
```

2) Start the agent (from source):
```bash
source /home/asrlab/tm2_ros2-humble/install/setup.bash
python3 /home/asrlab/tm2_ros2-humble/src/llm-tm-control/ur_agent/scripts/ur_agent.py
```
- If you prefer `ros2 run`, rebuild only the agent package and run:
```bash
cd /home/asrlab/tm2_ros2-humble
colcon build --packages-select ur_agent
source install/setup.bash
ros2 run ur_agent ur_agent.py
```

3) Interact with the agent (examples):
- “Move joint 4 to 90 degrees” → agent converts to radians and publishes a `JointTrajectory` to `/tmr_arm_controller/joint_trajectory`.
- “Read current joint states” → agent echoes from `/joint_states`.

## Verify the system
- Controllers:
```bash
ros2 control list_controllers | cat
# Expect: tmr_arm_controller [active], joint_state_broadcaster [active]
```
- Command topic/action:
```bash
ros2 topic list | grep tmr_arm_controller | cat
# /tmr_arm_controller/joint_trajectory

ros2 action list | grep follow_joint_trajectory | cat
# /tmr_arm_controller/follow_joint_trajectory
```
- States and TFs used by RViz/MoveIt:
```bash
ros2 topic echo /joint_states | head -n 5 | cat
```

## RViz notes
The TM MoveIt launch starts RViz with a MoveIt view. If you don’t see motion:
- Ensure `robot_state_publisher` is running (it is part of `tm5s_moveit.launch.py`).
- Ensure joint names match (we updated the agent to TM’s `joint_1..joint_6`).
- Confirm the controller sees the commands:
```bash
ros2 topic echo /tmr_arm_controller/state | head -n 20 | cat
```

## What not to run for TM
- Do not launch the UR agent services launch for TM:
  - `ros2 launch ur_agent agent.launch.py` (starts UR-only services: cartesian and controller switcher)
- The TM integration does not need those services.

## Adapting for other TM models
- Use the matching MoveIt config launch:
  - `tm7s_moveit_config/launch/tm7s_moveit.launch.py`, `tm12s_moveit_config/...`, etc.
- Joint names remain `joint_1..joint_6`.

## Troubleshooting
- Agent still tries to switch controllers or references UR:
  - You might be running from the UR workspace or an older install. Start a fresh shell and source only TM, or source TM last:
    ```bash
    source /home/asrlab/0915-ur5/install/setup.bash
    source /home/asrlab/tm2_ros2-humble/install/setup.bash
    ```
- No motion in RViz but controllers active:
  - Check `/tmr_arm_controller/state` and `/joint_states`.
  - Ensure topic names and joint names match controller expectations.
- Cartesion motion needed:
  - Not included here. You can integrate a TM-compatible cartesian controller and then re-enable/implement the agent tools accordingly.

## Acknowledgements
- Original UR agent and ROSA framework code.
- TM MoveIt configuration packages for model-specific launches and controllers.

---
If you need this agent to support additional TM features (cartesian control, IO, etc.), we can extend the toolset and launch flows accordingly.
