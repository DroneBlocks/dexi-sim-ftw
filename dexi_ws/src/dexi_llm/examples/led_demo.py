#!/usr/bin/env python3
"""LED demo — cycles through colors and effects via the on-device LLM.

Each prompt is interpreted by the fine-tuned Llama model running on the Pi,
which translates natural language into the correct ROS 2 service call.

Usage:
    # Run full demo (colors + effects)
    python3 led_demo.py

    # Single prompt
    python3 led_demo.py make the led green
"""

import sys
import time

import rclpy
from rclpy.node import Node
from dexi_interfaces.srv import LLMChat

RAINBOW_PROMPTS = [
    "make the led red",
    "make the led orange",
    "make the led yellow",
    "make the led green",
    "make the led blue",
    "make the led purple",
]

EFFECT_PROMPTS = [
    "do the rainbow effect",
    "show me the meteor animation",
    "do the comet effect",
    "make the leds ripple",
    "galaxy effect",
    "show the loading effect",
    "blink red",
]

DELAY_BETWEEN = 5.0  # seconds between prompts


def call_llm(node, client, prompt: str) -> None:
    request = LLMChat.Request()
    request.prompt = prompt

    print(f"\n>>> \"{prompt}\"")
    t0 = time.monotonic()
    future = client.call_async(request)
    rclpy.spin_until_future_complete(node, future, timeout_sec=120.0)
    elapsed = time.monotonic() - t0

    if future.result() is not None:
        r = future.result()
        print(f"    Response: {r.response}")
        if r.commands_executed:
            print(f"    Commands: {list(r.commands_executed)}")
        print(f"    Time: {elapsed:.1f}s")
    else:
        print(f"    FAILED after {elapsed:.1f}s")


def main():
    rclpy.init()
    node = Node("led_demo_client")
    client = node.create_client(LLMChat, "/dexi/llm/llm_node/chat")

    print("Waiting for LLM service...")
    if not client.wait_for_service(timeout_sec=10.0):
        print("Service not available")
        return

    if len(sys.argv) > 1:
        # Single prompt mode
        call_llm(node, client, " ".join(sys.argv[1:]))
    else:
        # Full demo: colors then effects
        all_prompts = RAINBOW_PROMPTS + EFFECT_PROMPTS + ["turn off the leds"]
        print(f"Running LED demo ({len(all_prompts)} prompts, {DELAY_BETWEEN}s delay)")
        t_total = time.monotonic()

        print("\n--- Colors ---")
        for i, prompt in enumerate(RAINBOW_PROMPTS):
            call_llm(node, client, prompt)
            print(f"    Waiting {DELAY_BETWEEN}s...")
            time.sleep(DELAY_BETWEEN)

        print("\n--- Effects ---")
        for prompt in EFFECT_PROMPTS:
            call_llm(node, client, prompt)
            print(f"    Waiting {DELAY_BETWEEN}s...")
            time.sleep(DELAY_BETWEEN)

        call_llm(node, client, "turn off the leds")

        total = time.monotonic() - t_total
        print(f"\nDone! Total time: {total:.1f}s")

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
