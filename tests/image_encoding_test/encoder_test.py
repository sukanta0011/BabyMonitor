import cv2

CAMERA_SOURCE = "http://192.168.1.105:81/stream"

QUALITIES_TO_TEST = [95, 80, 60, 50, 40, 30]


def main():
    cap = cv2.VideoCapture(CAMERA_SOURCE)
    if not cap.isOpened():
        print("Could not open camera source:", CAMERA_SOURCE)
        return

    ret, frame = cap.read()
    if not ret:
        print("Could not read a frame from the camera.")
        return

    print(f"Captured frame: {frame.shape[1]}x{frame.shape[0]}\n")
    print(f"{'Quality':>8} | {'Size (bytes)':>12}")
    print("-" * 25)

    for q in QUALITIES_TO_TEST:
        success, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, q])
        if success:
            print(f"{q:>8} | {len(buffer):>12}")
        else:
            print(f"{q:>8} | encode failed")

    cap.release()


if __name__ == "__main__":
    main()