#!/bin/bash

# Create a temporary directory to store the renamed files
mkdir -p temp_dir

# Counter for the new filenames
counter=0

# Loop through files sorted numerically
for file in $(ls -v Cam_002/*.jpg); do
    # Pad the counter with zeros to 5 digits
    new_name=$(printf "%05d.jpg" $counter)
    
    # Move file to temp directory with new name
    mv "$file" "temp_dir/$new_name"
    
    # Increment counter
    ((counter++))
done

# Move files back to original directory
mv temp_dir/* Cam_002/
rmdir temp_dir