# How to process


This document describes how to process the files useed in the paper "Enhancing Railway Detection by Priming Neural Networks
with Project Exaptations". The files are available at [https://filedn.eu/l4hiESSdAeuuEoSLE7Uolr4/boosting_paper/2022-08-16_boosting-trackmodels.zip](2022-08-16_boosting-trackmodels.zip). 

### Preconditions
#### Software
*Tested on Ubuntu 20.04, partly Windows 10 (WSL2) but not everything will work there*

From the software side, you need to have the following software installed:
- a functioning docker installation (see [https://docs.docker.com/get-docker/](https://docs.docker.com/get-docker/))
- a functioning docker-compose installation (see [https://docs.docker.com/compose/install/](https://docs.docker.com/compose/install/)) (should come with docker)
- anaconda (see [https://docs.anaconda.com/anaconda/install/](https://docs.anaconda.com/anaconda/install/))

#### Hardware
The processing is intensive these requirements are more guesswork than anything else. In the paper a threadripper 3990x/256GB was used.
- recommended at least 32GB of memory. This is mostly used by blender and if ifcconvert is used, it should be lighter on memory.
- disk space (recommended at least 100GB) 

### Setup
Download and unzip the test files to a folder of your choice. 

```bash
conda env create --name railtwin_virtualizer python=3.10 --file environment.yml
```

```bash
conda activate railtwin_virtualizer
```

```bash
pip install -r requirements.txt
```

### Processing
```
DISCLAIMER: Sometimes the virtualization seem to hick-up (mostly helios). If there is no cpu usage for a longer time restart the recent process.
```

All processes are executed using the **main.py** script. The script uses a primary level to determine which steps to execute. 
The primary level is the first argument to the script. The primary levels are:
- **prepare_models**
- **simulate**
- **prepare_labels**
- **evaluate**
- **visualize**
- **pre-production**

Each script has a number of subcommands that can be reviewed using the **--help** option. Preproduction executes prepare, simulate and some label functions.
This schould generate the base labels to start AI Experiments. 

```bash
python main.py --in <path-to-ifc-folder> --out <path-to-ifc-folder> --object_mapping <path-to-object_mapping.json> --sysco_map <path-to-sysco_map.json> 
```

#### 1. Prepare the models for the simulation with Helios
There are multiple substeps to be taken. The goal is to extract a railcart ride along a given track model. 
The trackmodel needs the 4.1 alignment description which will be extracted an sampled first.
After this, areas are seperated. Originally the software recgonized multiple alignments in the same area.
And creates a seperate model for each alignment. Remnenants of this are still in the code and might be activated by the ONLY_CREATE_ONE_MODEL_MULTI_TRACKS flag.
In the development we went for more diversification and made sure that each model has a single alignment. 
During this, the ifc model is also triangulated and object wise operations are conducted (mostly specific to ProVI)

In a next step the models are converted to obj. There are two options, a simple convert, and an enrichment version with blender.
The blender version creates more realistic surfaces and is the default, but uses insane amounts of memory. You can influence the behaviour with  BLENDER_VOXEL_SIZE.
It starts a blender docker that then works with the python/modelling/blender scripts. 

The last step in before the helios simulation is the modification of the *.mtl files so the material type links to the ifc entitiy.

All steps can be executed using the following command:
```bash
python main.py prepare_models --in <path-to-ifc-folder> --out <path-to-workdir> --step all_steps
```

#### 2. Simulate the railcart ride with Helios
For the simulation there are few things to consider. The railcart follows the previously extracted alignment. 
The settings are defined in the traversal is speed varied simulation/templates. 
Additionally, speed and sampling is varied by the code (SpeedoMeter and assemble_survey). 
The whole process is started in a helios docker which is started automatically.

The simulation is started using the following command:
```bash
python main.py simulate --in <path-to-workdir> --step all_steps
```
#### 3. Prepare the labels and files
After the simulation the pointclouds are the processed with reduced prior knowledge to make the results comparable to real pointclouds.

###### Batching / Chunking
The first start splits the generated point cloud into multiple segments. The segments are defined by the length and default is 100m.

```batch
python main.py prepare_labels --in <path-to-workdir> --step batches
```

###### Enrichment
The second step is an enrichment, where addtional features are added to the points, the following features are always accessible:
- dtm height (see elberink et al. 2013)
- dtm class (see elberink et al. 2013, reworked but same concept)

*if alignment is available, and option is set:*
- distance to track 
- sagittal_distance
- scan_angle

```batch
python main.py prepare_labels --in <path-to-workdir> --step enrich
```

###### Label Format
The third step is situational and depends on the provided mapping data (see supplement git). Examples are present in labeling/mapping.
There are few options to choose from:
- helios2rtib3+ (converts the helios data to the rtib3+ format)
- s3dis2rtib3+  (converts the s3dis data to the rtib3+ format, s3dis is the same as export of CloudCompare)
- helios2s3dis  (cross convert (not testet in latest version))
- unify_labels  (create a different label system if labels need to be reduces (e.g. for training))

#### 4. Evaluate the results
After KPConv training and evaluation, here are some tools to get statistics.

#### 5. Visualize the results
Some tools to visualize the results.


