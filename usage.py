import csv
from math import copysign

from shrayder import H3Shrayder

if __name__ == "__main__":
    # Load data we created in the "prepare_data" notebook.
    with open("data/example.csv") as fp:
        reader = csv.reader(
            fp,
            delimiter=",",
        )
        # We wrote the csv with columns names, skip them
        next(reader)
        records = [[float(x) for x in row] for row in reader]

    # Get bounds from the notebook as well
    # Z Scaling may need some testing.
    app = H3Shrayder(
        data=records,
        record=False,
        z_scaling=1 / 10000,
        bounds=[-5.14803401, 41.32679241, 9.56688994, 51.09477395],
        colormap=[
            ((0.098, 0.902, 1.0), 0.0),
            ((0.298, 0.702, 1.0), 1000),
            ((0.4, 0.6, 1.0), 1500),
            ((0.502, 0.498, 1.0), 2000),
            ((1.0, 0.0, 1.0), 3000),
            ((1.0, 0.0, 1.0), 4000),
            ((1.0, 0.0, 1.0), 6000),
            ((0.902, 0.098, 1.0), 8000),
            ((1.0, 0.0, 1.0), 10000),
            ((0.702, 0.298, 1.0), 30000),
            ((0.702, 0.298, 1.0), 100000),
        ],  # Color map is ((rgb), value)
        window_size=(1280, 720),
        edit_mode=False,
        cam_pos=(0, 0, 7),  # Cam pose will only read Z for now.
        light_pos=(-5, -5, 3),
    )

    # Add "Labels"
    cities = [
        {"name": "Roazhon", "lat": -1.6662876144498853, "lon": 48.111097022925094},
        {"name": "Paris", "lat": 2.4449998927894967, "lon": 48.78028805116983},
        {"name": "Marseille", "lat": 5.362474756616706, "lon": 43.316790836426065},
    ]
    for city in cities:
        app.add_label(
            text=city["name"],
            x0=city["lat"],
            y0=city["lon"],
            x1=city["lat"] + copysign(0.5, city["lat"] - app.midx),
            y1=city["lon"] + copysign(0.5, city["lon"] - app.midy),
            z0=0,
            z1=0.5,
            line_color=(0.2, 0.2, 0.2, 1),
        )
    app.run()
