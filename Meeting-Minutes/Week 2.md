**Date:** 02/08/2024
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
1. Further on calibration
2. The OpenCV camera calibration method
3. Intrinsic and extrinsic parameter tuning
4. Extrinsic initialisation (global and local coordinate system setup, calibrating starting point by showing a checkerboard pattern)

### Discussion Points:
1. Further on calibration
   - Key points discussed
      - Methods of precise calibration to setup object detection and tracking.
      - Discussion on challenges faced during multi-camera calibration and ways to address them.
   - Decisions made
      - Continue exploring various calibration techniques to find the most efficient one.
      
2. The OpenCV camera calibration method
   - Key points discussed
      - Utilising OpenCV’s built-in functions for camera calibration.
      - Steps involved in using a printed checkerboard pattern for intrinsic calibration.
      - Potential issues and troubleshooting for common calibration problems.
   - Decisions made
      - Standardise the use of OpenCV for intrinsic calibration across all cameras.
   - Action items
      - Set up a test environment using OpenCV.

3. Extrinsic initialisation (global and local coordinate system setup, calibrating starting point by showing a checkerboard pattern)
   - Key points discussed
      - Setting up a global coordinate system to ensure consistency across multiple cameras.
      - Using a checkerboard pattern to initialise extrinsic parameters and establish a starting point.
      - Discussion on best practices for maintaining calibration over time and across different setups.
   - Decisions made
      - Use a checkerboard pattern for initialising extrinsic parameters and ensure regular recalibration.
   - Action items
      - Create a detailed guide for extrinsic initialisation and share it with the team for implementation.

4. Presentation Workload Distribution and Discussion
   - Key points discussed
      - Discussed the upcoming presentation's format and expectations.

### Action Items:
- [ ] Experiment with different calibration methods and document the results: Assigned to Evam, Lennox, Due before next meeting
- [ ] Set up a test environment using OpenCV for camera calibration and validate the results: Assigned to Lennox, Tom, Due before next meeting
- [ ] Develop a workflow for parameter tuning and test it with a sample camera setup: Assigned to all, Due before next meeting
- [ ] Create a detailed guide for extrinsic initialisation and share it with the team: Assigned to Tom, Lennox, Due before next meeting

### Next Meeting:
**Date:** 09/08/2024  
**Time:** 4:00pm - 4:30pm  
**Location:** Barr Smith South/1062/Teaching Room

### Additional Notes:
N/A
