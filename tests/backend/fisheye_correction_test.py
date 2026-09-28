import time
import cv2
import numpy as np

INPUT_PATH = "/home/sukanta/42Prague/SideProject/BabyMonitor/test_frames/night_vision_frame.png"
OUTPUT_PATH = "frame_160_corrected.jpg"


class Fisheye160Corrector:

    def __init__(self, width, height, balance=0.5):
        """balance: 0.0 retains only the undistorted center (maximum crop).

        1.0 retains all pixels (leaves black borders around edges).
        0.4 - 0.6 is usually optimal for baby cribs.
        """
        self.w = width
        self.h = height

        # 1. Focal length approximation for 160° FOV:
        # For a full 160° field of view, focal length f ≈ width / (2 * sin(FOV/2)) or roughly w * 0.4 to 0.5
        f = self.w * 0.5
        cx = self.w / 2.0
        cy = self.h / 2.0

        self.K = np.array(
            [[f, 0.0, cx], [0.0, f, cy], [0.0, 0.0, 1.0]], dtype=np.float64
        )

        # Typical radial distortion coefficients (k1, k2, k3, k4) for a 160° M12/OV2640 lens
        self.D = np.array([[-0.08], [0.04], [-0.02], [0.005]], dtype=np.float64)

        # 2. Compute the new camera matrix accounting for FOV scale (balance parameter)
        new_K = cv2.fisheye.estimateNewCameraMatrixForUndistortRectify(
            self.K, self.D, (self.w, self.h), np.eye(3), balance=balance
        )

        # 3. Precompute undistortion and rectification transformation map
        # CV_16SC2 format yields the fastest execution during cv2.remap on ARM CPUs
        self.map1, self.map2 = cv2.fisheye.initUndistortRectifyMap(
            self.K, self.D, np.eye(3), new_K, (self.w, self.h), cv2.CV_16SC2
        )

    def process(self, frame):
        # Extremely fast: just memory lookups using the precalculated mapping
        return cv2.remap(
            frame,
            self.map1,
            self.map2,
            interpolation=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
        )


def main():
    frame = cv2.imread(INPUT_PATH)
    if frame is None:
        print(f"Could not load image at {INPUT_PATH}")
        return

    h, w = frame.shape[:2]
    print(f"Loaded frame: {w}x{h}")

    # Initialization & pre-calculation benchmark (Done ONCE)
    t0 = time.perf_counter()
    corrector = Fisheye160Corrector(width=w, height=h, balance=0.5)
    t_init = (time.perf_counter() - t0) * 1000

    # Real-time remap benchmark (Done EVERY frame)
    t1 = time.perf_counter()
    corrected_frame = corrector.process(frame)
    t_remap = (time.perf_counter() - t1) * 1000

    print("\n--- Benchmark (160° Fisheye Correction) ---")
    print(f"One-time Map Generation: {t_init:6.2f} ms")
    print(f"Per-Frame Remap Cost:    {t_remap:6.2f} ms")
    print(f"Theoretical Max FPS:     {1000 / t_remap:6.1f} FPS\n")

    cv2.imwrite(OUTPUT_PATH, corrected_frame)
    print(f"Saved rectilinear frame to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()