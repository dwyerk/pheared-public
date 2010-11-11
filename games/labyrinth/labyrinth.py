import soya, os, sys, soya.sdlconst

soya.init()
soya.path.append(os.path.join(os.path.dirname(sys.argv[0]),""))

scene = soya.World()
board_model = soya.Model.get('lab1')

class RotatingBody(soya.Body):
    def advance_time(self, proportion):
        soya.Body.advance_time(self, proportion)
        self.rotate_y(proportion * 1.0)

class TiltBody(soya.Body):
    def __init__(self, parent, model):
        soya.Body.__init__(self, parent, model)
        self.speed = soya.Vector(self, 0.0, 0.0, 0.0)
        self.max_z = self.max_x = 10
        self.tilt_z = 0
        self.tilt_x = 0
        self.tilt_forward = False
        self.tilt_backward = False
        self.tilt_right = False
        self.tilt_left = False

    def begin_round(self):
        soya.Body.begin_round(self)

        for event in soya.process_event():
            event_type = event[0]

            if event_type == soya.sdlconst.KEYDOWN:
                key, modifier = event[1:]

                if key == soya.sdlconst.K_UP:
                    self.tilt_forward = True
                    print "tilt forward", self.tilt_x

                elif key == soya.sdlconst.K_DOWN:
                    self.tilt_backward = True
                    print "tilt back", self.tilt_x

                elif key == soya.sdlconst.K_LEFT:
                    self.tilt_left = True
                    print "tilt left", self.tilt_z

                elif key == soya.sdlconst.K_RIGHT:
                    self.tilt_right = True
                    print "tilt right", self.tilt_z

                elif key == soya.sdlconst.K_q:
                    soya.MAIN_LOOP.stop()

                elif key == soya.sdlconst.K_ESCAPE:
                    soya.MAIN_LOOP.stop()

            elif event_type == soya.sdlconst.KEYUP:
                key, modifier = event[1:]

                if key == soya.sdlconst.K_UP:
                    self.tilt_forward = False
                    print "end tilt forward"

                elif key == soya.sdlconst.K_DOWN:
                    self.tilt_backward = False
                    print "end tilt back"

                elif key == soya.sdlconst.K_LEFT:
                    self.tilt_left = False
                    print "end tilt left"

                elif key == soya.sdlconst.K_RIGHT:
                    self.tilt_right = False
                    print "end tilt right"

            elif event_type == soya.sdlconst.QUIT:
                soya.MAIN_LOOP.stop()

            elif event_type == soya.sdlconst.MOUSEMOTION:
                # Need to figure out how far from 0 we went
                print "mouse movement", event
            else:
                print "unhandled event:", event


    def advance_time(self, proportion):
        soya.Body.advance_time(self, proportion)

        #self.rotate_x(self.tilt_x)
        #self.rotate_z(self.tilt_z)

        move_factor = 1

        # This isn't exactly right, because it allows the board to rotate
        if self.tilt_forward and self.tilt_x >= -self.max_x:
            self.tilt_x -= move_factor
            self.rotate_x(-move_factor)
        elif not self.tilt_forward and self.tilt_x < 0:
            self.tilt_x += move_factor
            self.rotate_x(move_factor)

        if self.tilt_backward and self.tilt_x <= self.max_x:
            self.tilt_x += move_factor
            self.rotate_x(move_factor)
        elif not self.tilt_backward and self.tilt_x > 0:
            self.tilt_x -= move_factor
            self.rotate_x(-move_factor)

        if self.tilt_left and self.tilt_z <= self.max_z:
            self.tilt_z += move_factor
            self.rotate_z(move_factor)
        elif not self.tilt_left and self.tilt_z > 0:
            self.tilt_z -= move_factor
            self.rotate_z(-move_factor)

        if self.tilt_right and self.tilt_z >= -self.max_z:
            self.tilt_z -= move_factor
            self.rotate_z(-move_factor)
        elif not self.tilt_right and self.tilt_z < 0:
            self.tilt_z += move_factor
            self.rotate_z(move_factor)

#board = RotatingBody(scene, board_model)
board = TiltBody(scene, board_model)

light = soya.Light(scene)
light.set_xyz(0.5,0.0,2.0)

light = soya.Light(scene)
light.set_xyz(0.0, -5.0, 2.0)

camera = soya.Camera(scene)
camera.z = 30.0
camera.y = 0.0

soya.set_root_widget(camera)
soya.MainLoop(scene).main_loop()
