FROM debian:bullseye-slim

ENV DEBIAN_FRONTEND noninteractive
ENV LANG C.UTF-8

RUN apt-get -y update && apt-get install -y \
	build-essential git cmake \
    sudo nano htop gosu \
    openssh-server rsync \
    libarmadillo-dev libglm-dev libglu1-mesa-dev

# create user, ids are temporary
ARG USER_ID=1000
RUN useradd -m --no-log-init phaethon && yes chariot | passwd phaethon
RUN usermod -aG sudo phaethon
RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers


# clone Helios++
WORKDIR /home/phaethon
RUN git clone https://github.com/3dgeo-heidelberg/helios.git helios++

RUN apt-get install -y wget
# get dependecies
WORKDIR /home/phaethon/helios++/lib
RUN wget http://download.osgeo.org/proj/proj-8.0.0.tar.gz \
#https://github.com/OSGeo/gdal/releases/download/v3.3.0/gdal-3.3.0.tar.gz --no-check-certificate \
https://boostorg.jfrog.io/artifactory/main/release/1.76.0/source/boost_1_76_0.tar.gz && \
tar -xzvf proj-8.0.0.tar.gz && tar -xzvf boost_1_76_0.tar.gz

# clone & build LAStools
RUN git clone https://github.com/LAStools/LAStools.git LAStools
RUN mkdir LAStools/_build && cd LAStools/_build && cmake .. && make -j $(nproc) && cd ..

# Install Proj
RUN apt install -y libsqlite3-dev sqlite3 libtiff5-dev libcurl4-openssl-dev automake libtool
RUN git clone https://github.com/OSGeo/PROJ.git Proj
RUN cd Proj \
    && mkdir build \
    && cd build \
    && cmake .. -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF \
    && make -j$(nproc) \
    && make install

# Install GDAL
RUN apt install -y pkg-config
RUN git clone https://github.com/OSGeo/gdal.git gdal
RUN mkdir gdal/_build && cd gdal/_build && cmake cmake --build .. && make -j $(nproc) && make install && cd ..
#WORKDIR /home/phaethon/helios++/lib/gdal-3.3.0
RUN #./configure && make -j $(nproc) && make install

# Install Boost
WORKDIR /home/phaethon/helios++/lib/boost_1_76_0
RUN apt install -y libpython3.9-dev python3 python3-pip && \
./bootstrap.sh --with-python=python3.9 && ./b2 cxxflags=-fPIC && ./b2 install


# clone & build LAStools
#WORKDIR /home/phaethon/helios++
#RUN git clone https://github.com/LAStools/LAStools.git lib/LAStools
#RUN mkdir lib/LAStools/_build && cd lib/LAStools/_build && cmake .. && make -j $(nproc)

# build helios ++
WORKDIR /home/phaethon/helios++
ENV PYTHONPATH=/home/phaethon
RUN mkdir _build && cd _build && cmake -DPYTHON_BINDING=1 -DPYTHON_VERSION=39 .. && make -j $(nproc)

# Install PyHelios dependencies
RUN python3 -m pip install open3d

RUN chown -R phaethon:sudo "/home/phaethon/helios++"
RUN chmod -R a=r,a+X,u+w "/home/phaethon/helios++"
RUN chmod 755 "/home/phaethon/helios++/_build/helios"

#RUN echo "PATH=$PATH:/home/phaethon/helios++/_build" >> /home/phaethon/.profile
ENV PATH "$PATH:/home/phaethon/helios++/_build"

WORKDIR /home/phaethon/

RUN echo "Recopying stuff"
# Add helios-entrypoint, for user-managment (gosu e.t.c)
COPY helios-entrypoint.sh /usr/local/bin/helios-entrypoint.sh
RUN chmod +x /usr/local/bin/helios-entrypoint.sh
ENTRYPOINT ["/usr/local/bin/helios-entrypoint.sh"]
