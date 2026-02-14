import os
import csv
from numpy import mean, std, max, min

# Accepts a list of r_scores and condition (e.g. "full_sentence-targets") returns summary stats for the list
def getSummaryStats(r_scores, condition):
    # print(r_scores)
    print(f"Summary Statistics for {condition} condition (n = {len(r_scores)})\n======================================")
    print(f"Mean: {mean(r_scores)}")
    print(f"Std: {std(r_scores)}")
    print(f"Range: {max(r_scores) - min(r_scores)}")
    print(f"Max: {max(r_scores)}")
    print(f"Min: {min(r_scores)}\n\n")

# Returns r_scores for a list of stimulus numbers
def getRScores(stimulus_numbers, condition, csvFolderPath):
    # print(condition)
    
    # Get CSV path
    if "targets" in condition:
        filename =  "high_correlation_stimuli.csv"
    elif "distractors" in condition:
        filename = "low_correlation_stimuli.csv"
    csv_file = os.path.join(csvFolderPath, filename)

    r_scores_dict = {}
    with open(csv_file, mode = "r") as f:
        reader = csv.reader(f)
        next(reader)
        for (stim_num, r_score) in reader:
            r_scores_dict[stim_num] = r_score
        
    r_scores_list = []
    for stim_num in stimulus_numbers:
        r_scores_list.append(float(r_scores_dict[stim_num]))
    
    return r_scores_list

def main():

    # Get paths
    curDir = os.path.dirname(__file__)
    stimuliFolderPath = os.path.join(curDir, "..", "..", "audio_stimuli")
    targetFolders = ["full_sentence", "imagined_sentence", "examples"]
    csvFolderPath = os.path.join(stimuliFolderPath, "correlation_csvs")

    # Initialize object to store stimulus data
    data_dict = {}

    # Iterate over folders and build lists
    for folder in targetFolders:
        
        # Get path to folder
        for stim_type in ["targets", "distractors"]:
            
            # key to index into data dict
            dict_key = f"{folder}-{stim_type}"

            # Iterate over the stimuli
            folderPath = os.path.join(stimuliFolderPath, folder, stim_type)
            for wav_file in os.listdir(folderPath):

                # Remove extension to get stimulus number
                stim_number = wav_file.replace(".wav", "")

                # Add to data dict
                try:
                    data_dict[dict_key].append(stim_number)
                except:
                    data_dict[dict_key] = [stim_number]

    # Get super lists    
    data_dict["all-targets-examples-excluded"] = data_dict['full_sentence-targets'] + data_dict['imagined_sentence-targets']
    data_dict["all-distractors-examples-excluded"] = data_dict['full_sentence-distractors'] + data_dict['imagined_sentence-distractors']
    data_dict["all-targets-examples-included"] = data_dict['full_sentence-targets'] + data_dict['imagined_sentence-targets'] + data_dict["examples-targets"]
    data_dict["all-distractors-examples-included"] = data_dict['full_sentence-distractors'] + data_dict['imagined_sentence-distractors'] + data_dict["examples-distractors"]

    # Get data for each condition
    for condition in data_dict.keys():
        r_scores_list = getRScores(data_dict[condition], condition, csvFolderPath)
        getSummaryStats(r_scores_list, condition)



    

if __name__ == "__main__":
    main()