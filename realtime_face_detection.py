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
    for index, current_face_location in enumerate(all_face_locations):
        top_pos,right_pos,bottom_pos,left_pos = current_face_location
        top_pos= top_pos*4
        right_pos=right_pos*4
        bottom_pos=bottom_pos*4
        left_pos = left_pos*4
        print('Found face {} at top:{},right:{},bottom:{},left:{}'.format(index+1,top_pos,right_pos,bottom_pos,left_pos))