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