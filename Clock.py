from AppKit import *
import dispatch
from objc import super
import ClockData
from PyObjCTools import AppHelper
import time
import Project
from Project import Interval

def setFnDown(obj, val): # dirty
  obj.fnDown = val

class AppDelegate(NSObject):
  def applicationDidFinishLaunching_(self, notification):
    self.start = time.time()
    self.intervalStart = self.start
    self.lastFrame = self.start
    self.fadingPower = 0
    self.currentInterval = Interval()
    self.intervals = []
    self.fnDown = False
    self.gonnaQuit = False
    self.isTick = True  # tick or tock?
    self.lastTick = 0  # integer count
    self.prepared = False  # play a file silently to reduce lag
    # listen for hotkeys
    #! Goto System Preferences > Security & Privacy > Accessibility to enable
    window.orderFrontRegardless()
    NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
      NSEventMaskFlagsChanged,
      self.handler_
    )
    NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
      NSEventMaskFlagsChanged,
      self.handler_
    )
    # when the menu is open, force show/unshow
    NSNotificationCenter.defaultCenter().addObserverForName_object_queue_usingBlock_(
      NSMenuDidBeginTrackingNotification,
      menu, None, lambda _: setFnDown(self, True)
    )
    NSNotificationCenter.defaultCenter().addObserverForName_object_queue_usingBlock_(
      NSMenuDidEndTrackingNotification,
      menu, None, lambda _: setFnDown(self, False)
    )

    # start loop
    self.timer = NSTimer.timerWithTimeInterval_target_selector_userInfo_repeats_(
      1./60, self, "logic:", None, True
    )
    NSRunLoop.currentRunLoop().addTimer_forMode_(
      self.timer,
      NSRunLoopCommonModes
    )

  def loadFile_(self, sender):
    self.panel = NSOpenPanel.openPanel()
    self.panel.setMessage_("Select a json file...")
    self.panel.beginWithCompletionHandler_(self.parse_)

  def parse_(self, result):
    if result == NSModalResponseOK:
      doc = self.panel.URLs().objectAtIndex_(0)
      data = bytes(NSData.dataWithContentsOfURL_(doc))
      result = Project.loadData(data)
      if type(result) == str:
        alert = NSAlert.alloc().init()
        alert.setAlertStyle_(NSAlertStyleCritical)
        alert.setInformativeText_(result)
        alert.setMessageText_("Error loading clock")
        alert.runModal()
        return
      self.intervals = result
      self.currentInterval = Interval(totalTime=0)
      # tell it to change immediately when we have a chance

  def logic_(self, sender):
    current = time.time()
    if self.fadingPower <= 0.01:
      # should quit?
      if self.gonnaQuit and not swoosh.isPlaying():
        NSApp.terminate_(self)

      # next interval?
      # if you peek, we never switch to the next :)
      if not self.gonnaQuit and \
        current - self.intervalStart + 0.02 > self.currentInterval.totalTime:
        boom.play()
        self.intervalStart = current
        self.lastTick = 0
        if self.intervals:
          self.currentInterval = self.intervals.pop(0)
        else:
          self.currentInterval = Interval()

    # half-time forced show
    # half-time -0.7 to +1.5 (maybe slightly more)
    halftime = self.currentInterval.totalTime/2
    # but if it is too short, then no half time (but it still flashes)
    inHalftime = halftime > 10 and \
      halftime - 0.75 <= current - self.intervalStart <= halftime + 1.55
    # end-time forced show
    # when last pip starts to disappear
    endtime = self.currentInterval.totalTime * (1 - 1/self.currentInterval.totalPip) \
      if self.currentInterval.totalPip > 0 else float("inf")
    inEndtime = endtime - 2.15 <= current - self.intervalStart <= \
      min(endtime + 1.2, self.currentInterval.totalTime - 0.65)
    # also appear at the start to not be too quiet
    shouldDisplay = not self.gonnaQuit and \
      (self.fnDown or inHalftime or inEndtime or current - self.start <= 2)

    # tick-tock noise
    if current - self.intervalStart \
      >= (self.lastTick + 0.5) * Project.settings["ticktock"] and \
      not self.prepared:
      if self.isTick:
        dispatch.dispatch_async(queue, playAudio(tick, True))
      else:
        dispatch.dispatch_async(queue, playAudio(tock, True))
      self.prepared = True
    if current - self.intervalStart \
      >= (self.lastTick + 1) * Project.settings["ticktock"]:
      if self.fadingPower >= 0.99 and \
        not inHalftime and not inEndtime and \
        self.currentInterval.totalPip > 0 and current - self.intervalStart <= endtime:
        if self.isTick:
          dispatch.dispatch_async(queue, playAudio(tick))
        else:
          dispatch.dispatch_async(queue, playAudio(tock))
        self.isTick = not self.isTick
        self.prepared = False
      self.lastTick += 1

    dt = min(current - self.lastFrame, 1/20)
    if shouldDisplay:
      self.fadingPower += dt
      self.fadingPower = min(self.fadingPower, 1)
    else:
      self.fadingPower -= dt/0.7
      self.fadingPower = max(self.fadingPower, 0)

    clock = ClockData.computeClock(
      self.currentInterval.totalTime,
      current - self.intervalStart,
      self.currentInterval.totalPip,
      self.currentInterval.karmaSymbol,
      self.currentInterval.karmaReinforced,
      self.currentInterval.maxKarma,
      # mystic parameter space change
      self.fadingPower if shouldDisplay else (self.fadingPower - 1) * 0.7
    )

    if clock.alpha > 0:
      img = clock.render()
      self.nsimg = NSImage.alloc().initWithData_(NSData.dataWithBytes_length_(img, len(img)))
      imgView.setImage_(self.nsimg)
    window.setAlphaValue_(clock.alpha)
    self.lastFrame = current

  def handler_(self, event):
    if event.keyCode() == 63:
      if event.modifierFlags() & NSEventModifierFlagFunction:
        # FN pressed
        self.fnDown = True
      elif event.modifierFlags() & NSEventModifierFlagDeviceIndependentFlagsMask == 0:
        # FN released
        self.fnDown = False

  def swoosh_(self, _):
    NSStatusBar.systemStatusBar().removeStatusItem_(status)
    self.gonnaQuit = True
    swoosh.play()


class PixelatedView(NSImageView):
  """A custom view to disable any antialiasing."""
  def drawRect_(self, rect):
    quality = NSGraphicsContext.currentContext().imageInterpolation()
    NSGraphicsContext.currentContext().setImageInterpolation_(NSImageInterpolationNone)
    super().drawRect_(rect)
    NSGraphicsContext.currentContext().setImageInterpolation_(quality)

# Start the application and hide the icon
NSApplication.sharedApplication()
delegate = AppDelegate.alloc().init()
NSApp().setDelegate_(delegate)
NSApp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

# Load audio files
tock = NSSound.alloc().initWithContentsOfFile_byReference_("./resources/tock.wav", False)
tick = NSSound.alloc().initWithContentsOfFile_byReference_("./resources/tick.wav", False)
swoosh = NSSound.alloc().initWithContentsOfFile_byReference_("./resources/Pre.wav", False)
boom = NSSound.alloc().initWithContentsOfFile_byReference_("./resources/Hit.wav", False)


# status bar presence
statusImg = NSImage.alloc().initByReferencingFile_("./resources/icon.pdf")
statusImg.setTemplate_(True)
status = NSStatusBar.systemStatusBar().statusItemWithLength_(NSSquareStatusItemLength)
status.button().setImage_(statusImg)

menu = NSMenu.alloc().initWithTitle_("Menu")
menu.addItemWithTitle_action_keyEquivalent_(
  "Load...",
  "loadFile:",
  ""
)
menu.addItemWithTitle_action_keyEquivalent_(
  "Quit",
  "swoosh:",
  ""
)
status.setMenu_(menu)

# make a window
clock_size = round(ClockData.CANVAS_SIZE * Project.SCALE)
window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
  (Project.POSITION,(clock_size,clock_size)),
  NSBorderlessWindowMask,
  NSBackingStoreBuffered,
  False
)
window.setLevel_(NSScreenSaverWindowLevel)
window.setBackgroundColor_(NSColor.clearColor())
window.setOpaque_(False)
window.setIgnoresMouseEvents_(True)
window.setHasShadow_(False)
window.setCollectionBehavior_(
  NSWindowCollectionBehaviorCanJoinAllApplications |
  NSWindowCollectionBehaviorCanJoinAllSpaces |
  NSWindowCollectionBehaviorStationary |
  NSWindowCollectionBehaviorFullScreenAuxiliary |
  NSWindowCollectionBehaviorIgnoresCycle
)

# make the image
nsimg = NSImage.alloc().initWithSize_(ClockData.CANVAS_RECT)
imgView = PixelatedView.imageViewWithImage_(nsimg)
imgView.setImageScaling_(NSImageScaleAxesIndependently)
window.setContentView_(imgView)

# dispatch queues
queue = dispatch.dispatch_get_global_queue(dispatch.DISPATCH_QUEUE_PRIORITY_HIGH, 0)
def playAudio(file, stop=False):
  def closure():
    file.setVolume_(0.0 if stop else 1.0)
    # a = time.time()
    file.play()
    # print(file, time.time() - a, stop)
    if stop:
      file.stop()
  return closure

NSApp.run()
# AppHelper.runEventLoop()

