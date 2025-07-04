import cv2
import dlib
import face_recognition
import os


print(cv2.__version__)
print(dlib.__version__)
print(face_recognition.__version__)

image_test = cv2.imread('images/trump-modhi.png')

if image_test is None:
    print(f"Error: Could not load image from {image_path}")
else:
    cv2.imshow("Image", image_test)
    cv2.waitKey(0)
    cv2.destroyAllWindows()