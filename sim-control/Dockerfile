# Gazebo client + a 100-line HTTP server: lets a dashboard button reset the SITL
# aircraft (teleport the model to tag 0) without touching Docker.
FROM droneblocks/px4-gazebo-slim:1.16.0
RUN apt-get update && apt-get install -y --no-install-recommends python3 && rm -rf /var/lib/apt/lists/*
COPY sim_control.py /opt/sim_control.py
ENV GAZEBO_MASTER_URI=http://px4-sitl:11345 PORT=8090
ENTRYPOINT ["python3", "/opt/sim_control.py"]
