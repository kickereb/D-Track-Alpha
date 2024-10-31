# DTRACK Calibration Suite

## How to obtain syncronised calibration images from all the nodes

1. Setup known static ip addresses on a master computer and all the slave nodes
2. On master computer run an MQTT broker docker server to be able to send and receive image trigger
3. Run `python master_calibrator.py` on master computer (laptop)
4. Run `python start_slave_nodes_remotely.py` on master computer (laptop) which will start all the connected nodes automatically.
5. Follow GUI instructions on master computer.

## How to utilise the syncronised calibration images to obtain camera matricies for all camera nodes

After following previous sections instructions on how to obtain the syncronised calibration images, follow these steps to run the calibration script that processes all of the images.

1. Run `python calibration.py`
2. Send the matricies to the corresponding node using `scp data/calibrations/Cam_001_calibration.yml dtrack@node_ip:/home/dtrack/D-Track-Alpha/camera_node/calibration_matrices.yml`
