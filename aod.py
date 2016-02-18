import numpy as np
import cv2

def getForegroundMask(frame, background, th):
    # reduce the nois in the farme
    frame =  cv2.blur(frame, (5,5))
    # get the absolute difference between the foreground and the background
    fgmask= cv2.absdiff(frame, background)
    # convert foreground mask to gray
    fgmask = cv2.cvtColor(fgmask, cv2.COLOR_BGR2GRAY)
    # apply threshold (th) on the foreground mask
    _, fgmask = cv2.threshold(fgmask, th, 255, cv2.THRESH_BINARY)
    # setting up a kernal for morphology
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5,5))
    # apply morpholoygy on the foreground mask to get a better result
    fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_CLOSE, kernel)
    return fgmask

def MOG2init(history, T, nMixtures):
    # create an instance of MoG and setting up its history length
    fgbg = cv2.createBackgroundSubtractorMOG2(history)
    # setting up the protion of the background model
    fgbg.setBackgroundRatio(T)
    # setting up the number of MoG
    fgbg.setNMixtures(nMixtures)
    return fgbg

def extract_objs(image, step_size, window_size):
    # a threshold for min static pixels needed to be found in the sliding window
    th = (window_size**2) * 0.1
    current_nonzero_elements = 0
    # penalty is how meny times the expanding process didn't manage to find new
    # static pixels, step is how much the expanding of the sliding will be and objs is a returned
    # value containing the objects in the image
    penalty, step, objs = 0, 5, []
    # a while loop for sliding window in x&y
    y = 0
    while(y < image.shape[0]):
        x = 0
        while(x < image.shape[1]):
            # counting the nonzero elements in the current window
            current_nonzero_elements = np.count_nonzero(image[y:y+window_size, x:x+window_size])
            if(current_nonzero_elements > th):
                width =  window_size
                height = window_size
                # expand in x & y
                penalty = 0
                while(penalty < 1):
                    dx = np.count_nonzero(image[y:y+height, x+width:x+width+step])
                    dy = np.count_nonzero(image[y+height: y+height+step, x:x+width])
                    if(dx == 0 and dy == 0):
                        penalty += 1
                        width += step
                        height += step
                    elif(dx >= dy):
                        width += step
                    else:
                        height += step

                objs.append([x, y, width, height])
                y += height
                break
            x += step_size
        y += step_size
    if(len(objs)):
        return objs
    return

cap = cv2.VideoCapture('1.mp4')

# setting up a kernal for morphology
kernal = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3,3))

# MoG for long background model
fgbgl = MOG2init(300, 0.4, 3)
# MoG for short background model
fgbgs = MOG2init(300, 0.4, 3)

longBackgroundInterval = 20
shortBackgroundINterval = 1

clfg = longBackgroundInterval   # counter for longbackgroundInterval
csfg = shortBackgroundINterval  # counter for shortBackgroundInteral

# static obj likelihood
L = np.zeros(np.shape(cap.read()[1])[0:2])
static_obj = np.zeros(np.shape(cap.read()[1])[0:2])
k, maxe, thh= 100, 1000, 700

while(1):
    ret, frame = cap.read()

    if clfg == longBackgroundInterval:
        frameL = np.copy(frame)
        fgbgl.apply(frameL)
        BL = fgbgl.getBackgroundImage(frameL)
        clfg = 0
    else:
        clfg += 1

    if csfg == shortBackgroundINterval:
        frameS = np.copy(frame)
        fgbgs.apply(frameS)
        BS = fgbgs.getBackgroundImage(frameS)
        csfg = 0
    else:
        csfg += 1

    # update short&long foregrounds
    FL = getForegroundMask(frame, BL, 70)
    FS = getForegroundMask(frame, BS, 70)

    # detec static pixels and apply morphology on it
    static = FL&cv2.bitwise_not(FS)
    static = cv2.morphologyEx(static, cv2.MORPH_CLOSE, kernal)
    # dectec non static objectes and apply morphology on it
    not_static = FS|cv2.bitwise_not(FL)
    not_static = cv2.morphologyEx(not_static, cv2.MORPH_CLOSE, kernal)

    # update static obj likelihood
    L = (static == 255) * (L+1) + ((static == 255)^1) * L
    L = (not_static == 255) * (L-k) + ((not_static == 255)^1) * L
    L[ L>maxe ] = maxe
    L[ L<0 ] = 0

    static_obj[L >= thh ] = 255
    static_obj[L < thh ] = 0

    frame[L>=thh] = 0,0,255
    #cv2.imshow("static_obj", static_obj)
    cv2.imshow("frame", frame)

    # check if Esc is presed exit the video
    k = cv2.waitKey(1) & 0xff
    if k == 27:
        break

cap.release()
cv2.destoryAllWindows()
