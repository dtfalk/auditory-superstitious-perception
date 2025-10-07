# **Superstitious Perception Experiment**
Hello everyone, my name is David Falk. I work at the University of Chicago and this is a document explaining how to run the code associated with the Superstitious Perception Experiment. 

## Contact Info
**email #1:** dtfalk@uchicago.edu
**email #2:** davidtobiasfalk@gmail.com

# Software you should download
The goal of this section is to give you a place where you can run python code and create Anaconda Virtual Environments using the **.yml** file in this github. If you already have a way of doing that, then you may skip this section and proceed to the next section. Otherwise, here is how to do this...

First, you will need to install Python on your device. If you already have it, then great! Otherwise, or if you do not know if you have it installed, follow the instructions in this link: https://wiki.python.org/moin/BeginnersGuide/Download

Second, you want to install VS Code. You can install it from the following link: https://code.visualstudio.com/download

Follow the link above and select the version of VS Code that matches your operating system. If it asks to create a **Desktop Icon** or **Desktop Shortcut** during installation, then please select this option.

Once this is downloaded, open up VS Code. Then search around for the **Extensions** tab. It will either be located on the left side of your screen or the top of your screen. Mine is located on the left side of my screen and it looks like 4 squares. Three of the squares are connected to each other and the top-right square looks like it is floating away from the other three. Open the **Extensions** tab and use the search bar and enter **Python**. It is published by Microsoft. Download this extension. Once it is downloaded, exit out of VS Code.

Third, you will want to install Anaconda. This is for managing our virtual environments. You may download it from this link: https://www.anaconda.com/download/success

Once it is downloaded and installed, follow the instructions in this link to get anaconda and vs code working together: https://docs.anaconda.com/working-with-conda/ide-tutorials/vscode/


# Downloading the code
Now we need to download the code for the experiment. Start by going to the github respository that contains the code (https://github.com/dtfalk/superstitious_perception_experiment). 

Scroll to the top of the page and you should see a green "<> Code" button. Click on this button and a drop down menu will appear. Click on the "Download Zip" option and this will download the code for you as a zip file. 

Once the download finishes, open up the folder and extract the folder inside of it. Put it on your desktop. Inside this folder should be all of the files/folders found on the github link. You don't want to open the folder and find a single folder which contains all of the code/templates. Rename the folder on your desktop to **superstitious_perception_experiment**.


Then open a **Anaconda Prompt** (can be found in your file searcher) and enter the following command to download all necessary packages for the experiment...

```
conda env create -f superstitious_perception_experiment.yml
```

# Running the code
Now open up VS Code. Press the **File** tab (likely towards the top left of the screen) and select **Open Folder...** from the dropdown menu. Navigate to your desktop, select the folder with the experimental code, and open it. This should open the superstitious perception experiment code in your VS Code window. 

Now click on the **View** tab (likely towards the top left of the screen) and select **Command Palette...**. Then enter **>Python: Select Interpreter**. This should open a drop down menu. Select the one that says something like **Python 3.9.0 ('superstitious_perception_experiment')**. 

Now open up the the **runExperiment.py** file from the left of the screen. **MAKE SURE THAT YOU ARE LOOKING AT THE CONTENTS OF THIS FILE FOR THE NEXT STEP**. It should look like this if you scroll to the top of the file...

```
import pygame as pg
from random import shuffle
from time import sleep
from helperFunctions import *
from questionnaires import main as questions
from questionnaires import flow_state_scale


# The experiment itself
def experiment(subjectName, subjectNumber, block, targets, distractors, saveFolder, win):


    # various variables for handling the game
    pg.event.clear()
    reset = False
    startTime = pg.time.get_ticks()
    
    # select an initial image
    image, stimulusNumber, stimulusType = selectStimulus(targets, distractors)
```

Now click on the **Run** tab (likely towards the top left of the screen) and select **Run Without Debugging**. If it asks you which debugger you want to choose, just pick whatever standard Python one is there. Now the code should be running!

# Things you need to modify
This experiment has a requirement that the images that the user sees occupy 2-degrees of their visual field. Ensuring this happens is a function of how big the monitor is, how far the user is sitting from the screen, and the resolution of the computer. 

All you will need is a measuring tape and you can change the two lines of code to ensure we adhere to this 2-degrees requirement.

First, measure the width of your screen in **centimeters**. You do not need the height. You do not need the diagonal size of the screen. **You only need the width of the monitor the subject will be looking at. You need this in centimeters.** 

Second, you need some idea of how far the subject will be sitting from the screen. Try to simulate the situation by pretending that you are the subject sitting in the chair. Take a measurement from your eyes to the screen. You can either do this once, or you can let the subject decide how they want to sit and then measure the distance from them to the screen. **You need this distance in centimeters.**

Next, open up the **constants.py** file. This is what you will see...
```
import os
from math import tan, radians
from screeninfo import get_monitors

# This block of code gets info about the subject's monitor
# =======================================================================
# =======================================================================

screen_width_in_centimeters = 31.5
distance_from_screen_in_centimeters = 69
number_of_sona_credits = 'xxx'
```

Change the the **screen_width_in_centimeters** variable to the width of the screen that you measured earlier. Then change the **distance_from_screen_in_centimeters** variable to the distance that the subject is sitting from the screen. For example, if the screen is 50 cm wide and the subject is sitting 100 cm away from the screen, then your code should look like this...
```
import os
from math import tan, radians
from screeninfo import get_monitors

# This block of code gets info about the subject's monitor
# =======================================================================
# =======================================================================

screen_width_in_centimeters = 50
distance_from_screen_in_centimeters = 100
number_of_sona_credits = 'xxx'
```

The other thing you will need to change is the **number_of_sona_credits** variable above. It is currently set to 'xxx'. Change it to however many SONA credits you are offering your subjects for their participation.
So if you are offering them 2 credits, then the line should read...
```
number_of_sona_credits = '2'
```

If you are offering them 0.5 SONA credits, then the line should read...
```
number_of_sona_credits = '0.5'
```

This updates what the subject sees during the consent screens at the beginning of the experiment
**That is all that you should need to change!!**

**If at any point in the study you see a screen that does not tell you which button to press, then press the F key**

# Data Outputs
The experiment typically takes 90 minutes to run. When the experiment first starts you will be asked to enter a **Subject Name** and a **Subject Number**. Once the subject completes the experiment, their results will be located in the **results** folder. The sub-folder containing their results will be named according to their subject number. So if your subject has subject number **1122334455**, then their results will be in a folder that is named **1122334455**. Within each folder there will be the following files:

**dissociative_experiences.csv:** The subject's responses to the dissociative experiences questionnaire.

**launay_slade.csv:** The subject's responses to the Launay-Slade questionnaire.

**tellegen.csv:** The subject's responses to the tellegen absorption questionnaire.

**flow_state_scale.csv:** The subject's responses to the flow state scale.

**gaussian_icorrelated.csv:** The subject's responses to the gaussian-weighted with i-correlated distractors block.

**gaussian_uncorrelated.csv:** The subject's responses to the gaussian-weighted with uncorrelated distractors block.

**unweighted_icorrelated.csv:** The subject's responses to the unweighted with i-correlated distractors block.

**unweighted_uncorrelated.csv:** The subject's responses to the unweighted with uncorrelated distractors block.

**stanford_sleepiness.csv:** The subject's three responses to the single-question stanford sleepiness scale.

**selfReflect_methodology.txt:** The subject's explanation of how they chose which stimuli they think had the H vs not.

**selfReflect_changes.txt:** The subject's explanation of how their decision procedure changed over the course of the experiment.

**additional_comments.txt:** The experimenter's additional comments as a text file.

**summaryData.csv:** A file containing summary data of the subject's performance over the four blocks. This includes dprime scores and the order in which the subjects received the blocks.