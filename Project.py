import json
from dataclasses import dataclass
# Parses json data and use it to determine our clock project

SCALE = 1  # how much to scale your clock
POSITION = (150, 100)  # distance to the bottom left corner
settings = {
  "ticktock": 3.2  # seconds between ticks
}

@dataclass
class Interval:
  totalPip: int = 0
  totalTime: float = float("inf")  # in seconds
  karmaSymbol : int = 0  # 0 to maxKarma
  karmaReinforced : bool = False
  maxKarma : int = 5 # 5 to 10 excluding 6

def loadData(data) -> list[Interval]:
  try:
    r = json.loads(data)
  except Exception as e:
    return "Invalid JSON: " + repr(e)
  if "ticktock" in r:
    settings["ticktock"] = r["ticktock"]
  if "intervals" in r and type(r["intervals"]) == list:
    intervals = []
    for obj in r["intervals"]:
      try:
        intervals.append(Interval(**obj))
      except:
        return "Invalid interval: " + repr(obj)
    return intervals
  return "Intervals not readable."
