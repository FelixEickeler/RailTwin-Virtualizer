# ModelVirtualizer

This is the complete toolkit to simulate point clouds from *.ifc 4x1 models that prepares all labels for training with kpconv.
There are two pathways:
- SYNTH: ifc -> blender -> helios -> pointcloud -> labels -> unify_labels
- PHYSICAL: pointcloud -> labels -> unify_labels

### How to get started
To run the files published in the paper: https://www.mdpi.com/2072-4292/14/21/5482, see the HOW-TO-README.md
[doc/how-to-process.md](doc/how-to-process.md)

The whole tool includes various steps. A general overview is in the image below. 
[![Processing steps](https://raw.githubusercontent.com/railtwin/railtwin_virtualizer/main/doc/processing_steps.png)](https://raw.githubusercontent.com/railtwin/railtwin_virtualizer/main/doc/processing_steps.png)


### General Process
####1. Prepare Models
   1.  **Extract the alignments from the 4x1 model** <br> 
   The alignments will later provide the path for the laser-scanning platform. 
   Plots of the alignments are also created !
   <br><br>
   
   2. **Extract Areas** <br>
   Only the *.ifc objects in the vicinity of the alignment will be considered. 
   If there are multiple alignments each alignment will result in one point_cloud simulation. 
   All extracted *.ifc files are fully triangulated and will have one surface-style linked to each ifc_object. 
   The surface-style will be named after the guid of the ifc element.
   Additional output is a mapping of all ifc elements, and their name representing their class as a *.json obj
   Two different mapping exists. A file-wise local mapping and a global mapping (default: folder above)
   <br><br>
   
   3. **Convert IFC** <br>
   Straight forward conversion of the extracted *.ifc file to a obj file. 
   <br><br>
   4. **Helios Preparation** <br>
   The *.mtl, which now have the guids in the material names, will be processed. 
   Two new *.new mtl files will be generated (helios_classification): class & object classification  
   
####2. Simulation 
   1. **Preprocessing** <br>
   Needed helios files are generated. 
   This includes the ifc depend on files: survey.xml, scene.xml and the generic helios setting: platforms.xml, scanners.xml
   All speccific files will be put into the "helios" folder
   <br><br>
   2. **Simulation** <br>
   Straight forward simulation with helios. Take care this might take time !
   <br><br>
   3. **Post** <br>
   Alternative way to generate output !

####3. Prepare Labels
   1. Create Batches
   2. Enrich
   3. Convert Labels (optional)
   4. unify Labels (optional)

####4. Evaluation
   1. Evaluation of the inferent results

####5. Visualization
   1. Visualization of the inferent results


