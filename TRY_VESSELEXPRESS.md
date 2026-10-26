# Try VesselExpress with the Browser UI

This guide runs the upstream VesselExpress web interface on the same computer where Docker is installed. It does not require cloning this repository or changing its files.

## 1. Install Docker

- **Windows or macOS:** Install and start [Docker Desktop](https://docs.docker.com/get-docker/).
- **Linux:** Install Docker Engine using the instructions for your distribution at [Docker Engine installation](https://docs.docker.com/engine/install/), then make sure the Docker daemon is running.

Open a terminal (PowerShell is fine on Windows) and check that Docker can reach its engine:

```sh
docker version
```

The output should include both a **Client** and a **Server** section. If the Server section is missing or reports an error, start Docker Desktop or the Docker service before continuing.

## 2. Download and start VesselExpress

Pull the browser-interface image published by the VesselExpress project:

```sh
docker pull phispa1812/vesselexpress
```

Create a named volume for uploads, configuration, and results. The volume keeps this data when the container stops or is replaced:

```sh
docker volume create vessel-express-data
```

Start the web app:

```sh
docker run -d --name vesselexpress-ui -p 127.0.0.1:5000:5000 -v vessel-express-data:/home/user/VesselExpress_server/VesselExpress/data phispa1812/vesselexpress
```

Open **http://localhost:5000** in a browser on that same computer. The port is bound to localhost so other computers on the network cannot connect directly. The app does not provide authentication, so do not change this to a network-wide port binding for shared use.

If port 5000 is already in use, change the port mapping to `127.0.0.1:5001:5000` and open **http://localhost:5001** instead.

## 3. Run a small test

For a first run, use the project's [example data on Zenodo](https://doi.org/10.5281/zenodo.5733150) and start with one representative single-channel grayscale TIFF stack. Large light-sheet volumes can require substantial memory and disk space, so avoid beginning with a full study batch.

In the web interface:

1. Upload a `.tif` or `.tiff` image stack.
2. Review the parameter sidebar. The right parameters depend on the organ and imaging data; example-data presets and the separate [Napari plugin](https://www.napari-hub.org/plugins/vessel-express-napari) can help with tuning.
3. Apply configuration changes, then select **Run Pipeline**.
4. Follow progress in the console. When processing finishes, download the statistics or all results. Save downloaded results somewhere outside the Docker volume if you need to share or archive them.

The project describes a pipeline that segments vessels, extracts skeletons, builds a graph, and calculates vascular measurements. Review the resulting masks and measurements to make sure the settings suit your data before using results in an experiment.

## 4. Stop and resume

Stop the app when you are done:

```sh
docker stop vesselexpress-ui
```

Start it again later:

```sh
docker start vesselexpress-ui
```

The `vessel-express-data` volume remains available across stops and restarts. The interface's **Clear files** action deletes uploaded and generated files from the app's data directory, so download anything you want to keep first.

## 5. Remove the test installation

Remove the stopped or running container:

```sh
docker rm -f vesselexpress-ui
```

This leaves the data volume intact. To permanently delete the uploaded files, configuration, and results too, remove the volume:

```sh
docker volume rm vessel-express-data
```

## Troubleshooting

- **The page does not load:** Check `docker ps` for the container and `docker logs vesselexpress-ui` for startup errors. Confirm you are opening the same host port used in the `docker run` command.
- **The container name is already in use:** Run `docker start vesselexpress-ui` if it already exists, or remove it with `docker rm -f vesselexpress-ui` before creating a new one. The named data volume is separate and will remain unless explicitly removed.
- **The app is slow or the computer runs out of memory:** Stop the run and try a smaller image or fewer files. The software processes image volumes and can be resource-intensive.
- **You are running Docker on a remote server:** This guide assumes the browser and Docker are on the same computer. Do not expose the unauthenticated app directly to a shared network; use an appropriately secured tunnel or deployment setup instead.

For more background, see the [VesselExpress source and upstream instructions](https://github.com/RUB-Bioinf/VesselExpress) and the [paper included in this repository](rapid_vascular_analysis_cell_paper.pdf).
