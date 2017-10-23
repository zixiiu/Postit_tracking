from collections import deque
import numpy as np
import argparse
import imutils
import cv2
import time
import timeit
import datetime
import pyfttt
import logging


logging.basicConfig(filename='log.log',level=logging.DEBUG,format='%(asctime)s %(message)s')



#IFTTT ALART SETTINGS
api_key = "YOUR_API_KEY_HERE"
event = "motion_stopped"
push = False
#====================

ColorLower = (140, 50, 50)
ColorUpper = (180, 255, 255)
#HSV color, Hue=0-180, Sat=0-255, Val=0-255
pts = deque(maxlen=64) #points vari
camera = cv2.VideoCapture(1)
stopped = 0 #stop indicator
ref_center = None

logging.info("system start")

while True:
	(grabbed, frame) = camera.read()
	frame = imutils.resize(frame, width=800)


	#create mask for color
	hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
	mask = cv2.inRange(hsv, ColorLower, ColorUpper)
	mask = cv2.erode(mask, None, iterations=2)
	mask = cv2.dilate(mask, None, iterations=2)
	
	cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
	center = None
	#Detect boxes
	if len(cnts) > 0:
		c = max(cnts, key=cv2.contourArea)
		rect = cv2.minAreaRect(c)
		box = cv2.boxPoints(rect)
		boxn=np.array(box).reshape((-1,1,2)).astype(np.int32)
		if rect[1][1] > 10: #Height > 50 pixel
			cv2.drawContours(frame,[boxn],0,(255,0,0),2)
			center = (int(rect[0][0]),int(rect[0][1]))
		
	# update the points var
	pts.appendleft(center)
	
	key = cv2.waitKey(1) & 0xFF
	#IFTTT toggle
	if key == ord("p"):
		if push == False:
			push = True
		else:
			push = False
	if push:
		cv2.putText(frame,"IFTTT ON", (10,20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), thickness=1)
	else:
		cv2.putText(frame,"IFTTT OFF", (10,20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,255), thickness=1)



	# alarts
	detect_frame_num = 10
	if len(pts) >detect_frame_num:
		if pts[detect_frame_num] is None or pts[0] is None:
			cv2.putText(frame,"Not Detected!!!", (10,50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,255), thickness=3)
		else:
			motion_check = abs(pts[detect_frame_num][0]-pts[0][0])+abs(pts[detect_frame_num][1]-pts[0][1])
			if motion_check < 3:
				cv2.putText(frame,"Not Moving!!!", (10,50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), thickness=3)
				if stopped == 0:
					print "stopped at",datetime.datetime.fromtimestamp(int(time.time())).strftime('%Y-%m-%d %H:%M:%S')
					logging.info("movement stop")
					if push:
						pyfttt.send_event(api_key,event) #IFTTT alart
					stopped = 1
			else:
				cv2.putText(frame,"Moving!!!", (10,50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), thickness=3)
				if stopped == 1:
					logging.info("movement start")
				stopped = 0


	#RPM Calculator
	if key == ord("r"): #reset original point
		ref_center = center
		rep = 0
		ref_time = time.time()
		logging.info("RPM counter start")


	if center is not None:
		if ref_center:
			center_check = abs(center[0]-ref_center[0])+abs(center[1]-ref_center[1])
			if center_check < 10: #one round
				if rep == 0:
					elapsed_time = time.time() - ref_time
					RPM = str(round(60/elapsed_time,2))
					ref_time = time.time()
					rep = 1
					logging.info("round complete! RPM = %s",RPM)
			else:
				rep = 0

			cv2.putText(frame,'RPM=', (10,90), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,0), thickness=3)
			cv2.putText(frame,RPM, (100,90), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,0), thickness=3)
			cv2.circle(frame,ref_center,10,color=(0,255,255),thickness=3)

			
	# Draw trace line
	for i in xrange(1, len(pts)):
		if pts[i - 1] is None or pts[i] is None:
			continue
		thickness = int(np.sqrt(64  / float(i + 1)) * 2.5)
		cv2.line(frame, pts[i - 1], pts[i], (0, 0, 255), thickness)


	cv2.imshow("Frame", frame)
	cv2.imshow('Mask', mask)
	
	# quit when q
	if key == ord("q"):
		break

	#max fps
	time.sleep(0.1)

camera.release()
cv2.destroyAllWindows()