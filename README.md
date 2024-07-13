# [WIP] shrayder
Trying to use [panda3d](https://www.panda3d.org/) to create kinda cool maps.


## How to use

Prepare Data following [this notebook.](./prepare_data.ipynb)

You need to pass data in the form `[(lat, lon, value), (lat, lon, value), (lat, lon, value), ...]`

Example in [this script](./usage.py)

Then run `python3 usage.py`

You can move around using the Arrow Keys

Zoom with `w` and un-zoom with `s`

The shaders might be the worst you'll ever read, as it's essentially a Frankenstein's Monster from what I found on the forums.
Any help would be more than appreciated. 😼

# Dev
Use `stubgen -o ./ -p panda3d` to get autocomplete in IDE.