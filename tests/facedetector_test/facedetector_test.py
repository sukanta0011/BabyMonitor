import cv2
import numpy as np
import sys

IMAGE_PATH = sys.argv[1] if len(sys.argv) > 1 else "test_frames/test.png"


def enhance_contrast(image: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_enhanced = clahe.apply(l)

    enhanced_lab = cv2.merge((l_enhanced, a, b))
    return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)


def draw_and_save(image: np.ndarray, detections: list, output_path: str):
    annotated = image.copy()
    for x, y, w, h, score in detections:
        cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(annotated, f"{score:.3f}", (x, max(y - 8, 12)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    cv2.imwrite(output_path, annotated)
    print(f"Saved annotated image to {output_path}")


def test_yunet(image: np.ndarray):
    h, w = image.shape[:2]
    detector = cv2.FaceDetectorYN.create(
        model='face_detection_models/face_detection_yunet_2023mar.onnx',
        config='',
        input_size=(w, h),
        score_threshold=0.1,   # lowered from 0.6 to see borderline detections too
        nms_threshold=0.3,
        top_k=5000
    )
    _, faces = detector.detect(image)
    if faces is None:
        return []
    return [(int(f[0]), int(f[1]), int(f[2]), int(f[3]), float(f[14])) for f in faces]


def main():
    image = cv2.imread(IMAGE_PATH)
    if image is None:
        print(f"Could not load image at {IMAGE_PATH}")
        return

    print(f"Image size: {image.shape[1]}x{image.shape[0]}\n")

    print("--- YuNet ---")
    enhanced = enhance_contrast(image)
    yunet_results = test_yunet(enhanced)
    draw_and_save(enhanced, yunet_results, "test_frames/yunet_annotated.jpg")
    if not yunet_results:
        print("No face detected")
    for x, y, w, h, score in yunet_results:
        print(f"  box=({x},{y},{w},{h}) score={score:.3f}")

if __name__ == "__main__":
    main()