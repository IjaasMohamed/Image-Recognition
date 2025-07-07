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
    
    # Convert to RGB for face_recognition
    current_frame_rgb = cv2.cvtColor(current_frame_small, cv2.COLOR_BGR2RGB)
    all_face_locations = face_recognition.face_locations(current_frame_rgb, model='hog')
    
    for index, current_face_location in enumerate(all_face_locations):
        top_pos,right_pos,bottom_pos,left_pos = current_face_location
        # Scale back up since we used the small frame
        top_pos= top_pos*4
        right_pos=right_pos*4
        bottom_pos=bottom_pos*4
        left_pos = left_pos*4
        print('Found face {} at top:{},right:{},bottom:{},left:{}'.format(index+1,top_pos,right_pos,bottom_pos,left_pos))
        cv2.rectangle(current_frame, (left_pos,top_pos), (right_pos, bottom_pos),(0,0,255),2)
    
    # Move imshow OUTSIDE the loop
    cv2.imshow("Webcam Video", current_frame)
        
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    
webcam_vedio_stream.release()
cv2.destroyAllWindows()