FROM debian:bullseye-slim

ENV DEBIAN_FRONTEND noninteractive
ENV LANG C.UTF-8

RUN apt-get -y update && apt-get install -y \
    sudo nano htop gosu \
    openssh-server rsync \
    wget xz-utils unzip \
    libx11-dev libxxf86vm-dev libxcursor-dev libxi-dev libxrandr-dev libxinerama-dev libglew-dev
# create user, ids are temporary
ARG USER_ID=1000
RUN useradd -m --no-log-init mash && yes mesh | passwd mash
RUN usermod -aG sudo mash
RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# clone Helios++
WORKDIR /home/mash
RUN wget https://ftp.halifax.rwth-aachen.de/blender/release/Blender3.1/blender-3.1.2-linux-x64.tar.xz
RUN apt-get install -y




RUN mkdir /home/mash/blender
RUN tar -Jxf blender-*-linux-x64.tar.xz --strip-components=1 -C /home/mash/blender
RUN rm blender-*-linux-x64.tar.xz

# BlenderBim Addon
RUN wget https://github.com/IfcOpenShell/IfcOpenShell/releases/download/blenderbim-220509/blenderbim-220509-py310-linux.zip
RUN unzip blenderbim-*-py310-linux.zip -d /home/mash/blender/3.1/scripts/addons/
RUN rm blenderbim-*-py310-linux.zip

#/home/mash/.config/blender/3.1/config
RUN mkdir -p "/home/mash/.config/blender/3.1/config"
COPY patches/userpref.blend /home/mash/.config/blender/3.1/config/userpref.blend

RUN chown -R mash:sudo "/home/mash/blender"
RUN chmod -R a=r,a+X,u+w "/home/mash/blender"
RUN chmod 755 "/home/mash/blender/blender"
RUN chmod 755 "/home/mash/blender/3.1/python/bin/python3.10"

#RUN echo "PATH=$PATH:/home/phaethon/helios++/_build" >> /home/phaethon/.profile
ENV PATH "$PATH:/home/mash/blender/blender"

RUN echo "Preparing stuff"
COPY blender-entrypoint.sh /usr/local/bin/blender-entrypoint.sh
RUN chmod +x /usr/local/bin/blender-entrypoint.sh
ENTRYPOINT ["/usr/local/bin/blender-entrypoint.sh"]
