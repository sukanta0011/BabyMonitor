import cv2
# import numpy as np
import time

INPUT_PATH = ("/home/sukanta/42Prague/SideProject/"
             "BabyMonitor/test_frames/night_vision_frame.png")
OUTPUT_PATH = "frame_enhanced_v3.jpg"

def enhance_low_light_contrast(frame):
    t0 = time.perf_counter()

    # 1. Grayscale (ESP32-CAM night vision has zero useful color data)
    if len(frame.shape) == 3:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        gray = frame.copy()

    # 2. Stretch Histogram to use the full 0-255 range (Min-Max Normalization)
    # Often ESP32 night frames only occupy values between 20 and 110.
    min_val, max_val, _, _ = cv2.minMaxLoc(gray)
    if max_val - min_val > 10:
        stretched = cv2.normalize(
            gray, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
    else:
        stretched = gray

    # 3. Two-Tier CLAHE
    # First pass: large tile size for
    # global light balance (fixes the hot IR spot on the left)
    clahe_broad = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(16, 16))
    broad_eq = clahe_broad.apply(stretched)

    # Second pass: small tile size for local fabric/crib edges
    clahe_local = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(6, 6))
    local_eq = clahe_local.apply(broad_eq)

    # 4. Edge-Aware High-Pass Sharpening (doesn't boost background noise)
    # Bilateral blur isolates flat surfaces vs sharp edges
    smooth = cv2.bilateralFilter(local_eq, d=7, sigmaColor=40, sigmaSpace=40)
    # The difference (high-frequency components only)
    high_freq = cv2.subtract(local_eq, smooth)

    # Re-inject high frequencies with a scaling factor
    enhanced = cv2.addWeighted(local_eq, 1.0, high_freq, 1.5, 0)

    t1 = time.perf_counter()
    print(f"Enhancement time: {(t1 - t0) * 1000:.2f} ms")

    return enhanced

def main():
    frame = cv2.imread(INPUT_PATH)
    if frame is None:
        print(f"Could not load {INPUT_PATH}")
        return

    result = enhance_low_light_contrast(frame)
    cv2.imwrite(OUTPUT_PATH, result)
    print(f"Saved optimized output to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
