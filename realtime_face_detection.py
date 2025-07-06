# -*- coding: utf-8 -*-
"""
Created on Sun Jul  6 16:39:07 2025

@author: acer
"""

import cv2
import face_recognition

webcam_vedio_stream = cv2.VideoCapture(0)

all_face_locations = []

while True:
    ret, current_frame = webcam_vedio_stream.read()
    current_frame_small = cv2.resize(current_frame, (0,0),fx=0.25, fy=0.25) #resize to speed
    all_face_locations = face_recognition.face_locations(image_to_detect, model='hog')