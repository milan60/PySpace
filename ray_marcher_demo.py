#!/usr/bin/env python

import pygame, sys, math, random, os
import numpy as np
import pyspace

from pyspace.coloring import *
from pyspace.fold import *
from pyspace.geo import *
from pyspace.object import *
from pyspace.shader import Shader
from pyspace.camera import Camera

from ctypes import *
from OpenGL.GL import *
from pygame.locals import *

import ctypes
user32 = ctypes.windll.user32

import os
os.environ['SDL_VIDEO_CENTERED'] = '1'

#Size of the window and rendering
win_size = (user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))

#Maximum frames per second
max_fps = 120

#Forces an 'up' orientation when True, free-camera when False
gimbal_lock = False

#Mouse look speed
look_speed = 0.003

#Use this avoids collisions with the fractal
auto_velocity = True
auto_multiplier = 2.0

#Maximum velocity of the camera
max_velocity = 2.0

#Amount of acceleration when moving
speed_accel = 2.0

#Velocity decay factor when keys are released
speed_decel = 0.6

clicking = False
mouse_pos = None
screen_center = (int(win_size[0]/2), int(win_size[1]/2))
start_pos = [0, 0, 12.0]
vel = np.zeros((3,), dtype=np.float32)
look_x = 0.0
look_y = 0.0

#----------------------------------------------
#    When building your own fractals, you can
# substitute numbers with string placeholders
# which can be tuned real-time with key bindings.
#
# In this example program:
#    '0'   +Insert  -Delete
#    '1'   +Home    -End
#    '2'   +PageUp  -PageDown
#    '3'   +NumPad7 -NumPad4
#    '4'   +NumPad8 -NumPad5
#    '5'   +NumPad9 -NumPad6
#
# Hold down left-shift to decrease rate 10x
# Hold down right-shift to increase rate 10x
#
# Set initial values of '0' through '6' below
#----------------------------------------------
keyvars = [0.34, 3.28, 0.42, 0.38, 0.19, 1.0]

recursionMultiplier = 1

#----------------------------------------------
#            Fractal Examples Below
#----------------------------------------------
def infinite_spheres():
    obj = Object()
    obj.add(FoldRepeatX(2.0))
    obj.add(FoldRepeatY(2.0))
    obj.add(FoldRepeatZ(2.0))
    obj.add(Sphere(0.5, (1.0, 1.0, 1.0), color=(0.9,0.9,0.5)))
    return obj

def butterweed_hills():
    global recursionMultiplier
    obj = Object()
    obj.add(OrbitInitZero())
    for _ in range(30):
        obj.add(FoldAbs())
        obj.add(FoldScaleTranslate(1.5, (-1.0,-0.5,-0.2)))
        obj.add(OrbitSum((0.5, 0.03, 0.0)))
        obj.add(FoldRotateX(3.61))
        obj.add(FoldRotateY(2.03))
    obj.add(Sphere(1.0, color='orbit'))
    return obj

def mandelbox():
    global recursionMultiplier
    obj = Object()
    obj.add(OrbitInitInf())
    for _ in range(16):
        obj.add(FoldBox(1.0))
        obj.add(FoldSphere(0.5, 1.0))
        obj.add(FoldScaleOrigin(2.0))
        obj.add(OrbitMinAbs(1.0))
    obj.add(Box(6.0, color='orbit'))
    return obj

def mausoleum():
    global recursionMultiplier
    obj = Object()
    obj.add(OrbitInitZero())
    for _ in range(8):
        obj.add(FoldBox(0.34))
        obj.add(FoldMenger())
        obj.add(FoldScaleTranslate(3.28, (-5.27,-0.34,0.0)))
        obj.add(FoldRotateX(math.pi/2))
        obj.add(OrbitMax((0.42,0.38,0.19)))
    obj.add(Box(2.0, color='orbit'))
    return obj

def menger():
    global recursionMultiplier
    obj = Object()
    for _ in range(8):
        obj.add(FoldAbs())
        obj.add(FoldMenger())
        obj.add(FoldScaleTranslate(3.0, (-2,-2,0)))
        obj.add(FoldPlane((0,0,-1), -1))
    obj.add(Box(2.0, color=(.2,.5,1)))
    return obj

def tree_planet():
    global recursionMultiplier
    obj = Object()
    obj.add(OrbitInitInf())
    for _ in range(30):
        obj.add(FoldRotateY(0.44))
        obj.add(FoldAbs())
        obj.add(FoldMenger())
        obj.add(OrbitMinAbs((0.24,2.28,7.6)))
        obj.add(FoldScaleTranslate(1.3, (-2,-4.8,0)))
        obj.add(FoldPlane((0,0,-1), 0))
    obj.add(Box(4.8, color='orbit'))
    return obj

def sierpinski_tetrahedron():
    global recursionMultiplier
    obj = Object()
    obj.add(OrbitInitZero())
    for _ in range(9):
        obj.add(FoldSierpinski())
        obj.add(FoldScaleTranslate(2, -1))
    obj.add(Tetrahedron(color=(0.8,0.8,0.5)))
    return obj

def snow_stadium():
    global recursionMultiplier
    obj = Object()
    obj.add(OrbitInitInf())
    for _ in range(30):
        obj.add(FoldRotateY(3.33))
        obj.add(FoldSierpinski())
        obj.add(FoldRotateX(0.15))
        obj.add(FoldMenger())
        obj.add(FoldScaleTranslate(1.57, (-6.61, -4.0, -2.42)))
        obj.add(OrbitMinAbs(1.0))
    obj.add(Box(4.8, color='orbit'))
    return obj

def test_fractal():
    global recursionMultiplier
    obj = Object()
    obj.add(OrbitInitInf())
    for _ in range(20):
        obj.add(FoldSierpinski())
        obj.add(FoldMenger())
        obj.add(FoldRotateY(math.pi/2))
        obj.add(FoldAbs())
        obj.add(FoldRotateZ('0'))
        obj.add(FoldScaleTranslate(1.89, (-7.10, 0.396, -6.29)))
        obj.add(OrbitMinAbs((1,1,1)))
    obj.add(Box(6.0, color='orbit'))
    return obj

#----------------------------------------------
#             Helper Utilities
#----------------------------------------------
def interp_data(x, f=2.0):
    new_dim = int(x.shape[0]*f)
    output = np.empty((new_dim,) + x.shape[1:], dtype=np.float32)
    for i in range(new_dim):
        a, b1 = math.modf(float(i) / f)
        b2 = min(b1 + 1, x.shape[0] - 1)
        output[i] = x[int(b1)]*(1-a) + x[int(b2)]*a
    return output

def make_rot(angle, axis_ix):
    s = math.sin(angle)
    c = math.cos(angle)
    if axis_ix == 0:
        return np.array([[ 1,  0,  0],
                         [ 0,  c, -s],
                         [ 0,  s,  c]], dtype=np.float32)
    elif axis_ix == 1:
        return np.array([[ c,  0,  s],
                         [ 0,  1,  0],
                         [-s,  0,  c]], dtype=np.float32)
    elif axis_ix == 2:
        return np.array([[ c, -s,  0],
                         [ s,  c,  0],
                         [ 0,  0,  1]], dtype=np.float32)

def reorthogonalize(mat):
    u, s, v = np.linalg.svd(mat)
    return np.dot(u, v)

def translate(value, leftMin, leftMax, rightMin, rightMax):
    leftSpan = leftMax - leftMin
    rightSpan = rightMax - rightMin
    valueScaled = float(value - leftMin) / float(leftSpan)
    return rightMin + (valueScaled * rightSpan)

def convertRGB(r, g, b):
    return (translate(r, 0, 255, 0, 1), translate(g, 0, 255, 0, 1), translate(b, 0, 255, 0, 1))

FreeMouse = False
LockSpeed = False
LockedSpeed = None
LockedAcc = None

# move the cursor back , only if the window is focused
def center_mouse():
    if pygame.key.get_focused():
        pygame.mouse.set_pos(screen_center)

#--------------------------------------------------
#                  Video Recording
#
#    When you're ready to record a video, press 'r'
# to start recording, and then move around.  The
# camera's path and live '0' through '5' parameters
# are recorded to a file.  Press 'r' when finished.
#
#    Now you can exit the program and turn up the
# camera parameters for better rendering.  For
# example; window size, anti-aliasing, motion blur,
# and depth of field are great options.
#
#    When you're ready to playback and render, press
# 'p' and the recorded movements are played back.
# Images are saved to a './playback' folder.  You
# can import the image sequence to editing software
# to convert it to a video.
#
#    You can press 's' anytime for a screenshot.
#---------------------------------------------------

if __name__ == '__main__':
    print("")
    print("")
    print("Controls:")
    print("c           Take a screenshot")
    print("r           Start/Stop a recording")
    print("p           Playback the last recording")
    print("f           Pause/Unpause")
    print("Left Shift  Lock/Unlock current movement")
    print("Space       Hold to move faster")
    print("")
    print("Select a fractal")
    print("Options: infinite_spheres, butterweed_hills, mandelbox, mausoleum, menger, tree_planet, sierpinski_tetrahedron, snow_stadium, test_fractal")
    
    fractalSelection = str(input())
    
    #print("")
    #print("Select a recursion multiplier (integer between 1 and 5) leave empty for default")
    #recursionMultiplierSelection = str(input())
    #if recursionMultiplierSelection == "2":
    #    recursionMultiplier = 2
    #elif recursionMultiplierSelection == "3":
    #    recursionMultiplier = 3
    #elif recursionMultiplierSelection == "4":
    #    recursionMultiplier = 4
    #elif recursionMultiplierSelection == "5":
    #    recursionMultiplier = 5
    
    pygame.init()
    window = pygame.display.set_mode(win_size, OPENGL | DOUBLEBUF)
    pygame.mouse.set_visible(FreeMouse)
    center_mouse()
    
    obj_render = False
    
    if fractalSelection == "infinite_spheres":
        obj_render = infinite_spheres()
    elif fractalSelection == "butterweed_hills":
        obj_render = butterweed_hills()
    elif fractalSelection == "mandelbox":
        obj_render = mandelbox()
    elif fractalSelection == "mausoleum":
        obj_render = mausoleum()
    elif fractalSelection == "menger":
        obj_render = menger()
    elif fractalSelection == "tree_planet":
        obj_render = tree_planet()
    elif fractalSelection == "sierpinski_tetrahedron":
        obj_render = sierpinski_tetrahedron()
    elif fractalSelection == "snow_stadium":
        obj_render = snow_stadium()
    elif fractalSelection == "test_fractal":
        obj_render = test_fractal()
    else:
        print("Invalid selection")
        sys.exit(0)
        
    pygame.display.set_caption(fractalSelection + ' Fractal')
    

    #======================================================
    #             Change camera settings here
    # See pyspace/camera.py for all camera options
    #======================================================
    camera = Camera()
    camera['ANTIALIASING_SAMPLES'] = 1
    camera['AMBIENT_OCCLUSION_STRENGTH'] = 0.01
    camera['DIFFUSE_ENABLED'] = True
    camera['FOG_ENABLED'] = True
    camera['LIGHT_COLOR'] = convertRGB(252, 212, 64)
    
    camera['LOD_MULTIPLIER'] = 100
    camera['MIN_DIST'] = 0.000001
    camera['VIGNETTE_FOREGROUND'] = True
    #======================================================

    shader = Shader(obj_render)
    program = shader.compile(camera)

    matID = glGetUniformLocation(program, "iMat")
    prevMatID = glGetUniformLocation(program, "iPrevMat")
    resID = glGetUniformLocation(program, "iResolution")
    ipdID = glGetUniformLocation(program, "iIPD")

    glUseProgram(program)
    glUniform2fv(resID, 1, win_size)
    glUniform1f(ipdID, 0.04)

    fullscreen_quad = np.array([-1.0, -1.0, 0.0, 1.0, -1.0, 0.0, -1.0, 1.0, 0.0, 1.0, 1.0, 0.0], dtype=np.float32)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, fullscreen_quad)
    glEnableVertexAttribArray(0)

    mat = np.identity(4, np.float32)
    mat[3,:3] = np.array(start_pos)
    prevMat = np.copy(mat)
    for i in range(len(keyvars)):
        shader.set(str(i), keyvars[i])

    recording = None
    rec_vars = None
    playback = None
    playback_vars = None
    playback_ix = -1
    frame_num = 0
    
    color_white = (255, 255, 255)
    last_fps = 0
    
    def finish_recording():
        global recording
        global rec_vars
        np.save('recording.npy', np.array(recording, dtype=np.float32))
        np.save('rec_vars.npy', np.array(rec_vars, dtype=np.float32))
        recording = None
        rec_vars = None

    def start_playback():
        global playback
        global playback_vars
        global playback_ix
        global prevMat
        if not os.path.exists('playback'):
            os.makedirs('playback')
        playback = np.load('recording.npy')
        playback_vars = np.load('rec_vars.npy')
        playback = interp_data(playback, 2)
        playback_vars = interp_data(playback_vars, 2)
        playback_ix = 0
        prevMat = playback[0]
    
    def getScreenshotFileName():
        if not os.path.exists('screenshots'):
            os.makedirs('screenshots')
        
        index = 1
        filename = 'screenshots/screenshot_'+str(index)+'.png'
        while os.path.exists(filename):
            index += 1
            filename = 'screenshots/screenshot_'+str(index)+'.png'
        return filename

    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit(0)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    if recording is None:
                        recording = []
                        rec_vars = []
                    else:
                        finish_recording()
                elif event.key == pygame.K_p:
                    if recording is not None:
                        finish_recording()
                    start_playback()
                elif event.key == pygame.K_c:
                    pygame.image.save(window, getScreenshotFileName())
                elif event.key == pygame.K_f:
                    FreeMouse = not FreeMouse
                    if FreeMouse:
                        center_mouse()
                    pygame.mouse.set_visible(FreeMouse)
                elif event.key == pygame.K_ESCAPE:
                    sys.exit(0)
                elif event.key == pygame.K_LSHIFT:
                    if not LockSpeed:
                        LockedSpeed = None
                        LockedAcc = None
                    LockSpeed = not LockSpeed
                    
        if FreeMouse:
            continue

        mat[3,:3] += vel * (clock.get_time() / 1000)

        if auto_velocity:
            de = obj_render.DE(mat[3]) * auto_multiplier
            if not np.isfinite(de):
                de = 0.0
        else:
            de = 1e20

        all_keys = pygame.key.get_pressed()

        rate = 0.0001

        if all_keys[pygame.K_INSERT]:   keyvars[0] += rate; #print(keyvars)
        if all_keys[pygame.K_DELETE]:   keyvars[0] -= rate; #print(keyvars)
        if all_keys[pygame.K_HOME]:     keyvars[1] += rate; #print(keyvars)
        if all_keys[pygame.K_END]:      keyvars[1] -= rate; #print(keyvars)
        if all_keys[pygame.K_PAGEUP]:   keyvars[2] += rate; #print(keyvars)
        if all_keys[pygame.K_PAGEDOWN]: keyvars[2] -= rate; #print(keyvars)
        if all_keys[pygame.K_KP7]:      keyvars[3] += rate; #print(keyvars)
        if all_keys[pygame.K_KP4]:      keyvars[3] -= rate; #print(keyvars)
        if all_keys[pygame.K_KP8]:      keyvars[4] += rate; #print(keyvars)
        if all_keys[pygame.K_KP5]:      keyvars[4] -= rate; #print(keyvars)
        if all_keys[pygame.K_KP9]:      keyvars[5] += rate; #print(keyvars)
        if all_keys[pygame.K_KP6]:      keyvars[5] -= rate; #print(keyvars)

        if playback is None:
            prev_mouse_pos = mouse_pos
            mouse_pos = pygame.mouse.get_pos()
            dx,dy = 0,0
            if prev_mouse_pos is not None:
                center_mouse()
                time_rate = (clock.get_time() / 1000.0) / (1 / max_fps)
                dx = (mouse_pos[0] - screen_center[0]) * time_rate
                dy = (mouse_pos[1] - screen_center[1]) * time_rate

            if pygame.key.get_focused():
                if gimbal_lock:
                    look_x += dx * look_speed
                    look_y += dy * look_speed
                    look_y = min(max(look_y, -math.pi/2), math.pi/2)

                    rx = make_rot(look_x, 1)
                    ry = make_rot(look_y, 0)

                    mat[:3,:3] = np.dot(ry, rx)
                else:
                    rx = make_rot(dx * look_speed, 1)
                    ry = make_rot(dy * look_speed, 0)

                    mat[:3,:3] = np.dot(ry, np.dot(rx, mat[:3,:3]))
                    mat[:3,:3] = reorthogonalize(mat[:3,:3])

            acc = np.zeros((3,), dtype=np.float32)
            
            if all_keys[pygame.K_a]:
                acc[0] -= speed_accel / max_fps
            if all_keys[pygame.K_d]:
                acc[0] += speed_accel / max_fps
            if all_keys[pygame.K_w]:
                acc[2] -= speed_accel / max_fps
            if all_keys[pygame.K_s]:
                acc[2] += speed_accel / max_fps
            
            if LockSpeed and LockedAcc is not None:
                acc = LockedAcc
            else:
                LockedAcc = acc

            if np.dot(acc, acc) == 0.0:
                vel *= speed_decel # TODO
            elif not LockSpeed or LockedSpeed is None:
                vel += np.dot(mat[:3,:3].T, acc)
                vel_ratio = min(max_velocity, de) / (np.linalg.norm(vel) + 1e-12)
                if vel_ratio < 1.0:
                    vel *= vel_ratio
                LockedSpeed = vel
            elif LockSpeed:
                vel = LockedSpeed
            
            if all_keys[pygame.K_SPACE] and not LockSpeed:
                vel *= 10.0

            if recording is not None:
                recording.append(np.copy(mat))
                rec_vars.append(np.array(keyvars, dtype=np.float32))
        else:
            if playback_ix >= 0:
                ix_str = '%04d' % playback_ix
                pygame.image.save(window, 'playback/frame' + ix_str + '.png')
            if playback_ix >= playback.shape[0]:
                playback = None
                break
            else:
                mat = prevMat * 0.98 + playback[playback_ix] * 0.02
                mat[:3,:3] = reorthogonalize(mat[:3,:3])
                keyvars = playback_vars[playback_ix].tolist()
                playback_ix += 1

        for i in range(3):
            shader.set(str(i), keyvars[i])
        shader.set('v', np.array(keyvars[3:6]))
        shader.set('pos', mat[3,:3])

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glUniformMatrix4fv(matID, 1, False, mat)
        glUniformMatrix4fv(prevMatID, 1, False, prevMat)
        prevMat = np.copy(mat)

        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)
        
        pygame.display.flip()
        clock.tick(max_fps)
        frame_num += 1
        
        last_fps = clock.get_fps()
        
        print('FPS:' + str(last_fps), end='\r')
