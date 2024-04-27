# Rain World Clock

Recreates the cycle clock in the game [Rain World](https://rainworldgame.com/). If you haven't played it, go check it out!

## Building

Make sure you have Python (3.12.1), `setuptools` (69.5.1), `PyObjC` (10.2), `numpy` (1.26.3) and `pillow` (10.3.0) installed. Generally the newest version should work, but the version numbers are included in parentheses if you are reading this a few decades in the future.

Run `python3 setup.py py2app` to build. The results will be in `dist/Clock.app`.

## Usage

Open the app. It will create a task bar button. Use the drop-down menu from the button to select JSON files. An example file (the comments are not valid JSON, they are for demo purposes only):

```js
{
  "ticktock": 3.2,  // seconds between tick and tock
  "intervals": [{
    "totalPip": 25,  // total number of pips in a cycle, can be zero (default)
    "totalTime": 1791,  // total seconds in the cycle, can be zero for infinite time (default)
    "karmaSymbol": 1,  // karma symbol from 0-10, 0 (default) means empty
    "karmaReinforced": true  // karma flower is in effect, default false
  }, {
    "totalPip": 15,
    "totalTime": 670,
    "karmaSymbol": 8,
    "maxKarma": 9  // max karma (7-10) must be specified if karmaSymbol > 5.
  }]
}
```

The sound effects come from [this repo](https://github.com/cookiecaker/Rain-World-Sounds) and are properties of the Rain World developers. All png files in the repo come from the [rain world wiki](https://rainworld.miraheze.org/wiki/Category:Karma_icons), see copyright notices there. The rest are shared under the MIT License.
