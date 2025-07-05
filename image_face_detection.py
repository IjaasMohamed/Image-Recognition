# -*- coding: utf-8 -*-
"""
Created on Sat Jul  5 19:41:49 2025

@author: USER
"""

import cv2
import face_recognition

image_to_detect = cv2.imread('images/trump-modhi.png')

all_face_locations = face_recognition.face_locations(image_to_detect, model='hog')

print('There are {} no of faces in this image'.format(len(all_face_locations)))

for index, current_face_location in enumerate(all_face_locations):
    top_pos,right_pos,bottom_pos,left_pos = current_face_location
    print("Found face {} at top:{}, right:{}, bottom:{}, left:{}".format(index+1, top_pos,right_pos,bottom_pos,left_pos))
    current_face_image = image_to_detect[top_pos:bottom_pos,left_pos:right_pos]
    cv2.imshow("Face No "+ str(index+1),current_face_image)