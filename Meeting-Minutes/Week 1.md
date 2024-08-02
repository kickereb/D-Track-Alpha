**Date:** 26/07/2024
**Time:** 4:00pm - 4:30pm
**Location:** Barr Smith South/1062/Teaching Room
### Attendees:
- Lennox Avdiu
- Tom Zhu
- Evam Kaushik
- Ranjeet
- Damith
### Absent:
- Everyone attended
### Agenda:
1. Potential ways of achieving camera calibration & multi-camera setup
2. Software architecture
3. How to solve Raspberry Pi & camera setup issues
4. Addressing how we might tackle object detection/tracking
### Discussion Points:
1. Potential ways of achieving camera calibration & multi-camera setup
   - Key points discussed
      - Intrinisics will be easy to calculate by utilising a printed checkerboard and utilise a package such as opencv to automatically calculate these values
      - Extrinsics will be a bit more problematic for a multi-camera setup as some thought and care need to go in to how we properly map each cameras frame to some global coordinate system. One potential solution discussed was the use of feature detection with algorithms such as SIFT or ORB on each camera and some reference image which will provide mapped points from which we can calculate a homography. There are benefits to this approach such as the ease of setting up any additional camera in future without fiddling around with measuring its extrinsics relative to the global coordinate system. There was discussion however, on how there may be another approach to consider from the paper referenced `Track initialization and re-identification for 3D multi-view multi-object tracking.`.
   - Decisions made
      - None as of yet, as there are still other approaches to consider which might make the groups life easier in future.
   - Action items
      - Read `Track initialisation and re-identification for 3D multi-view multi-object tracking.` and evaluate the pros and cons between the paper's approach to calculating extrinsics and the feature matching way.
2. Software architecture
   - Key points
      - Will be challenging to create a cloud platform for real-time data streaming due to unknown network latency. This is to be further investigated once we establish the link between the raspberry pi object tracking node and the backend server to actually test what kind of fps we could acheive. Otherwise it might just make more sense to have a local computer acting as the backend server.
      - Python was everyones preferred choice for backend language so we can utilise FastAPI.
      - React native might make sense due to being mobile os agnostic and React js experience on the team.
   - Decisions made
      - Unnecessary to decide as of yet
   - Action items
      - Blocked by the Raspberry PI setup because it's not possible to test streaming performance, hence no decisions can be made on software architecture as of yet.
3. How to solve Raspberry Pi & camera setup issues
   - Key points discussed
      - Camera may have been faulty and was deemed to be non-resolvable.
   - Decisions made
      - Getting a new camera and RPI from Fei.
   - Action items
      - Get new camera working [Was successfully done by Tom :partying_face:]
4. Addressing how we might tackle object detection/tracking
   - Key points discussed
      - Yolov8 seems to be what we want to utilise for object tracking
   - Decisions made
      - None as of yet
   - Action items
      - Get Yolov8 object tracking working on Raspberry PI
### Action Items:
- [ ] Read `Track initialisation and re-identification for 3D multi-view multi-object tracking.`: Assigned to Lennox, Evam, Due before next meeting
- [x] Get new camera working: Assigned to Tom, Due before next meeting
- [ ] Get Yolov8 object tracking working on Raspberry PI: Unassigned, Due week 3?
### Next Meeting:
**Date:** 26/07/2024
**Time:** 4:00pm - 4:30pm
**Location:** Barr Smith South/1062/Teaching Room
### Additional Notes:
N/A
