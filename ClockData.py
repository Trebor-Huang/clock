from PIL import Image, ImageDraw
from dataclasses import dataclass
import Project
import io
import numpy as math

SCALE = 4

CANVAS_SIZE = 151
CANVAS_RECT = (CANVAS_SIZE,CANVAS_SIZE)
CANVAS_SIZE_SCALE = int(CANVAS_SIZE * SCALE)
# 67x67 karma symbols and circles
KARMA_SIZE = 67

x, y = math.meshgrid(
  math.linspace(-1, 1, CANVAS_SIZE),
  math.linspace(-1, 1, CANVAS_SIZE)
)
radius = math.clip(1 - math.tanh(3.9 * (x**2 + y**2)**2.5), 0, 1) * 255
background = math.concatenate((
    math.zeros((CANVAS_SIZE, CANVAS_SIZE, 3)),
    radius.reshape((CANVAS_SIZE, CANVAS_SIZE, 1))
  ), axis=2).astype('uint8')
background = Image.fromarray(background, "RGBA")

karmas = {}
for number in [
  "1", "2", "3", "4", "5",
  "6-1", "6-2", "6-3", "6-4",
  "7-1", "7-2", "7-3", "7-4",
  "8-2", "8-3", "8-4",
  "9-3", "9-4",
  "10"]:
  with Image.open(f"./resources/Karma_{number}.png") as img:
    karmas[number] = img.convert("RGBA")

with Image.open(f"./resources/Circle.png") as img:
  karmas["Circle"] = img.convert("RGBA")
with Image.open(f"./resources/CircleReinforced.png") as img:
  karmas["CircleReinforced"] = img.convert("RGBA")

@dataclass
class Clock:
  """Manages the animation state of the Rain World clock."""
  alpha : float = 1  # from 0 to 1
  karmaSymbol : int = 0  # 0 to maxKarma
  karmaReinforced : bool = False
  maxKarma : int = 5 # 5 to 10 excluding 6
  karmaScale : float = 1

  pipTotal : int = 20
  pipCurrent : int = 15  # not including last pip
  pipRingRadius : float = 34  # px
  pipRingExpansion : float = 1
    # 0 means everything is collapsed counterclockwise to the top

  pipExRadius : int = 2  # px
  pipInRadius : int = 0  # Also used to flash
  lastPipExRadius : int = 2.8
  lastPipInRadius : int = 1.5
  pulsePos : float = None

  def render(self):
    """Draws the clock on a PIL image."""
    img = Image.new("RGBA", (CANVAS_SIZE_SCALE,CANVAS_SIZE_SCALE), (0,0,0,0))

    # Outer circle
    karpos = round((CANVAS_SIZE - KARMA_SIZE * self.karmaScale)/2) * SCALE
    karsize = round(KARMA_SIZE * self.karmaScale) * SCALE
    img.alpha_composite(karmas[
        "CircleReinforced" if self.karmaReinforced else "Circle"
      ].resize((karsize, karsize),
        resample=Image.Resampling.NEAREST),
      dest=(karpos,karpos))
    if self.karmaSymbol > 0:
      # try to determine karma name
      if self.karmaSymbol <= 5:
        name = str(self.karmaSymbol)
      elif 6 <= self.karmaSymbol < 10:
        name = f"{self.karmaSymbol}-{self.maxKarma-6}"
      else:
        name = "10"
      img.alpha_composite(
        karmas[name].resize((karsize, karsize),
          resample=Image.Resampling.NEAREST),
        dest=(karpos,karpos))

    # draw pip ring
    draw = ImageDraw.Draw(img)
    for i in range(self.pipCurrent):
      angle = 2 * math.pi * (1 - i / self.pipTotal) * self.pipRingExpansion
      y = round(CANVAS_SIZE / 2 - self.pipRingRadius * math.cos(angle)) * SCALE
      x = round(CANVAS_SIZE / 2 + self.pipRingRadius * math.sin(angle)) * SCALE

      realRadius = self.pipExRadius * SCALE
      if self.pulsePos is not None:
        realRadius *= 1 + math.exp(- 0.5 * (i - self.pulsePos)**2)
      draw.ellipse([
          (x-realRadius, y-realRadius),
          (x+realRadius, y+realRadius)
        ],
        outline="white",
        fill="white" if self.pipInRadius <= 0 else None,
        width= round((self.pipExRadius - self.pipInRadius) * SCALE)
      )

    # draw last pip
    if self.pipTotal > 0:
      angle = 2 * math.pi * (1 - self.pipCurrent / self.pipTotal) * self.pipRingExpansion
      y = round(CANVAS_SIZE / 2 - self.pipRingRadius * math.cos(angle)) * SCALE
      x = round(CANVAS_SIZE / 2 + self.pipRingRadius * math.sin(angle)) * SCALE
      draw.ellipse([
          (x-self.lastPipExRadius * SCALE, y-self.lastPipExRadius * SCALE),
          (x+self.lastPipExRadius * SCALE, y+self.lastPipExRadius * SCALE)
        ],
        outline="white",
        fill="white" if self.lastPipInRadius <= 0 else None,
        width= round((self.lastPipExRadius - self.lastPipInRadius) * SCALE)
      )

    # downsample
    img = img.resize(CANVAS_RECT, Image.Resampling.NEAREST)
    # composite with halo to aid readibility
    composite = Image.alpha_composite(background, img)
    with io.BytesIO() as buffer:
      composite.save(buffer, format="PNG")
      return buffer.getvalue()

def computeClock(timeTotal, timeCurrent,
    pipTotal, karmaSymbol, karmaReinforced, maxKarma,
    fadeInOut  # controls fade in and out; fade out takes 0.7s and fade in 1s.
    # positive: time since appearance, negative: time since asked to close
  ):
  """Computes the clock state from display data."""
  # runs from pipTotal to 0 during the interval
  pipRatio = pipTotal * (1 - timeCurrent / timeTotal)
  pipCurrent = max(int(pipRatio), 0)
  if pipTotal <= 0:
    timeToPipOff = 0
  elif timeTotal == float("inf") or timeTotal <= 0:
    timeTotal = float("inf")
    timeToPipOff = float("inf")
  else:
    timeToPipOff = ((max(round(pipRatio), 0) - pipRatio) / pipTotal) * timeTotal

  # negative: pending pip-off; positive: we just pipped-off
  tickCount = timeCurrent / Project.settings["ticktock"]
  if pipTotal * (1 - round(tickCount) * Project.settings["ticktock"] / timeTotal) < 1:
    # stop ticking at the last pip
    timeToTick = float("inf")
  else:
    timeToTick = round(tickCount) - tickCount

  # pip ring radius depends on whether it is reinforced
  pipRingRadius = 40 if karmaReinforced else 32

  # A pulse runs down the pips
  if fadeInOut < 0 or fadeInOut > 1.5:
    pulsePos = None
  else:
    pulsePos = pipCurrent * (1 - fadeInOut ** 2.5) - 5

  if -0.7 < fadeInOut < 1:
    if fadeInOut < 0:
      fadeInOut = 1 + fadeInOut/0.7
    karmaScale = min(1, 0.7 + fadeInOut ** 1.1)
    # pip expansion low => slightly larger radius
    pipRingRadius *= 0.2 * 0.1**fadeInOut + 0.98
    pipRingRadius *= karmaScale
    alpha = fadeInOut ** 1.1
    pipRingExpansion = 0.5 * (math.tanh(5 * (fadeInOut - 0.4)) + 1)
  elif fadeInOut < 0:  # Completely faded
    return Clock(alpha = 0)
  else:  # Completely shown
    alpha = 1
    pipRingExpansion = 1
    pulsePos = None
    karmaScale = 1

  pipInRadius = 0
  pipExRadius = 2
  # Half-time flashing (1.5s)
  if timeTotal/2 < timeCurrent < timeTotal/2 + 1.5:
    if (timeCurrent - timeTotal/2) % 0.5 < 0.25:
      pipInRadius = 1.5
      pipExRadius = 2.5
  else:
    # Ticking
    pipRingRadius *= max(1, 1.11 - abs(timeToTick/9.8) ** (0.52 if timeToTick < 0 else 0.4))

  lastPipInRadius = 1.5
  lastPipExRadius = 2.5

  # last pip disappears after
  if pipTotal > 0:
    anticipation = min(1.1, 0.5 * timeTotal / pipTotal)
    transition = min(0.5, 0.5 * timeTotal / pipTotal)
    if -anticipation < timeToPipOff < 0:
      lastPipExRadius *= (-timeToPipOff / anticipation)**0.8
      lastPipInRadius *= max((-timeToPipOff / anticipation) ** 2 - 0.3, 0)
    if 0 <= timeToPipOff < transition:
      lastPipInRadius = 1.5 * (timeToPipOff / transition) ** 1.5
      lastPipExRadius = 2 + 0.5 * (timeToPipOff / transition) ** 0.1

  # At fade-in and fade-out, smaller pip radius
  if abs(fadeInOut) < 1:
    scaleFactor = min(1 , (fadeInOut % 1) * 1.5)
    pipInRadius *= scaleFactor
    pipExRadius *= scaleFactor
    lastPipInRadius *= scaleFactor
    lastPipExRadius *= scaleFactor

  return Clock(
    alpha,
    karmaSymbol, karmaReinforced, maxKarma,
    karmaScale,
    pipTotal, pipCurrent,
    pipRingRadius, pipRingExpansion,
    pipExRadius, pipInRadius,
    lastPipExRadius, lastPipInRadius,
    pulsePos
  )
