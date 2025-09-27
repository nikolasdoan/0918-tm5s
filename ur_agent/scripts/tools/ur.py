#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  Copyright (c) 2024. Jet Propulsion Laboratory. All rights reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import rclpy
import rclpy.publisher
from langchain.agents import tool
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from typing import List
from sensor_msgs.msg import JointState
import threading
import time 
from geometry_msgs.msg import Pose, PoseStamped

_shared_node = None
joint_traj_publisher = None
current_joint_states = None
cartesian_motion_client = None
joint_states_received = False 
cartesian_motion_client = None
current_ef_pose = None
controller_switcher_client = None


def initialize_node():
    global _shared_node, joint_traj_publisher, cartesian_motion_client,current_ef_pose, controller_switcher_client
    if _shared_node is None:
        print("Initializing ROS node and starting spin thread...")
        rclpy.init()
        _shared_node = rclpy.create_node('ur_agent_node')
        joint_traj_publisher = _shared_node.create_publisher(JointTrajectory, '/tmr_arm_controller/joint_trajectory', 10)
        _shared_node.create_subscription(JointState, '/joint_states', joint_state_callback, 10)

        def spin_node():
            try:
                rclpy.spin(_shared_node)
            except Exception as e:
                print(f"Error in spin thread: {e}")
                rclpy.shutdown()
        # Start spinning the node in a background thread
        spin_thread = threading.Thread(target=spin_node, daemon=True)
        spin_thread.start()
        print("Spin thread started.")


def joint_state_callback(msg):
    global current_joint_states,joint_states_received
    current_joint_states = list(msg.position)
    joint_states_received = True

def pose_callback(msg):
    global current_ef_pose
    current_ef_pose = msg
    
@tool
def publish_joint_positions(joint_positions: List[float], duration_sec: int = 5) -> str:
    """
        Publishes a `JointTrajectory` to command the TM robot joints to specified positions.
        Critical: ensure tmr_arm_controller is active.
        
        :param joint_positions: List of up to six joint positions in radians.
        :param duration_sec: Motion duration in seconds (default: 5).
        :return: Success message or error details.

    """
    global _shared_node, joint_traj_publisher, current_joint_states
    initialize_node()

    print("Waiting for joint states to be available...")

    try:
        
        print("tmr_arm_controller is active.")

        # Timeout for waiting for joint states
        timeout = 10  # seconds
        start_time = time.time()

        while current_joint_states is None:
            rclpy.spin_once(_shared_node, timeout_sec=0.1)
            if time.time() - start_time > timeout:
                return "Error: Timed out waiting for joint states to become available."
            
        print("Current joint states are initialized. Testing publish_joint_positions...")
        # Validate input length
        if len(joint_positions) > 6:
            return "Error: Too many joint positions provided. Expected at most 6."

        # Handle uninitialized current_joint_states
        if current_joint_states is None:
            return "Error: Current joint states are not initialized yet. Wait for /joint_states messages."

        # Retrieve current joint states for unspecified joints
        full_joint_positions = current_joint_states[:]
        for i, pos in enumerate(joint_positions):
            full_joint_positions[i] = pos  # Update specified positions

        # Prepare the message
        trajectory_msg = JointTrajectory()
        trajectory_msg.header.stamp = _shared_node.get_clock().now().to_msg()
        trajectory_msg.joint_names = [
            "joint_1",
            "joint_2",
            "joint_3",
            "joint_4",
            "joint_5",
            "joint_6",
        ]

        # Create a trajectory point
        point = JointTrajectoryPoint()
        point.positions = full_joint_positions
        point.time_from_start.sec = duration_sec
        trajectory_msg.points.append(point)

        # Publish the trajectory message
        joint_traj_publisher.publish(trajectory_msg)

        result = f"Published joint trajectory: {joint_positions} over {duration_sec} seconds."
        # Confirm execution
        return(result)

    except Exception as e:
        error_msg = f"Failed to publish joint trajectory: {e}"
        return error_msg

@tool
def retrieve_joint_states() -> str:
    """
        Retrieves the current joint states of the TM robot.

        :return: Joint states as a formatted string or an error message.
    """
    global _shared_node, current_joint_states, joint_states_received
    initialize_node()
    print("Waiting for joint states to be available...")
    try:
        timeout = 10  # seconds
        start_time = time.time()

        # Wait for the current_joint_states to be initialized
        while not joint_states_received:
            rclpy.spin_once(_shared_node, timeout_sec=0.1)
            if time.time() - start_time > timeout:
                return "Error: Timed out waiting for joint states to become available."
       
        # Spin to ensure the latest joint state message is processed
        for _ in range(3):  # Spin multiple times to avoid timing issues
            rclpy.spin_once(_shared_node, timeout_sec=0.1)
        
        # Format the joint states as a string for return
        joint_states_str = ", ".join([f"{state:.4f}" for state in current_joint_states])
        result = f"Current joint states: [{joint_states_str}]"
        print(result)
        return result

    except Exception as e:
        error_msg = f"Error retrieving joint states: {e}"
        print(error_msg)
        return error_msg

@tool
def activate_controller_request(controller_name: str) -> str:
    """
        Not supported for TM robots via this agent.

        :param controller_name: Ignored.
        :return: Informational message.
    """
    return "Not supported: TM uses controller_manager with tmr_arm_controller; dynamic switching not provided here."
    

@tool
def cartesian_motion_request(x: float, y: float, z: float) -> str:
    """
        Not supported for TM robots via this agent (no TM cartesian controller wired).

        :param x: Ignored.
        :param y: Ignored.
        :param z: Ignored.
        :return: Informational message.
    """
    return "Not supported: TM cartesian motion is not configured in this agent."
    
@tool
def get_current_pose() -> str:
    """
        Not supported for TM robots via this agent (no TM cartesian controller wired).

        :return: Informational message.
    """
    return "Not supported: TM cartesian pose topic is not configured in this agent."
