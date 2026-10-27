# lightsheet_analysis
A repository for code for analyzing vasculature segmented from light sheet microscopy

## Neurolucida XML to colored OBJ

This Flask application converts Neurolucida vessel tracings into a 3D tube mesh. It uses each edge's centerline points and `d` diameters to build the geometry, and writes each vessel's XML color to an OBJ material. The OBJ and its companion MTL file are downloaded together in a ZIP archive.

### Run locally

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000), choose a Neurolucida `.xml` tracing, select the tube smoothness, and convert. Import the `.obj` from the ZIP into 3D software with the `.mtl` in the same folder to preserve the vessel colors. Coordinates and diameters remain in the units recorded in the source XML.

The app accepts XML files up to 50 MB and limits output to two million mesh vertices. For a network deployment, run behind an appropriately secured web server; the built-in Flask server is intended for local use.

### Run tests

```sh
python -m unittest discover -s tests
```
