import socket
import json
import time
import binascii
import os
import argparse
from datetime import datetime

# === CONFIGURATION ===
MULTICAST_IP = "239.255.50.10"
UDP_PORT = 5010
OUTPUT_JSON_FILE = "dcsbios_data_test.json"

# === ARGUMENT PARSING ===
parser = argparse.ArgumentParser(description="DCS-BIOS UDP Capture Tool")
parser.add_argument("--output", type=str, default=OUTPUT_JSON_FILE, help="Output JSON file name")
parser.add_argument("--duration", type=float, help="Capture duration in seconds (default: capture until Ctrl+C)")
parser.add_argument("--max-frames", type=int, help="Maximum number of frames to capture")
args = parser.parse_args()

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# === SETUP SOCKET ===
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# Bind to the multicast port
sock.bind(("", UDP_PORT))

# Join multicast group
mreq = socket.inet_aton(MULTICAST_IP) + socket.inet_aton("0.0.0.0")
sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

print(f"[INFO] Listening for UDP packets on {MULTICAST_IP}:{UDP_PORT}")
print(f"[INFO] Output file: {args.output}")
if args.duration:
    print(f"[INFO] Capture duration: {args.duration:.1f} seconds")
if args.max_frames:
    print(f"[INFO] Max frames: {args.max_frames}")
print("⏳ Press Ctrl+C to stop and save.\n")

# === CAPTURE LOOP ===
frames = []
last_frame_time = None
start_time = time.perf_counter()
frame_count = 0

try:
    while True:
        # Check if duration limit reached
        if args.duration and (time.perf_counter() - start_time) >= args.duration:
            print(f"\n✅ Duration limit ({args.duration}s) reached")
            break

        # Check if max frames reached
        if args.max_frames and frame_count >= args.max_frames:
            print(f"\n✅ Max frames ({args.max_frames}) reached")
            break

        # Receive UDP packet
        data, addr = sock.recvfrom(4096)
        current_time = time.perf_counter()

        # Calculate timing since last frame
        if last_frame_time is None:
            timing = 0.0  # First frame has no delay
        else:
            timing = current_time - last_frame_time

        # Convert binary data to hex string
        hex_data = binascii.hexlify(data).decode('ascii')

        # Store frame
        frame = {
            "data": hex_data,
            "timing": timing
        }
        frames.append(frame)

        last_frame_time = current_time
        frame_count += 1

        # Print progress every 100 frames
        if frame_count % 100 == 0:
            elapsed = current_time - start_time
            print(f"📦 Captured {frame_count} frames in {elapsed:.1f}s ({frame_count/elapsed:.1f} fps)")

except KeyboardInterrupt:
    print(f"\n🛑 Capture stopped by user")

# === SAVE DATA ===
elapsed = time.perf_counter() - start_time
print(f"\n[INFO] Captured {len(frames)} frames in {elapsed:.1f}s")
if len(frames) > 0:
    avg_fps = len(frames) / elapsed
    print(f"[INFO] Average FPS: {avg_fps:.1f}")

    with open(args.output, "w") as f:
        json.dump(frames, f, indent=2)

    print(f"✅ Saved to {args.output}")

    # Calculate file size
    file_size = os.path.getsize(args.output)
    if file_size > 1024 * 1024:
        print(f"[INFO] File size: {file_size / (1024 * 1024):.2f} MB")
    else:
        print(f"[INFO] File size: {file_size / 1024:.2f} KB")
else:
    print("⚠️ No frames captured - file not saved")

sock.close()
