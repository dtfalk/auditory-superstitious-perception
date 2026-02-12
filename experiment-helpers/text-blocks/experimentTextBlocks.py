from ..experimenterLevers import SENTENCE_TO_IMAGINE

# Instructions that are not specific to any block or condition
# =======================================================================
# =======================================================================

explanationText_1 = 'Welcome to the experiment!\n\n\
In this experiment, you will listen to a series of short, static-like audio samples. For each sample, your task is to decide whether a specific word is present in the sound.\n\n\
The word you will be listening for is \"Wall\".\n\n\
This task is intentionally very difficult. The audio samples will mostly sound like noise, and the word will never be clearly spoken or easy to hear. Many people report feeling unsure whether they ever truly hear the word they are searching for.\n\n\
Even so, people typically perform well on this task despite feeling uncertain. Feeling unsure or unconfident is normal and expected.\n\n\
Your job is not to clearly identify the word, but to listen carefully and decide whether the sound gives you the impression that the word \"Wall\" might be present.'

explanationText_2 = 'To help you think about this task, imagine overhearing someone speaking through a wall or a closed door. You can tell that a voice might be there, but the sound is muffled and buried in ambient noise. You strain to listen, trying to pick out speech, and sometimes it feels like a specific word or phrase might have been present, even though you are never sure.\n\n\
This task is similar in spirit, but the word that you are listening for will be even more difficult to discern. You will never clearly hear the word \"Wall\". Instead, you may find yourself caught between hearing and guessing, where the sound creates a vague impression rather than a definite perception.\n\n\
Many people describe this experience as a strange or superstitious feeling, where intuition, along with faint internal impressions or sensations, guides decisions more than clear evidence.\n\n\
That uneasy, in-between feeling is not a mistake or a sign that something is wrong. These subtle thoughts and impressions are a meaningful part of yourself that is quietly trying to make itself known.\n\n\
Your job is to engage with these thoughts and feelings, take them seriously, and listen carefully to what they are trying to tell you.'

explanationText_3 = f'As mentioned earlier, throughout this experiment you will always be listening for the word \"Wall\".\n\n\
Importantly, you will always be listening for the word \"Wall\" as it occurs within the context of this sentence:\n\n\
\"{SENTENCE_TO_IMAGINE}\"\n\n\
Rather than searching for an isolated word, this sentence provides the context that shapes how the word \"Wall\" would naturally sound.\n\n\
You will be introduced to a specific speaker, and you will hear a recording of the speaker saying the full sentence aloud.\n\n\
During the task, you are always searching for this speaker’s version of the word \"Wall\", as it would naturally occur at the end of this sentence.\n\n\
The audio samples you will listen to during the task will not clearly sound like the speaker’s voice. Instead, they will sound like noise. In some of these samples, traces of the speaker’s word \"Wall\" have been hidden within the noise.\n\n\
Your task is to decide whether the speaker’s \"Wall\", as spoken in the context of the sentence, seems to be present in each audio sample.'

explanationText_4 = 'What to keep in mind:\n\
    - When the word \"Wall\" is present, it always spans the entire audio sample from beginning to end.\n\
    - You should base your response on whatever impression or feeling the sound gives you, even if you are not confident.\n\n\
Important notes:\n\
    - If you have any questions at any point or wish to stop, please tell the experimenter immediately.\n\
    - We know this task is challenging and truly appreciate your effort and participation.\n\
    - Please try your best. Better performance increases your chances of winning the raffle.\n\
    - If you are actively trying, it is okay to trust your intuition.\n\n\
If you have any questions, please ask the experimenter now.'

explanationText_5 = 'A final note before beginning:\n\n\
Even with the sentence context and the speaker in mind, the audio samples you will hear will remain extremely noisy. You will never clearly hear the word \"Wall\" spoken in the samples.\n\n\
It is normal for many trials to feel uncertain, ambiguous, or as though nothing definite is there at all.\n\n\
That experience is expected. Doing well on this task does not require certainty or confidence, but a willingness to stay engaged and respond based on the impressions you have, even when they feel faint or unclear.'

breakScreenText = 'You have now completed 1 out of 2 blocks.\n\n You have earned a break.\n\n Please let the experimenter know.\n\nWhen you are ready you will begin the next portion of the experiment.\n\n'

exitScreenText = 'Thank you for participating in this study!\n\n'\
'Please notify the experimenter that you have completed the study.\n\n'\
# =======================================================================
# =======================================================================

# Block/Condition specific instructions
# =======================================================================
# =======================================================================

# Block introduction & explanation
# =======================================================================
fullSentenceBlockInstructionsText = (
    "In this part of the experiment, on each trial you will hear a recording of the speaker saying this sentence before you make your judgement:\n\n"
    f"\"{SENTENCE_TO_IMAGINE}\"\n\n"
    "The sentence is always the same, except that the final word is replaced by a short, static-like audio sample.\n\n"
    "Your task on each trial is to decide whether the speaker’s \"Wall\", as it would naturally complete the sentence, seems to be present in that noisy audio sample.\n\n"
    "A few important points:\n"
    "   - The audio samples themselves are not clearly spoken words. They are noisy clips that may or may not contain traces of the speaker’s \"Wall\".\n"
    "   - If the speaker’s \"Wall\" is present, it spans the entire audio sample from beginning to end.\n"
    "   - You are always judging whether the speaker’s version of \"Wall\" is present in the audio sample, NOT your own imagined version.\n\n"
    "Next, you will listen to the speaker say the full sentence as many times as you like.\n\n"
    "Press the spacebar to continue."
)


imaginedSentenceBlockInstructionsText = (
    "In this part of the experiment, you will imagine the speaker saying this sentence before you make your judgment:\n\n"
    f"\"{SENTENCE_TO_IMAGINE}\"\n\n"
    "On each trial, you will imagine the speaker saying the beginning of this sentence in their voice.\n\n"
    "As your imagined sentence reaches the word \"Wall\", you will click \"Play Audio\" to hear a short, static-like audio sample.\n\n"
    "Your task is to decide whether the speaker’s \"Wall\", as it would naturally complete the sentence, seems to be present in that noisy audio sample.\n\n"
    "A few important points:\n"
    "   - The audio samples themselves are not clearly spoken words. They are noisy clips that may or may not contain traces of the speaker’s \"Wall\".\n"
    "   - If the speaker’s \"Wall\" is present, it spans the entire audio sample from beginning to end.\n"
    "   - You are always judging whether the speaker’s version of \"Wall\" is present in the audio sample, NOT your own imagined version.\n"
    "   - You may only IMAGINE the sentence. Do not say the sentence out loud, move your lips or otherwise subvocalize. \n\n"
    "Next, you will hear the speaker say the full sentence as many times as you like.\n\n"
    "Press the spacebar to continue."
)
# =======================================================================

# Final reminders before the first trial of the block
# =======================================================================
preTrialQuickResponseTextFullSentence = (
    "Before you begin:\n\n"
    "- On each trial, you will hear the sentence once, with the final word replaced by a noisy audio sample.\n"
    "- Each audio sample can only be heard one time. There are no replays.\n"
    "- When you are ready to respond, press \"Y\" if you sense that the speaker’s \"Wall\" is present, and \"N\" if you believe it is not.\n"
    "- Please respond quickly after hearing the stimulus.\n\n"
    "On the next screen, you will be asked to respond to a single question.\n"
    "After that, you will hear the sentence again to prepare, and the real trials will begin immediately.\n\n"
    "Trust your gut feelings. It is okay to be uncertain.\n\n"
    "Press the spacebar to continue."
)


preTrialQuickResponseTextImaginedSentence = (
    "Before you begin:\n\n"
    "- On each trial, you will imagine the speaker saying the sentence, then listen to a noisy audio sample.\n"
    "- Each audio sample can only be heard one time. There are no replays.\n"
    "- When you are ready to respond, press \"Y\" if you believe the speaker’s \"Wall\" is present, and \"N\" if you believe it is not.\n"
    "- Please respond quickly after hearing the stimulus.\n\n"
    "- On every trial, imagine the sentence in the speaker’s voice and click \"Play Audio\" at the moment you would be imagining the word \"Wall\".\n"
    "- The sentence must be imagined silently. Do not say it out loud, under your breath, or move your mouth.\n\n"
    "On the next screen, you will be asked to respond to a single question.\n"
    "After that, you will hear the sentence again to prepare, and the real trials will begin immediately.\n\n"
    "Trust your gut feelings. It is okay to be uncertain.\n\n"
    "Press the spacebar to continue."
)
# =======================================================================

# Instructions shown on every trial
# =======================================================================
trialInstructions_full_sentence = [
    "Click 'Play Audio' to listen to the speaker saying the sentence.",
    "",
    "After listening, respond as quickly as you feel comfortable.",
    "Press 'Y' if you believe the speaker's \"Wall\" is hidden in the noisy audio sample.",
    "Press 'N' if you believe the speaker's \"Wall\" is NOT hidden in the noisy audio sample.",
]

trialInstructions_imagined_sentence = [
    "Silently imagine the speaker saying this sentence in their voice:",
    f'{SENTENCE_TO_IMAGINE}',
    "Imagine the speaker saying the beginning of the sentence and click 'Play Audio' when your imagined sentence reaches the word \"Wall\".",
    "After listening, respond as quickly as you feel comfortable.",
    "Press 'Y' if you believe the speaker's \"Wall\" is hidden in the noisy audio sample.",
    "Press 'N' if you believe the speaker's \"Wall\" is NOT hidden in the noisy audio sample.",
]
# =======================================================================
# =======================================================================   